package runtime

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/linxinhong/eventweave/runtime-go/internal/clock"
	"github.com/linxinhong/eventweave/runtime-go/internal/config"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/loader"
	"github.com/linxinhong/eventweave/runtime-go/internal/scheduler"
	"github.com/linxinhong/eventweave/runtime-go/internal/sink"
	fileSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/file"
	httpSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/http"
	nullSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/null"
	stdoutSink "github.com/linxinhong/eventweave/runtime-go/internal/sinks/stdout"
	"github.com/linxinhong/eventweave/runtime-go/internal/stats"
)

// LocalRuntime replays an event plan through a sink.
type LocalRuntime struct {
	cfg  config.RuntimeConfig
	sink sink.Sink
}

// New creates a runtime from config.
func New(cfg config.RuntimeConfig) (*LocalRuntime, error) {
	if err := cfg.Validate(); err != nil {
		return nil, err
	}

	var s sink.Sink
	switch cfg.Sink {
	case "stdout":
		s = stdoutSink.New()
	case "file":
		s = fileSink.New(cfg.Output)
	case "null":
		s = nullSink.New()
	case "http":
		s = httpSink.New(cfg.URL, cfg.Timeout, cfg.Retries)
	}

	return &LocalRuntime{cfg: cfg, sink: s}, nil
}

// Run executes the event plan and returns stats.
func (r *LocalRuntime) Run() (*stats.RuntimeStats, error) {
	events, err := loader.LoadEventPlan(filepath.Join(r.cfg.PlanDir, "event_plan.jsonl"))
	if err != nil {
		return nil, err
	}

	stats := stats.New()
	stats.UnresolvedRefs = countUnresolvedRefs(events)

	sorted := scheduler.SortEvents(events)
	if r.cfg.Limit > 0 && len(sorted) > r.cfg.Limit {
		sorted = sorted[:r.cfg.Limit]
	}

	if len(sorted) == 0 {
		stats.Finish()
		return stats, nil
	}

	clk, err := clock.New(sorted[0].EventTime, r.cfg.Speed, r.cfg.NoWait)
	if err != nil {
		return nil, err
	}

	if err := r.sink.Open(); err != nil {
		return nil, fmt.Errorf("open sink: %w", err)
	}
	defer r.sink.Close()

	for _, ev := range sorted {
		clk.WaitUntil(ev.EventTime)
		if err := r.sink.Write(ev); err != nil {
			stats.Failed++
			continue
		}
		stats.Emitted++
	}

	_ = r.sink.Flush()
	stats.Finish()
	return stats, nil
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
