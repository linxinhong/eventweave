package scheduler

import (
	"sort"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// SortEvents returns events ordered by event_time then event_id.
func SortEvents(events []event.Event) []event.Event {
	sorted := make([]event.Event, len(events))
	copy(sorted, events)
	sort.SliceStable(sorted, func(i, j int) bool {
		timeA, idA := sorted[i].SortKey()
		timeB, idB := sorted[j].SortKey()
		if !timeA.Equal(timeB) {
			return timeA.Before(timeB)
		}
		return idA < idB
	})
	return sorted
}
