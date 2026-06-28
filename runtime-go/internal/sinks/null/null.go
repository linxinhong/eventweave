package null

import "github.com/linxinhong/eventweave/runtime-go/internal/event"

// Sink counts events without writing them.
type Sink struct {
	count int
}

// New creates a null sink.
func New() *Sink { return &Sink{} }

// Open initializes the sink.
func (s *Sink) Open() error { return nil }

// Write increments the counter.
func (s *Sink) Write(ev event.Event) error {
	s.count++
	return nil
}

// Flush is a no-op.
func (s *Sink) Flush() error { return nil }

// Close is a no-op.
func (s *Sink) Close() error { return nil }

// Count returns counted events.
func (s *Sink) Count() int { return s.count }

// Failed always returns 0.
func (s *Sink) Failed() int { return 0 }
