package security

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestWindowsEventJSON(t *testing.T) {
	enc := WindowsEventJSON{}
	ev := event.Event{
		EventID:   "evt-001",
		ScenarioID: "test",
		SourceID:  "host01",
		EventType: "security",
		EventTime: time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
		Attributes: map[string]any{
			"EventID":      4624,
			"ProviderName": "Microsoft-Windows-Security-Auditing",
			"TargetUserName": "alice",
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
	sys := record["Event"].(map[string]any)["System"].(map[string]any)
	if sys["EventID"] != float64(4624) {
		t.Errorf("unexpected EventID: %v", sys["EventID"])
	}
}

func TestWindowsEventJSONMissingEventID(t *testing.T) {
	enc := WindowsEventJSON{}
	ev := event.Event{
		EventID:   "evt-001",
		ScenarioID: "test",
		SourceID:  "host01",
		EventType: "security",
		EventTime: time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
	}
	if _, err := enc.Encode(ev); err == nil {
		t.Fatal("expected error for missing EventID")
	}
}
