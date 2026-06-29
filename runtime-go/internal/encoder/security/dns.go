package security

import (
	"encoding/json"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// DNSJSON encodes DNS events as normalized JSON.
type DNSJSON struct{}

func init() {
	encoder.Register("dns-json", DNSJSON{})
}

// Name returns the encoder name.
func (DNSJSON) Name() string { return "dns-json" }

// ContentType returns the MIME type of the encoded output.
func (DNSJSON) ContentType() string { return "application/json" }

// Encode formats the event as a normalized DNS JSON record.
func (DNSJSON) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, []string{"client_ip", "query", "qtype"}); err != nil {
		return nil, err
	}
	record := map[string]any{
		"timestamp": ev.EventTime.Format("2006-01-02T15:04:05.000000Z"),
		"client_ip": ev.Attributes["client_ip"],
		"query":     ev.Attributes["query"],
		"qtype":     ev.Attributes["qtype"],
	}
	for key, value := range ev.Attributes {
		if _, exists := record[key]; !exists {
			record[key] = value
		}
	}
	return json.Marshal(record)
}
