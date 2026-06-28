package metrics

import (
	"github.com/linxinhong/eventweave/runtime-go/internal/stats"
)

// RecordRuntimeStats records all metrics for run or bench mode.
func RecordRuntimeStats(mode, sink string, st *stats.RuntimeStats) {
	RecordEventsLoaded(mode, st.LoadedEvents)
	RecordUnresolvedRefs(mode, st.UnresolvedRefs)
	for i := 0; i < st.Emitted; i++ {
		RecordEventEmitted(mode, sink, "", "", "success")
	}
	for i := 0; i < st.Failed; i++ {
		RecordEventFailed(mode, sink, "", "")
		RecordEventEmitted(mode, sink, "", "", "failed")
	}
	SetThroughput(mode, sink, st.ThroughputEPS)
	SetDuration(mode, sink, st.Duration().Seconds())
}
