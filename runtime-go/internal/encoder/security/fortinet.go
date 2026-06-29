package security

import (
	"fmt"
	"sort"
	"strings"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// FortinetFortiGate encodes events in Fortinet FortiGate log format.
type FortinetFortiGate struct{}

func init() {
	encoder.Register("fortinet-fortigate", FortinetFortiGate{})
}

// Name returns the encoder name.
func (FortinetFortiGate) Name() string { return "fortinet-fortigate" }

// ContentType returns the MIME type of the encoded output.
func (FortinetFortiGate) ContentType() string { return "text/plain" }

// Encode formats the event as a FortiGate key=value log line.
func (FortinetFortiGate) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, []string{"devname", "type", "subtype", "srcip", "dstip", "action"}); err != nil {
		return nil, err
	}

	required := []string{"devname", "type", "subtype", "srcip", "dstip", "action"}
	ordered := make([]string, 0, len(ev.Attributes))
	seen := map[string]bool{}
	for _, key := range required {
		value, _ := ev.Attributes[key]
		ordered = append(ordered, fmt.Sprintf("%s=\"%s\"", key, asString(value)))
		seen[key] = true
	}

	optional := []string{"srcport", "dstport", "service", "policyid", "level", "msg"}
	for _, key := range optional {
		if value, ok := ev.Attributes[key]; ok {
			ordered = append(ordered, fmt.Sprintf("%s=\"%s\"", key, asString(value)))
			seen[key] = true
		}
	}

	extra := make([]string, 0, len(ev.Attributes))
	for key := range ev.Attributes {
		if !seen[key] {
			extra = append(extra, fmt.Sprintf("%s=\"%s\"", key, asString(ev.Attributes[key])))
		}
	}
	sort.Strings(extra)
	ordered = append(ordered, extra...)

	return []byte(strings.Join(ordered, " ")), nil
}
