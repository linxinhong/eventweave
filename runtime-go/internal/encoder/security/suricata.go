package security

import (
	"encoding/json"
	"fmt"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// SuricataEVE encodes events as Suricata EVE JSON.
type SuricataEVE struct{}

func init() {
	encoder.Register("suricata-eve", SuricataEVE{})
}

// Name returns the encoder name.
func (SuricataEVE) Name() string { return "suricata-eve" }

// ContentType returns the MIME type of the encoded output.
func (SuricataEVE) ContentType() string { return "application/x-ndjson" }

// Encode formats the event as Suricata EVE JSON.
func (SuricataEVE) Encode(ev event.Event) ([]byte, error) {
	required := []string{"event_type", "src_ip", "dest_ip"}
	missing := make([]string, 0, len(required))
	for _, key := range required {
		if _, ok := ev.Attributes[key]; !ok {
			missing = append(missing, key)
		}
	}
	if len(missing) > 0 {
		return nil, encoder.NewEncodeError(fmt.Sprintf("missing required fields: %v", missing))
	}

	record := map[string]any{
		"timestamp":  ev.EventTime.Format("2006-01-02T15:04:05.000000-0700"),
		"event_type": ev.Attributes["event_type"],
		"src_ip":     ev.Attributes["src_ip"],
		"dest_ip":    ev.Attributes["dest_ip"],
	}
	optional := []string{
		"src_port", "dest_port", "proto", "alert", "http", "dns",
		"flow_id", "in_iface", "vlan",
	}
	for _, key := range optional {
		if value, ok := ev.Attributes[key]; ok {
			record[key] = value
		}
	}
	for key, value := range ev.Attributes {
		if _, exists := record[key]; !exists {
			record[key] = value
		}
	}
	return json.Marshal(record)
}
