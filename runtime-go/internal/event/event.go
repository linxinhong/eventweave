package event

import (
	"encoding/json"
	"time"
)

// Event mirrors the canonical EventWeave event structure.
type Event struct {
	EventID     string            `json:"event_id"`
	ScenarioID  string            `json:"scenario_id"`
	FlowID      *string           `json:"flow_id,omitempty"`
	SourceID    string            `json:"source_id"`
	EventType   string            `json:"event_type"`
	EventTime   time.Time         `json:"event_time"`
	GeneratedAt time.Time         `json:"generated_at"`
	EmitTime    *time.Time        `json:"emit_time,omitempty"`
	IngestTime  *time.Time        `json:"ingest_time,omitempty"`
	EntityRefs  map[string]string `json:"entity_refs"`
	Attributes  map[string]any    `json:"attributes"`
	SemanticRefs []string         `json:"semantic_refs"`
	Labels      []string          `json:"labels"`
	GroundTruth map[string]any    `json:"ground_truth"`
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
