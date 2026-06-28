package loader

import (
	"os"
	"path/filepath"
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
