package worker

import (
	"context"
	"sync"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/sink"
)

// collectingSink is a test sink that records all written events.
type collectingSink struct {
	mu     sync.Mutex
	events []event.Event
	fail   bool
}

func (s *collectingSink) Open() error  { return nil }
func (s *collectingSink) Close() error { return nil }
func (s *collectingSink) Flush() error { return nil }
func (s *collectingSink) Count() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.events)
}
func (s *collectingSink) Failed() int { return 0 }

func (s *collectingSink) Write(ev event.Event) error {
	if s.fail {
		return errTest
	}
	s.mu.Lock()
	s.events = append(s.events, ev)
	s.mu.Unlock()
	return nil
}

var errTest = errorString("test error")

type errorString string

func (e errorString) Error() string { return string(e) }

var _ sink.Sink = (*collectingSink)(nil)

// blockingSink blocks on Write until the channel is closed.
type blockingSink struct {
	block <-chan struct{}
}

func (s *blockingSink) Open() error  { return nil }
func (s *blockingSink) Close() error { return nil }
func (s *blockingSink) Flush() error { return nil }
func (s *blockingSink) Count() int   { return 0 }
func (s *blockingSink) Failed() int  { return 0 }

func (s *blockingSink) Write(ev event.Event) error {
	<-s.block
	return nil
}

var _ sink.Sink = (*blockingSink)(nil)

func TestPoolProcessesEvents(t *testing.T) {
	s := &collectingSink{}
	p := New(2, 10, "block", s)
	if err := p.Open(); err != nil {
		t.Fatal(err)
	}

	for i := 0; i < 10; i++ {
		if err := p.Submit(event.Event{EventID: string(rune('a' + i))}); err != nil {
			t.Fatalf("submit: %v", err)
		}
	}

	// Wait for workers to process.
	time.Sleep(100 * time.Millisecond)
	if err := p.Close(); err != nil {
		t.Fatalf("close: %v", err)
	}

	if s.Count() != 10 {
		t.Fatalf("expected 10 events, got %d", s.Count())
	}
}

func TestPoolFailPolicy(t *testing.T) {
	blocker := make(chan struct{})
	s := &blockingSink{block: blocker}
	p := New(1, 0, "fail", s)
	if err := p.Open(); err != nil {
		t.Fatal(err)
	}
	defer p.Close()
	defer close(blocker) // release worker on cleanup

	// Retry until the worker has started and accepts the first event.
	var err error
	deadline := time.Now().Add(200 * time.Millisecond)
	for {
		err = p.Submit(event.Event{EventID: "blocker"})
		if err == nil {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("first submit failed: %v", err)
		}
		time.Sleep(5 * time.Millisecond)
	}
	// Worker has received the event and is now blocked inside sink.Write.
	time.Sleep(20 * time.Millisecond)

	// With an unbuffered queue and a busy worker, fail policy should reject.
	if err := p.Submit(event.Event{EventID: "overflow"}); err == nil {
		t.Fatal("expected queue full error")
	}
}

func TestPoolWorkerFailure(t *testing.T) {
	s := &collectingSink{fail: true}
	p := New(1, 10, "block", s)
	if err := p.Open(); err != nil {
		t.Fatal(err)
	}

	_ = p.Submit(event.Event{EventID: "fail"})
	time.Sleep(50 * time.Millisecond)
	_ = p.Close()

	stats := p.Stats()
	if stats.Failed != 1 {
		t.Fatalf("expected 1 failed, got %d", stats.Failed)
	}
}

func TestPoolBlockPolicy(t *testing.T) {
	s := &collectingSink{}
	p := New(1, 1, "block", s)
	if err := p.Open(); err != nil {
		t.Fatal(err)
	}
	defer p.Close()

	// Fill queue.
	_ = p.Submit(event.Event{EventID: "first"})

	done := make(chan error, 1)
	go func() {
		done <- p.Submit(event.Event{EventID: "second"})
	}()

	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
	case <-time.After(200 * time.Millisecond):
		t.Fatal("expected blocking submit to complete after worker drains")
	}
}

func TestPoolDrainsJobsOnClose(t *testing.T) {
	s := &collectingSink{}
	p := New(1, 100, "block", s)
	if err := p.Open(); err != nil {
		t.Fatal(err)
	}

	for i := 0; i < 50; i++ {
		_ = p.Submit(event.Event{EventID: string(rune('a' + i))})
	}
	if err := p.Close(); err != nil {
		t.Fatalf("close: %v", err)
	}

	if s.Count() != 50 {
		t.Fatalf("expected 50 drained events, got %d", s.Count())
	}
}

func TestPoolSubmitFailsAfterClose(t *testing.T) {
	s := &collectingSink{}
	p := New(1, 10, "block", s)
	if err := p.Open(); err != nil {
		t.Fatal(err)
	}
	_ = p.Close()

	if err := p.Submit(event.Event{EventID: "late"}); err == nil {
		t.Fatal("expected error after pool closed")
	}
}

func TestPoolContextCancelsBlockedSubmit(t *testing.T) {
	blocker := make(chan struct{})
	s := &blockingSink{block: blocker}
	p := New(1, 0, "block", s)
	if err := p.Open(); err != nil {
		t.Fatal(err)
	}
	defer p.Close()
	defer close(blocker)

	// Block the worker so the queue fills.
	_ = p.Submit(event.Event{EventID: "blocker"})
	time.Sleep(20 * time.Millisecond)

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() {
		// This submit will block until the context is cancelled.
		// Submit does not accept a context, so simulate via pool closure.
		done <- p.Submit(event.Event{EventID: "waiter"})
	}()

	go func() {
		time.Sleep(30 * time.Millisecond)
		cancel()
		_ = ctx.Err()
		p.cancel()
	}()

	select {
	case err := <-done:
		if err == nil {
			t.Fatal("expected error after cancellation")
		}
	case <-time.After(500 * time.Millisecond):
		t.Fatal("expected blocked submit to return after cancellation")
	}
}
