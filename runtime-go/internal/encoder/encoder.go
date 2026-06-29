// Package encoder transforms canonical EventWeave events into vendor/log formats.
package encoder

import (
	"fmt"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// Encoder converts a canonical event into a vendor-specific byte representation.
type Encoder interface {
	Name() string
	ContentType() string
	Encode(ev event.Event) ([]byte, error)
}

// EncodeError indicates that an event could not be encoded.
type EncodeError struct {
	Reason string
}

func (e *EncodeError) Error() string {
	return fmt.Sprintf("encode failed: %s", e.Reason)
}

// NewEncodeError returns an encode error with the given reason.
func NewEncodeError(reason string) *EncodeError {
	return &EncodeError{Reason: reason}
}
