package encoder

import (
	"testing"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestEnrichmentAppliesDefaults(t *testing.T) {
	profile := EnrichmentProfile{
		Defaults: map[string]any{
			"devname": "firewall-01",
			"action":  "accept",
		},
	}
	ev := event.Event{
		EventID: "evt-001",
		Attributes: map[string]any{
			"srcip": "10.0.0.1",
		},
	}

	enriched := ApplyEnrichment(ev, profile)
	assert.Equal(t, "firewall-01", enriched.Attributes["devname"])
	assert.Equal(t, "accept", enriched.Attributes["action"])
	assert.Equal(t, "10.0.0.1", enriched.Attributes["srcip"])
}

func TestEnrichmentAppliesMappings(t *testing.T) {
	profile := EnrichmentProfile{
		Mappings: map[string]string{
			"srcip": "src_ip",
			"dstip": "dest_ip",
		},
	}
	ev := event.Event{
		EventID: "evt-001",
		Attributes: map[string]any{
			"src_ip":  "10.0.0.1",
			"dest_ip": "10.0.0.2",
		},
	}

	enriched := ApplyEnrichment(ev, profile)
	assert.Equal(t, "10.0.0.1", enriched.Attributes["srcip"])
	assert.Equal(t, "10.0.0.2", enriched.Attributes["dstip"])
}

func TestEnrichmentDoesNotMutateEvent(t *testing.T) {
	profile := EnrichmentProfile{
		Defaults: map[string]any{"devname": "firewall-01"},
		Mappings: map[string]string{"srcip": "src_ip"},
	}
	ev := event.Event{
		EventID: "evt-001",
		Attributes: map[string]any{
			"src_ip": "10.0.0.1",
		},
	}
	original := map[string]any{}
	for k, v := range ev.Attributes {
		original[k] = v
	}

	enriched := ApplyEnrichment(ev, profile)
	require.NotEqual(t, ev, enriched)
	assert.Equal(t, original, ev.Attributes)
	assert.NotContains(t, ev.Attributes, "devname")
	assert.NotContains(t, ev.Attributes, "srcip")
}

func TestEnrichmentPreservesExistingTarget(t *testing.T) {
	profile := EnrichmentProfile{
		Defaults: map[string]any{"srcip": "0.0.0.0"},
		Mappings: map[string]string{"srcip": "src_ip"},
	}
	ev := event.Event{
		EventID: "evt-001",
		Attributes: map[string]any{
			"src_ip":  "10.0.0.1",
			"srcip":   "192.168.1.1",
		},
	}

	enriched := ApplyEnrichment(ev, profile)
	assert.Equal(t, "192.168.1.1", enriched.Attributes["srcip"])
}

func TestEnrichmentMappingPriorityOverDefaults(t *testing.T) {
	profile := EnrichmentProfile{
		Defaults: map[string]any{"srcip": "0.0.0.0"},
		Mappings: map[string]string{"srcip": "src_ip"},
	}
	ev := event.Event{
		EventID: "evt-001",
		Attributes: map[string]any{
			"src_ip": "10.0.0.1",
		},
	}

	enriched := ApplyEnrichment(ev, profile)
	assert.Equal(t, "10.0.0.1", enriched.Attributes["srcip"])
}

func TestEnrichedEncoder(t *testing.T) {
	enc := NginxAccess{}
	profile := EnrichmentProfile{
		Defaults: map[string]any{
			"remote_addr":     "10.0.0.1",
			"request":         "GET / HTTP/1.1",
			"status":          200,
			"body_bytes_sent": 512,
		},
	}
	enrichedEnc := NewEnrichedEncoder(enc, profile)

	ev := event.Event{
		EventID:    "evt-001",
		Attributes: map[string]any{},
	}
	out, err := enrichedEnc.Encode(ev)
	require.NoError(t, err)
	assert.Contains(t, string(out), "10.0.0.1")
	assert.Contains(t, string(out), "GET / HTTP/1.1")
}

func TestLoadEnrichmentProfiles(t *testing.T) {
	profiles, err := LoadEnrichmentProfiles("../../../packs")
	require.NoError(t, err)
	require.Contains(t, profiles, "fortinet-fortigate")

	profile := profiles["fortinet-fortigate"]
	assert.Equal(t, "firewall-01", profile.Defaults["devname"])
	assert.Equal(t, "src_ip", profile.Mappings["srcip"])
}
