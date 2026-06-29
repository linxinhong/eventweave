package encoder

import (
	"maps"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// EnrichmentProfile describes how to enrich canonical events for one encoder.
type EnrichmentProfile struct {
	Encoder     string         `yaml:"encoder"`
	Defaults    map[string]any `yaml:"defaults"`
	Mappings    map[string]string `yaml:"mappings"`
	Description string         `yaml:"description,omitempty"`
}

// ApplyEnrichment returns a new event with the profile applied.
// The original event is not modified.
// Priority:
//   1. Existing target attribute.
//   2. Mapped source attribute (when target missing and source exists).
//   3. Default value.
func ApplyEnrichment(ev event.Event, profile EnrichmentProfile) event.Event {
	if profile.Defaults == nil && profile.Mappings == nil {
		return ev
	}

	newAttrs := maps.Clone(ev.Attributes)
	if newAttrs == nil {
		newAttrs = make(map[string]any)
	}

	// Apply mappings: copy from source field to target field only when target
	// is missing and source exists.
	for target, source := range profile.Mappings {
		if _, exists := newAttrs[target]; exists {
			continue
		}
		if value, ok := newAttrs[source]; ok {
			newAttrs[target] = cloneValue(value)
		}
	}

	// Apply defaults only for still-missing target fields.
	for target, value := range profile.Defaults {
		if _, exists := newAttrs[target]; exists {
			continue
		}
		newAttrs[target] = cloneValue(value)
	}

	enriched := ev
	enriched.Attributes = newAttrs
	return enriched
}

func cloneValue(v any) any {
	// For the simple scalar values used in enrichment (strings, numbers,
	// booleans), returning the value directly is safe. Lists and maps are
	// currently not expected in defaults/mappings.
	return v
}

// EnrichedEncoder wraps an encoder and applies an enrichment profile before
// encoding.
type EnrichedEncoder struct {
	enc     Encoder
	profile EnrichmentProfile
}

// NewEnrichedEncoder creates an encoder that enriches events before encoding.
func NewEnrichedEncoder(enc Encoder, profile EnrichmentProfile) *EnrichedEncoder {
	return &EnrichedEncoder{enc: enc, profile: profile}
}

// Name returns the underlying encoder name.
func (e *EnrichedEncoder) Name() string { return e.enc.Name() }

// ContentType returns the underlying encoder content type.
func (e *EnrichedEncoder) ContentType() string { return e.enc.ContentType() }

// Encode applies enrichment and delegates to the underlying encoder.
func (e *EnrichedEncoder) Encode(ev event.Event) ([]byte, error) {
	return e.enc.Encode(ApplyEnrichment(ev, e.profile))
}
