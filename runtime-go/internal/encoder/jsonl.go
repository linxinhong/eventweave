package encoder

import (
	"encoding/json"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// JSONL returns the canonical JSON representation of an event.
type JSONL struct{}

func init() {
	Register("jsonl", JSONL{})
}

// Name returns the encoder name.
func (JSONL) Name() string { return "jsonl" }

// ContentType returns the MIME type of the encoded output.
func (JSONL) ContentType() string { return "application/x-ndjson" }

// Encode marshals the event to JSON.
func (JSONL) Encode(ev event.Event) ([]byte, error) {
	return json.Marshal(ev)
}
