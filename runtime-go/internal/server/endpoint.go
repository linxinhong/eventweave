package server

import (
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// Endpoint is a protocol-specific server output.
type Endpoint interface {
	// ID returns the configured endpoint identifier.
	ID() string
	// Open starts the listener.
	Open() error
	// Close stops the listener and cleans up resources.
	Close() error
	// Write delivers an event to connected consumers.
	Write(ev event.Event) error
	// Stats returns per-endpoint counters.
	Stats() EndpointStats
}
