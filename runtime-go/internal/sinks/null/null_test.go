package null

import (
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestNullSinkCountsEvents(t *testing.T) {
	sink := New()
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	ev := event.Event{EventID: "e1", EventTime: time.Now()}
	if err := sink.Write(ev); err != nil {
		t.Fatalf("write: %v", err)
	}
	if sink.Count() != 1 {
		t.Fatalf("expected count 1, got %d", sink.Count())
	}
	if sink.Failed() != 0 {
		t.Fatalf("expected failed 0, got %d", sink.Failed())
	}
}
