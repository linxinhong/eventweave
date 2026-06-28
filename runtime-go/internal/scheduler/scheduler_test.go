package scheduler

import (
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestSortEvents(t *testing.T) {
	base := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	events := []event.Event{
		{EventID: "b", EventTime: base},
		{EventID: "a", EventTime: base},
		{EventID: "c", EventTime: base.Add(time.Second)},
	}
	sorted := SortEvents(events)
	if sorted[0].EventID != "a" || sorted[1].EventID != "b" || sorted[2].EventID != "c" {
		t.Fatalf("unexpected order: %+v", sorted)
	}
}
