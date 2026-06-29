package stdout

import (
	"encoding/json"
	"fmt"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// Sink prints events as JSON lines or encoded lines.
type Sink struct {
	enc    encoder.Encoder
	count  int
	failed int
}

// New creates a stdout sink.
func New(enc ...encoder.Encoder) *Sink {
	s := &Sink{}
	if len(enc) > 0 {
		s.enc = enc[0]
	}
	return s
}

// Open initializes the sink.
func (s *Sink) Open() error { return nil }

// Write prints one event.
func (s *Sink) Write(ev event.Event) error {
	var data []byte
	var err error
	if s.enc != nil {
		data, err = s.enc.Encode(ev)
	} else {
		data, err = json.Marshal(ev)
	}
	if err != nil {
		s.failed++
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

// Failed returns failed writes.
func (s *Sink) Failed() int { return s.failed }
