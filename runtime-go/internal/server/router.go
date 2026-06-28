package server

import (
	"strings"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// Match returns true if the event satisfies all non-empty filter fields.
func (f SourceFilter) Match(ev event.Event) bool {
	if f.SourceID != "" && !strings.EqualFold(f.SourceID, ev.SourceID) {
		return false
	}
	if f.EventType != "" && !strings.EqualFold(f.EventType, ev.EventType) {
		return false
	}
	return true
}
