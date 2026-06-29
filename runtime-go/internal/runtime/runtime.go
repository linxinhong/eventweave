package runtime

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"
	"time"

	segmentio "github.com/segmentio/kafka-go"

	"github.com/linxinhong/eventweave/runtime-go/internal/clock"
	"github.com/linxinhong/eventweave/runtime-go/internal/config"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/loader"
	"github.com/linxinhong/eventweave/runtime-go/internal/ratelimit"
	"github.com/linxinhong/eventweave/runtime-go/internal/scheduler"
	"github.com/linxinhong/eventweave/runtime-go/internal/sink"
	fileSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/file"
	httpSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/http"
	kafkaSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/kafka"
	nullSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/null"
	stdoutSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/stdout"
	syslogSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/syslog"
	"github.com/linxinhong/eventweave/runtime-go/internal/stats"
	"github.com/linxinhong/eventweave/runtime-go/internal/worker"
)

// LocalRuntime replays an event plan through a sink.
type LocalRuntime struct {
	cfg    config.RuntimeConfig
	sink   sink.Sink
	target string
}

// New creates a runtime from config in run mode.
func New(cfg config.RuntimeConfig) (*LocalRuntime, error) {
	return NewWithMode(cfg, "run")
}

// NewWithMode creates a runtime from config with the given mode label.
func NewWithMode(cfg config.RuntimeConfig, mode string) (*LocalRuntime, error) {
	if err := cfg.Validate(); err != nil {
		return nil, err
	}

	var s sink.Sink
	target := cfg.Sink
	switch cfg.Sink {
	case "stdout":
		s = stdoutSink.New()
	case "file":
		if err := fileSink.ValidatePath(cfg.Output, cfg.OutputDir); err != nil {
			return nil, err
		}
		s = fileSink.New(cfg.Output, cfg.OutputDir)
		target = cfg.Output
	case "null":
		s = nullSink.New()
	case "http":
		if err := httpSink.IsSafeURL(cfg.URL, cfg.AllowInternalURL); err != nil {
			return nil, err
		}
		hs, err := httpSink.New(cfg.URL, cfg.Timeout, cfg.MaxRetryDuration, cfg.Retries, cfg.BackoffFactor, cfg.AllowInternalURL)
		if err != nil {
			return nil, err
		}
		s = hs
		target = cfg.URL
	case "kafka":
		if cfg.BatchSize > 1 {
			writer := segmentio.NewWriter(segmentio.WriterConfig{
				Brokers: strings.Split(cfg.Brokers, ","),
				Topic:   cfg.Topic,
				Async:   false,
			})
			s = kafkaSink.NewBatchWithMode(
				writer,
				kafkaSink.KeyFunc(cfg.KeyField),
				cfg.BatchSize,
				cfg.BatchTimeout,
				cfg.Timeout,
				cfg.Retries,
				mode,
			)
		} else {
			s = kafkaSink.New(cfg.Brokers, cfg.Topic, cfg.KeyField, cfg.Timeout, cfg.Retries)
		}
		target = fmt.Sprintf("%s/%s", cfg.Brokers, cfg.Topic)
	case "syslog":
		s = syslogSink.New(cfg.SyslogAddr, cfg.SyslogProto, cfg.Facility, cfg.Severity, cfg.Tag)
		target = fmt.Sprintf("%s://%s", cfg.SyslogProto, cfg.SyslogAddr)
	}

	// Wrap kafka and http sinks in a worker pool when workers > 1.
	if cfg.Workers > 1 && (cfg.Sink == "kafka" || cfg.Sink == "http") {
		s = worker.NewWithMode(mode, cfg.Sink, cfg.Workers, cfg.QueueSize, cfg.OnQueueFull, s)
	}

	return &LocalRuntime{cfg: cfg, sink: s, target: target}, nil
}

// Target returns the human-readable sink destination.
func (r *LocalRuntime) Target() string { return r.target }

// Run executes the event plan and returns stats.
func (r *LocalRuntime) Run() (*stats.RuntimeStats, error) {
	return r.RunWithContext(context.Background())
}

// RunWithContext executes the event plan with cancellation support.
func (r *LocalRuntime) RunWithContext(ctx context.Context) (*stats.RuntimeStats, error) {
	events, err := loader.LoadEventPlan(filepath.Join(r.cfg.PlanDir, "event_plan.jsonl"))
	if err != nil {
		return nil, err
	}

	st := stats.New()
	st.LoadedEvents = len(events)
	st.UnresolvedRefs = countUnresolvedRefs(events)

	sorted := scheduler.SortEvents(events)
	if r.cfg.Limit > 0 && len(sorted) > r.cfg.Limit {
		sorted = sorted[:r.cfg.Limit]
	}

	if len(sorted) == 0 {
		st.Finish(r.cfg.Sink, r.target)
		return st, nil
	}

	first, last := sorted[0].EventTime, sorted[len(sorted)-1].EventTime
	st.FirstEventTime = &first
	st.LastEventTime = &last

	limiter, clk, err := r.buildLimiter(sorted[0].EventTime)
	if err != nil {
		return nil, err
	}

	if err := r.sink.Open(); err != nil {
		return nil, fmt.Errorf("open sink: %w", err)
	}
	defer r.sink.Close()

	for _, ev := range sorted {
		if err := ctx.Err(); err != nil {
			st.Finish(r.cfg.Sink, r.target)
			return st, err
		}
		if err := r.wait(ctx, limiter, clk, ev.EventTime); err != nil {
			if err == context.Canceled {
				st.Finish(r.cfg.Sink, r.target)
				return st, nil
			}
			return nil, err
		}
		if err := r.sink.Write(ev); err != nil {
			st.Failed++
			if r.cfg.MaxFailures > 0 && st.Failed >= r.cfg.MaxFailures {
				break
			}
			continue
		}
		st.Emitted++
	}

	_ = r.sink.Flush()
	st.Failed += r.sink.Failed()
	st.Finish(r.cfg.Sink, r.target)
	return st, nil
}

func (r *LocalRuntime) buildLimiter(start time.Time) (ratelimit.Limiter, *clock.RuntimeClock, error) {
	if r.cfg.NoWait {
		return &ratelimit.NoWaitLimiter{}, nil, nil
	}
	if r.cfg.Rate > 0 {
		lim, err := ratelimit.NewRateLimiter(r.cfg.Rate)
		if err != nil {
			return nil, nil, err
		}
		return lim, nil, nil
	}
	clk, err := clock.New(start, r.cfg.Speed, false)
	if err != nil {
		return nil, nil, err
	}
	return nil, clk, nil
}

func (r *LocalRuntime) wait(
	ctx context.Context,
	limiter ratelimit.Limiter,
	clk *clock.RuntimeClock,
	target time.Time,
) error {
	if limiter != nil {
		return limiter.Wait(ctx)
	}
	if clk != nil {
		return clk.WaitUntil(ctx, target)
	}
	return nil
}

func countUnresolvedRefs(events []event.Event) int {
	count := 0
	for _, ev := range events {
		for _, ref := range ev.SemanticRefs {
			if strings.HasPrefix(ref, "semantic://") {
				count++
				break
			}
		}
	}
	return count
}
