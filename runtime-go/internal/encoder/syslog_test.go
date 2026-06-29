package encoder

import (
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func makeSyslogEvent() event.Event {
	return event.Event{
		EventID:   "evt-001",
		ScenarioID: "test",
		SourceID:  "svc",
		EventType: "test.event",
		EventTime: time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
		Attributes: map[string]any{
			"syslog_facility": 16,
			"syslog_severity": 6,
			"hostname":        "host01",
			"syslog_tag":      "app",
			"message":         "hello",
		},
	}
}

func TestRFC3164(t *testing.T) {
	enc := RFC3164{}
	data, err := enc.Encode(makeSyslogEvent())
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	out := string(data)
	if !strings.HasPrefix(out, "<134>") {
		t.Errorf("expected priority 134, got %s", out)
	}
	if !strings.Contains(out, "host01 app: hello") {
		t.Errorf("unexpected syslog output: %s", out)
	}
}

func TestRFC5424(t *testing.T) {
	enc := RFC5424{}
	data, err := enc.Encode(makeSyslogEvent())
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	out := string(data)
	if !strings.HasPrefix(out, "<134>1 2026-06-29T12:00:00.000000Z host01 svc") {
		t.Errorf("unexpected rfc5424 output: %s", out)
	}
}
