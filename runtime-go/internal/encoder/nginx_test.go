package encoder

import (
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestNginxAccessEncoder(t *testing.T) {
	enc := NginxAccess{}
	ev := event.Event{
		EventID:   "evt-001",
		ScenarioID: "test",
		SourceID:  "nginx",
		EventType: "http.request",
		EventTime: time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
		Attributes: map[string]any{
			"remote_addr":     "192.168.1.1",
			"request":         "GET / HTTP/1.1",
			"status":          200,
			"body_bytes_sent": 42,
		},
	}
	data, err := enc.Encode(ev)
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	out := string(data)
	if !strings.HasPrefix(out, `192.168.1.1 - - [29/Jun/2026:12:00:00 +0000]`) {
		t.Errorf("unexpected nginx output: %s", out)
	}
	if !strings.Contains(out, `"GET / HTTP/1.1" 200 42`) {
		t.Errorf("missing request/status/bytes: %s", out)
	}
}

func TestNginxAccessEncoderMissingFields(t *testing.T) {
	enc := NginxAccess{}
	ev := event.Event{
		EventID:   "evt-001",
		ScenarioID: "test",
		SourceID:  "nginx",
		EventType: "http.request",
		EventTime: time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
		Attributes: map[string]any{
			"remote_addr": "192.168.1.1",
		},
	}
	if _, err := enc.Encode(ev); err == nil {
		t.Fatal("expected error for missing fields")
	}
}
