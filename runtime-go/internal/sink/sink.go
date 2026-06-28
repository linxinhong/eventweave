package sink

import "github.com/linxinhong/eventweave/runtime-go/internal/event"

// Sink is a destination for emitted events.
type Sink interface {
	Open() error
	Write(ev event.Event) error
	Flush() error
	Close() error
	Count() int
	Failed() int
}
