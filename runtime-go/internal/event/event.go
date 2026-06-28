package event

import (
	"encoding/json"
	"fmt"
	"time"
)

// Event mirrors the canonical EventWeave event structure.
type Event struct {
	EventID      string            `json:"event_id"`
	ScenarioID   string            `json:"scenario_id"`
	FlowID       *string           `json:"flow_id,omitempty"`
	SourceID     string            `json:"source_id"`
	EventType    string            `json:"event_type"`
	EventTime    time.Time         `json:"event_time"`
	GeneratedAt  time.Time         `json:"generated_at"`
	EmitTime     *time.Time        `json:"emit_time,omitempty"`
	IngestTime   *time.Time        `json:"ingest_time,omitempty"`
	EntityRefs   map[string]string `json:"entity_refs"`
	Attributes   map[string]any    `json:"attributes"`
	SemanticRefs []string          `json:"semantic_refs"`
	Labels       []string          `json:"labels"`
	GroundTruth  map[string]any    `json:"ground_truth"`
}

// timeFormats lists timestamp layouts accepted when loading an event plan.
var timeFormats = []string{
	time.RFC3339Nano,
	time.RFC3339,
	"2006-01-02 15:04:05.999999999-07:00",
	"2006-01-02 15:04:05.999999999Z07:00",
	"2006-01-02 15:04:05-07:00",
}

// parseTime tries multiple layouts to accommodate Python and Go outputs.
func parseTime(value string) (time.Time, error) {
	for _, layout := range timeFormats {
		if t, err := time.Parse(layout, value); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("cannot parse time %q", value)
}

// flexibleTime is a time.Time that unmarshals from several string layouts.
type flexibleTime time.Time

func (ft *flexibleTime) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err != nil {
		return err
	}
	t, err := parseTime(s)
	if err != nil {
		return err
	}
	*ft = flexibleTime(t)
	return nil
}

func (ft flexibleTime) Time() time.Time {
	return time.Time(ft)
}

// UnmarshalJSON loads an event while tolerating multiple timestamp formats.
func (e *Event) UnmarshalJSON(data []byte) error {
	type rawEvent Event
	raw := &struct {
		EventTime   flexibleTime  `json:"event_time"`
		GeneratedAt flexibleTime  `json:"generated_at"`
		EmitTime    *flexibleTime `json:"emit_time,omitempty"`
		IngestTime  *flexibleTime `json:"ingest_time,omitempty"`
		*rawEvent
	}{
		rawEvent: (*rawEvent)(e),
	}

	if err := json.Unmarshal(data, raw); err != nil {
		return err
	}

	e.EventTime = raw.EventTime.Time()
	e.GeneratedAt = raw.GeneratedAt.Time()
	if raw.EmitTime != nil {
		t := raw.EmitTime.Time()
		e.EmitTime = &t
	}
	if raw.IngestTime != nil {
		t := raw.IngestTime.Time()
		e.IngestTime = &t
	}
	return nil
}

// MarshalJSON serializes an Event to JSON.
func (e Event) MarshalJSON() ([]byte, error) {
	type alias Event
	return json.Marshal(alias(e))
}

// SortKey returns a tuple used for stable event ordering.
func (e Event) SortKey() (time.Time, string) {
	return e.EventTime, e.EventID
}
