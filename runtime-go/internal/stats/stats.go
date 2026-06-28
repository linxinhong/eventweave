package stats

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

// RuntimeStats summarizes a runtime execution.
type RuntimeStats struct {
	LoadedEvents   int        `json:"loaded_events"`
	Emitted        int        `json:"emitted"`         // succeeded writes
	Failed         int        `json:"failed"`          // failed writes
	UnresolvedRefs int        `json:"unresolved_refs"`
	ThroughputEPS  float64    `json:"throughput_eps"`
	Sink           string     `json:"sink"`
	Target         string     `json:"target"`
	FirstEventTime *time.Time `json:"first_event_time,omitempty"`
	LastEventTime  *time.Time `json:"last_event_time,omitempty"`
	StartTime      time.Time  `json:"start_time"`
	EndTime        *time.Time `json:"end_time,omitempty"`
}

// New creates initialized stats.
func New() *RuntimeStats {
	return &RuntimeStats{StartTime: time.Now()}
}

// Finish marks the runtime as finished and computes derived fields.
func (s *RuntimeStats) Finish(sink, target string) {
	now := time.Now()
	s.EndTime = &now
	s.Sink = sink
	s.Target = target
	d := s.Duration().Seconds()
	if d > 0 {
		s.ThroughputEPS = float64(s.Emitted) / d
	}
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
func (s *RuntimeStats) Print() {
	fmt.Println("Runtime finished")
	fmt.Printf("Events loaded: %d\n", s.LoadedEvents)
	fmt.Printf("Events emitted: %d\n", s.Emitted)
	if s.Failed > 0 {
		fmt.Printf("Events failed: %d\n", s.Failed)
	}
	fmt.Printf("Duration: %.3fs\n", s.Duration().Seconds())
	fmt.Printf("Throughput: %.0f events/sec\n", s.ThroughputEPS)
	fmt.Printf("Sink: %s", s.Sink)
	if s.Target != "" && s.Target != s.Sink {
		fmt.Printf(" (%s)", s.Target)
	}
	fmt.Println()
}

// PrintBenchmark outputs stats in a concise benchmark format.
func (s *RuntimeStats) PrintBenchmark() {
	fmt.Println("Benchmark finished")
	fmt.Printf("Events: %d\n", s.LoadedEvents)
	fmt.Printf("Succeeded: %d\n", s.Emitted)
	fmt.Printf("Failed: %d\n", s.Failed)
	fmt.Printf("Duration: %.3fs\n", s.Duration().Seconds())
	fmt.Printf("Throughput: %.0f events/sec\n", s.ThroughputEPS)
	fmt.Printf("Sink: %s", s.Sink)
	if s.Target != "" && s.Target != s.Sink {
		fmt.Printf(" (%s)", s.Target)
	}
	fmt.Println()
}

// WriteJSON writes stats to a JSON file.
func (s *RuntimeStats) WriteJSON(path string) error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0o644)
}
