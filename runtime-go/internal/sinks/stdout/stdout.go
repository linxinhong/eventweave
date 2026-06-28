package stdout

import (
	"encoding/json"
	"fmt"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// Sink prints events as JSON lines.
type Sink struct {
	count int
}

// New creates a stdout sink.
func New() *Sink { return &Sink{} }

// Open initializes the sink.
func (s *Sink) Open() error { return nil }

// Write prints one event.
func (s *Sink) Write(ev event.Event) error {
	data, err := json.Marshal(ev)
	if err != nil {
		return err
	}
	fmt.Println(string(data))
	s.count++
	return nil
}

// Flush is a no-op for stdout.
func (s *Sink) Flush() error { return nil }

// Close is a no-op for stdout.
func (s *Sink) Close() error { return nil }

// Count returns emitted events.
func (s *Sink) Count() int { return s.count }

// Failed always returns 0.
func (s *Sink) Failed() int { return 0 }
