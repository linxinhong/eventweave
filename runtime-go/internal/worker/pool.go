// Package worker provides a bounded worker pool for concurrent sink writes.
package worker

import (
	"context"
	"fmt"
	"strconv"
	"sync"
	"sync/atomic"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/metrics"
	"github.com/linxinhong/eventweave/runtime-go/internal/sink"
)

// PoolStats holds runtime counters for the worker pool.
type PoolStats struct {
	Submitted int64
	Processed int64
	Failed    int64
}

// Pool distributes events across a fixed number of workers.
type Pool struct {
	mode      string
	sinkName  string
	workers   int
	queueSize int
	onFull    string
	sink      sink.Sink

	jobs   chan event.Event
	wg     sync.WaitGroup
	ctx    context.Context
	cancel context.CancelFunc

	stats PoolStats
}

// New creates a worker pool that writes to the given sink.
func New(workers, queueSize int, onFull string, s sink.Sink) *Pool {
	return NewWithMode("run", "", workers, queueSize, onFull, s)
}

// NewWithMode creates a worker pool with mode and sink labels for metrics.
func NewWithMode(mode, sinkName string, workers, queueSize int, onFull string, s sink.Sink) *Pool {
	ctx, cancel := context.WithCancel(context.Background())
	return &Pool{
		mode:      mode,
		sinkName:  sinkName,
		workers:   workers,
		queueSize: queueSize,
		onFull:    onFull,
		sink:      s,
		jobs:      make(chan event.Event, queueSize),
		ctx:       ctx,
		cancel:    cancel,
	}
}

// Open starts the workers and opens the underlying sink.
func (p *Pool) Open() error {
	if err := p.sink.Open(); err != nil {
		return fmt.Errorf("open sink: %w", err)
	}

	for i := 0; i < p.workers; i++ {
		p.wg.Add(1)
		go p.runWorker(i)
	}
	return nil
}

// Close stops the pool, drains remaining jobs, flushes and closes the sink.
func (p *Pool) Close() error {
	p.cancel()
	close(p.jobs)
	p.wg.Wait()
	_ = p.sink.Flush()
	return p.sink.Close()
}

// Submit enqueues an event for a worker. Behavior when the queue is full
// depends on the configured onFull policy.
func (p *Pool) Submit(ev event.Event) error {
	atomic.AddInt64(&p.stats.Submitted, 1)
	metrics.SetQueueDepth(p.mode, p.sinkName, float64(len(p.jobs)))

	if p.onFull == "fail" {
		select {
		case p.jobs <- ev:
			return nil
		default:
			atomic.AddInt64(&p.stats.Failed, 1)
			return fmt.Errorf("worker queue full")
		}
	}

	// block policy
	select {
	case p.jobs <- ev:
		return nil
	case <-p.ctx.Done():
		atomic.AddInt64(&p.stats.Failed, 1)
		return fmt.Errorf("pool closed")
	}
}

// Write is a convenience alias for Submit to implement the sink interface.
func (p *Pool) Write(ev event.Event) error {
	return p.Submit(ev)
}

// Flush flushes the underlying sink.
func (p *Pool) Flush() error {
	return p.sink.Flush()
}

// Count returns the number of successfully processed events.
func (p *Pool) Count() int {
	return int(atomic.LoadInt64(&p.stats.Processed))
}

// Failed returns the number of failed events.
func (p *Pool) Failed() int {
	return int(atomic.LoadInt64(&p.stats.Failed))
}

// Stats returns a snapshot of pool counters.
func (p *Pool) Stats() PoolStats {
	return PoolStats{
		Submitted: atomic.LoadInt64(&p.stats.Submitted),
		Processed: atomic.LoadInt64(&p.stats.Processed),
		Failed:    atomic.LoadInt64(&p.stats.Failed),
	}
}

// QueueDepth returns the current number of events waiting in the queue.
func (p *Pool) QueueDepth() int {
	return len(p.jobs)
}

func (p *Pool) runWorker(id int) {
	defer p.wg.Done()
	workerID := strconv.Itoa(id)

	for {
		select {
		case ev, ok := <-p.jobs:
			if !ok {
				return
			}
			p.processEvent(ev, workerID)
		case <-p.ctx.Done():
			// Drain remaining jobs before exiting.
			for ev := range p.jobs {
				p.processEvent(ev, workerID)
			}
			return
		}
	}
}

func (p *Pool) processEvent(ev event.Event, workerID string) {
	if err := p.sink.Write(ev); err != nil {
		atomic.AddInt64(&p.stats.Failed, 1)
		metrics.RecordWorkerFailure(p.mode, p.sinkName, workerID)
		metrics.RecordWorkerEvent(p.mode, p.sinkName, workerID, "failed")
	} else {
		atomic.AddInt64(&p.stats.Processed, 1)
		metrics.RecordWorkerEvent(p.mode, p.sinkName, workerID, "success")
	}
	metrics.SetQueueDepth(p.mode, p.sinkName, float64(len(p.jobs)))
}
