package stats

import (
	"fmt"
	"time"
)

// RuntimeStats summarizes a runtime execution.
type RuntimeStats struct {
	Emitted         int
	Failed          int
	UnresolvedRefs  int
	StartTime       time.Time
	EndTime         *time.Time
}

// New creates initialized stats.
func New() *RuntimeStats {
	return &RuntimeStats{StartTime: time.Now()}
}

// Finish marks the runtime as finished.
func (s *RuntimeStats) Finish() {
	now := time.Now()
	s.EndTime = &now
}

// Duration returns elapsed real time.
func (s *RuntimeStats) Duration() time.Duration {
	end := s.EndTime
	if end == nil {
		now := time.Now()
		end = &now
	}
	return end.Sub(s.StartTime)
}

// Print outputs the stats in a human-readable format.
func (s *RuntimeStats) Print(sinkName, target string) {
	fmt.Println("Runtime finished")
	fmt.Printf("Events emitted: %d\n", s.Emitted)
	if s.Failed > 0 {
		fmt.Printf("Events failed: %d\n", s.Failed)
	}
	fmt.Printf("Duration: %.3fs\n", s.Duration().Seconds())
	fmt.Printf("Sink: %s", sinkName)
	if target != "" && target != sinkName {
		fmt.Printf(" (%s)", target)
	}
	fmt.Println()
}
