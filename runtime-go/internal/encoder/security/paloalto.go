package security

import (
	"fmt"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// PaloAltoTraffic encodes events as Palo Alto Networks traffic log CSV.
type PaloAltoTraffic struct{}

func init() {
	encoder.Register("paloalto-traffic", PaloAltoTraffic{})
}

// Name returns the encoder name.
func (PaloAltoTraffic) Name() string { return "paloalto-traffic" }

// ContentType returns the MIME type of the encoded output.
func (PaloAltoTraffic) ContentType() string { return "text/csv" }

// Encode formats the event as a Palo Alto traffic log CSV line.
func (PaloAltoTraffic) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, []string{"receive_time", "serial", "src", "dst", "sport", "dport", "proto", "action"}); err != nil {
		return nil, err
	}
	line := fmt.Sprintf(
		"%s,%s,%s,%s,%s,%s,%s,%s",
		asString(ev.Attributes["receive_time"]),
		asString(ev.Attributes["serial"]),
		asString(ev.Attributes["src"]),
		asString(ev.Attributes["dst"]),
		asString(ev.Attributes["sport"]),
		asString(ev.Attributes["dport"]),
		asString(ev.Attributes["proto"]),
		asString(ev.Attributes["action"]),
	)
	return []byte(line), nil
}
