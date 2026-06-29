package security

import (
	"encoding/json"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// WindowsEventJSON encodes events as Windows Event Log JSON.
type WindowsEventJSON struct{}

func init() {
	encoder.Register("windows-event-json", WindowsEventJSON{})
}

// Name returns the encoder name.
func (WindowsEventJSON) Name() string { return "windows-event-json" }

// ContentType returns the MIME type of the encoded output.
func (WindowsEventJSON) ContentType() string { return "application/x-ndjson" }

// Encode formats the event as a Windows Event Log JSON record.
func (WindowsEventJSON) Encode(ev event.Event) ([]byte, error) {
	if _, ok := ev.Attributes["EventID"]; !ok {
		return nil, encoder.NewEncodeError("missing required field: EventID")
	}

	providerName := ev.SourceID
	if p, ok := ev.Attributes["ProviderName"].(string); ok && p != "" {
		providerName = p
	}
	computer := ev.SourceID
	if c, ok := ev.Attributes["Computer"].(string); ok && c != "" {
		computer = c
	}
	channel := "Security"
	if c, ok := ev.Attributes["Channel"].(string); ok && c != "" {
		channel = c
	}

	system := map[string]any{
		"Provider": map[string]any{
			"Name": providerName,
			"Guid": ev.Attributes["ProviderGuid"],
		},
		"EventID":       ev.Attributes["EventID"],
		"Version":       ev.Attributes["Version"],
		"Level":         ev.Attributes["Level"],
		"Task":          ev.Attributes["Task"],
		"Opcode":        ev.Attributes["Opcode"],
		"Keywords":      ev.Attributes["Keywords"],
		"TimeCreated":   map[string]any{"SystemTime": ev.EventTime.Format("2006-01-02T15:04:05.000000Z")},
		"EventRecordID": ev.Attributes["EventRecordID"],
		"Computer":      computer,
		"Channel":       channel,
	}

	eventData := map[string]any{}
	excluded := map[string]bool{
		"EventID": true, "Version": true, "Level": true, "Task": true,
		"Opcode": true, "Keywords": true, "EventRecordID": true,
		"Computer": true, "Channel": true, "ProviderName": true, "ProviderGuid": true,
	}
	for key, value := range ev.Attributes {
		if !excluded[key] {
			eventData[key] = value
		}
	}

	record := map[string]any{"Event": map[string]any{"System": system}}
	if len(eventData) > 0 {
		record["Event"].(map[string]any)["EventData"] = eventData
	}
	return json.Marshal(record)
}
