package security

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestSuricataEVE(t *testing.T) {
	enc := SuricataEVE{}
	ev := event.Event{
		EventID:   "evt-001",
		ScenarioID: "test",
		SourceID:  "sensor",
		EventType: "alert",
		EventTime: time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
		Attributes: map[string]any{
			"event_type": "alert",
			"src_ip":     "10.0.0.1",
			"dest_ip":    "10.0.0.2",
			"src_port":   12345,
			"dest_port":  80,
			"proto":      "TCP",
		},
	}
	data, err := enc.Encode(ev)
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	var record map[string]any
	if err := json.Unmarshal(data, &record); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if record["event_type"] != "alert" {
		t.Errorf("unexpected event_type: %v", record["event_type"])
	}
}

func TestSuricataEVEMissingFields(t *testing.T) {
	enc := SuricataEVE{}
	ev := event.Event{
		EventID:   "evt-001",
		ScenarioID: "test",
		SourceID:  "sensor",
		EventType: "alert",
		EventTime: time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
	}
	if _, err := enc.Encode(ev); err == nil {
		t.Fatal("expected error for missing fields")
	}
}
