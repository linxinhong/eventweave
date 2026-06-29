package encoder

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func syslogPriority(ev event.Event) int {
	facility, _ := ev.Attributes["syslog_facility"].(int)
	if facility == 0 {
		facility = 16
	}
	severity, _ := ev.Attributes["syslog_severity"].(int)
	if severity == 0 {
		severity = 6
	}
	return facility*8 + severity
}

func syslogHostname(ev event.Event) string {
	if h, ok := ev.Attributes["hostname"].(string); ok && h != "" {
		return h
	}
	return ev.SourceID
}

func syslogTag(ev event.Event) string {
	if t, ok := ev.Attributes["syslog_tag"].(string); ok && t != "" {
		return t
	}
	return ev.SourceID
}

func syslogMessage(ev event.Event) string {
	if m, ok := ev.Attributes["message"].(string); ok && m != "" {
		return m
	}
	b, _ := json.Marshal(ev.Attributes)
	return string(b)
}

// RFC3164 encodes events as RFC3164 syslog messages.
type RFC3164 struct{}

func init() {
	Register("syslog-rfc3164", RFC3164{})
}

// Name returns the encoder name.
func (RFC3164) Name() string { return "syslog-rfc3164" }

// ContentType returns the MIME type of the encoded output.
func (RFC3164) ContentType() string { return "text/plain" }

// Encode formats the event as an RFC3164 message.
func (RFC3164) Encode(ev event.Event) ([]byte, error) {
	priority := syslogPriority(ev)
	timestamp := ev.EventTime.Format(time.Stamp)
	hostname := syslogHostname(ev)
	tag := syslogTag(ev)
	message := syslogMessage(ev)
	return []byte(fmt.Sprintf("<%d>%s %s %s: %s", priority, timestamp, hostname, tag, message)), nil
}

// RFC5424 encodes events as RFC5424 syslog messages.
type RFC5424 struct{}

func init() {
	Register("syslog-rfc5424", RFC5424{})
}

// Name returns the encoder name.
func (RFC5424) Name() string { return "syslog-rfc5424" }

// ContentType returns the MIME type of the encoded output.
func (RFC5424) ContentType() string { return "text/plain" }

// Encode formats the event as an RFC5424 message.
func (RFC5424) Encode(ev event.Event) ([]byte, error) {
	priority := syslogPriority(ev)
	timestamp := ev.EventTime.Format("2006-01-02T15:04:05.000000Z")
	hostname := syslogHostname(ev)
	procid := "-"
	if ev.FlowID != nil {
		procid = *ev.FlowID
	}
	message := syslogMessage(ev)
	return []byte(fmt.Sprintf(
		"<%d>1 %s %s %s %s %s - %s",
		priority, timestamp, hostname, ev.SourceID, procid, ev.EventType, message,
	)), nil
}
