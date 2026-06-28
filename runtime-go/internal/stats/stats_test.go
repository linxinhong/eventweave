package stats

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestStatsFinishComputesThroughput(t *testing.T) {
	s := New()
	s.LoadedEvents = 100
	s.Emitted = 95
	s.Failed = 5
	time.Sleep(50 * time.Millisecond)
	s.Finish("null", "null")

	if s.Duration().Seconds() <= 0 {
		t.Fatal("expected positive duration")
	}
	if s.ThroughputEPS <= 0 {
		t.Fatalf("expected positive throughput, got %f", s.ThroughputEPS)
	}
	expected := float64(s.Emitted) / s.Duration().Seconds()
	if diff := s.ThroughputEPS - expected; diff < -0.1 || diff > 0.1 {
		t.Fatalf("throughput mismatch: got %f, want %f", s.ThroughputEPS, expected)
	}
}

func TestStatsWriteJSON(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "stats.json")

	s := New()
	s.LoadedEvents = 10
	s.Emitted = 9
	s.Failed = 1
	s.Sink = "null"
	s.Target = "null"
	time.Sleep(10 * time.Millisecond)
	s.Finish("null", "null")

	if err := s.WriteJSON(path); err != nil {
		t.Fatalf("write json: %v", err)
	}

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read json: %v", err)
	}
	var decoded RuntimeStats
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal json: %v", err)
	}
	if decoded.LoadedEvents != 10 {
		t.Fatalf("loaded events mismatch: %d", decoded.LoadedEvents)
	}
	if decoded.Emitted != 9 {
		t.Fatalf("emitted mismatch: %d", decoded.Emitted)
	}
	if decoded.Failed != 1 {
		t.Fatalf("failed mismatch: %d", decoded.Failed)
	}
	if decoded.Sink != "null" {
		t.Fatalf("sink mismatch: %s", decoded.Sink)
	}
}
