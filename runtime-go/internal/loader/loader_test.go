package loader

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadEventPlan(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "event_plan.jsonl")
	content := `{"event_id":"e1","scenario_id":"sc1","source_id":"src1","event_type":"login","event_time":"2024-01-01T00:00:00Z","entity_refs":{},"attributes":{},"semantic_refs":[],"labels":[],"ground_truth":{}}
{"event_id":"e2","scenario_id":"sc1","source_id":"src1","event_type":"logout","event_time":"2024-01-01T00:00:01Z","entity_refs":{},"attributes":{},"semantic_refs":[],"labels":[],"ground_truth":{}}
`
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write fixture: %v", err)
	}

	events, err := LoadEventPlan(path)
	if err != nil {
		t.Fatalf("load event plan: %v", err)
	}
	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}
	if events[0].EventID != "e1" {
		t.Fatalf("unexpected event id: %s", events[0].EventID)
	}
}

func TestLoadEventPlanNotFound(t *testing.T) {
	_, err := LoadEventPlan(filepath.Join(t.TempDir(), "missing.jsonl"))
	if err == nil {
		t.Fatal("expected error for missing file")
	}
}
func TestLoadEventPlanSupportsLargeRecords(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "event_plan.jsonl")

	largePayload := strings.Repeat("x", 200_000)
	content := fmt.Sprintf(
		`{"event_id":"e1","scenario_id":"sc1","source_id":"src1","event_type":"login","event_time":"2024-01-01T00:00:00Z","entity_refs":{},"attributes":{"payload":%q},"semantic_refs":[],"labels":[],"ground_truth":{}}`+"\n",
		largePayload,
	)
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write fixture: %v", err)
	}

	events, err := LoadEventPlan(path)
	if err != nil {
		t.Fatalf("load event plan: %v", err)
	}
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}
	got := events[0].Attributes["payload"]
	if got != largePayload {
		t.Fatalf("large payload mismatch: got %d bytes, want %d", len(got.(string)), len(largePayload))
	}
}
