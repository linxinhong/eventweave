package security

import (
	"encoding/json"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// DBAPPSecurityWAF encodes events as DBAPPSecurity WAF JSON.
type DBAPPSecurityWAF struct{}

func init() {
	encoder.Register("dbappsecurity-waf", DBAPPSecurityWAF{})
}

// Name returns the encoder name.
func (DBAPPSecurityWAF) Name() string { return "dbappsecurity-waf" }

// ContentType returns the MIME type of the encoded output.
func (DBAPPSecurityWAF) ContentType() string { return "application/json" }

// Encode formats the event as a DBAPPSecurity WAF JSON record.
func (DBAPPSecurityWAF) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, []string{"devname", "srcip", "dstip", "url", "attack_type"}); err != nil {
		return nil, err
	}
	record := map[string]any{
		"timestamp":   ev.EventTime.Format("2006-01-02T15:04:05.000000Z"),
		"device_name": ev.Attributes["devname"],
		"src_ip":      ev.Attributes["srcip"],
		"dst_ip":      ev.Attributes["dstip"],
		"url":         ev.Attributes["url"],
		"attack_type": ev.Attributes["attack_type"],
	}
	for _, key := range []string{"method", "severity", "rule_id", "matched_data"} {
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

// NSFOCUSIPS encodes events as NSFOCUS IPS JSON.
type NSFOCUSIPS struct{}

func init() {
	encoder.Register("nsfocus-ips", NSFOCUSIPS{})
}

// Name returns the encoder name.
func (NSFOCUSIPS) Name() string { return "nsfocus-ips" }

// ContentType returns the MIME type of the encoded output.
func (NSFOCUSIPS) ContentType() string { return "application/json" }

// Encode formats the event as an NSFOCUS IPS JSON record.
func (NSFOCUSIPS) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, []string{"devname", "srcip", "dstip", "attack_name"}); err != nil {
		return nil, err
	}
	record := map[string]any{
		"timestamp":    ev.EventTime.Format("2006-01-02T15:04:05.000000Z"),
		"device_name":  ev.Attributes["devname"],
		"src_ip":       ev.Attributes["srcip"],
		"dst_ip":       ev.Attributes["dstip"],
		"attack_name":  ev.Attributes["attack_name"],
	}
	for _, key := range []string{"severity", "rule_id", "category", "action"} {
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
