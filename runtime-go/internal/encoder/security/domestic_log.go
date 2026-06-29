package security

import (
	"fmt"
	"sort"
	"strings"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// vendorLogEncoder encodes key=value logs with a vendor-specific field prefix.
type vendorLogEncoder struct {
	name       string
	content    string
	prefix     string
	deviceKey  string
	required   []string
	optional   []string
	fixedOrder []string
}

func (e vendorLogEncoder) Name() string { return e.name }

func (e vendorLogEncoder) ContentType() string { return e.content }

func (e vendorLogEncoder) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, e.required); err != nil {
		return nil, err
	}

	seen := map[string]bool{}
	ordered := make([]string, 0, len(e.required)+len(e.optional)+len(ev.Attributes))

	for _, key := range e.fixedOrder {
		fieldName := e.prefix + "_" + key
		lookupKey := key
		if key == "devname" {
			fieldName = e.prefix + "_" + e.deviceKey
		}
		value, _ := ev.Attributes[lookupKey]
		ordered = append(ordered, fmt.Sprintf("%s=\"%s\"", fieldName, asString(value)))
		seen[lookupKey] = true
	}

	for _, key := range e.optional {
		if _, ok := ev.Attributes[key]; !ok {
			continue
		}
		fieldName := e.prefix + "_" + key
		ordered = append(ordered, fmt.Sprintf("%s=\"%s\"", fieldName, asString(ev.Attributes[key])))
		seen[key] = true
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

// SangforAF encodes events as Sangfor AF log entries.
type SangforAF struct{}

func init() {
	encoder.Register("sangfor-af", SangforAF{})
}

func (SangforAF) Name() string       { return "sangfor-af" }
func (SangforAF) ContentType() string { return "text/plain" }
func (SangforAF) Encode(ev event.Event) ([]byte, error) {
	return vendorLogEncoder{
		name:       "sangfor-af",
		content:    "text/plain",
		prefix:     "sangfor",
		deviceKey:  "devname",
		required:   []string{"devname", "srcip", "dstip", "action"},
		optional:   []string{"srcport", "dstport", "service", "level", "msg"},
		fixedOrder: []string{"devname", "srcip", "dstip", "action"},
	}.Encode(ev)
}

// HuaweiUSG encodes events as Huawei USG log entries.
type HuaweiUSG struct{}

func init() {
	encoder.Register("huawei-usg", HuaweiUSG{})
}

func (HuaweiUSG) Name() string       { return "huawei-usg" }
func (HuaweiUSG) ContentType() string { return "text/plain" }
func (HuaweiUSG) Encode(ev event.Event) ([]byte, error) {
	return vendorLogEncoder{
		name:       "huawei-usg",
		content:    "text/plain",
		prefix:     "huawei",
		deviceKey:  "devname",
		required:   []string{"devname", "srcip", "dstip", "action"},
		optional:   []string{"srcport", "dstport", "service", "level", "msg"},
		fixedOrder: []string{"devname", "srcip", "dstip", "action"},
	}.Encode(ev)
}

// H3CSecPath encodes events as H3C SecPath log entries.
type H3CSecPath struct{}

func init() {
	encoder.Register("h3c-secpath", H3CSecPath{})
}

func (H3CSecPath) Name() string       { return "h3c-secpath" }
func (H3CSecPath) ContentType() string { return "text/plain" }
func (H3CSecPath) Encode(ev event.Event) ([]byte, error) {
	return vendorLogEncoder{
		name:       "h3c-secpath",
		content:    "text/plain",
		prefix:     "h3c",
		deviceKey:  "devName",
		required:   []string{"devname", "srcip", "dstip", "action"},
		optional:   []string{"srcport", "dstport", "service", "level", "msg"},
		fixedOrder: []string{"devname", "srcip", "dstip", "action"},
	}.Encode(ev)
}

// TopsecNGFW encodes events as Topsec NGFW log entries.
type TopsecNGFW struct{}

func init() {
	encoder.Register("topsec-ngfw", TopsecNGFW{})
}

func (TopsecNGFW) Name() string       { return "topsec-ngfw" }
func (TopsecNGFW) ContentType() string { return "text/plain" }
func (TopsecNGFW) Encode(ev event.Event) ([]byte, error) {
	return vendorLogEncoder{
		name:       "topsec-ngfw",
		content:    "text/plain",
		prefix:     "topsec",
		deviceKey:  "devname",
		required:   []string{"devname", "srcip", "dstip", "action"},
		optional:   []string{"srcport", "dstport", "service", "level", "msg"},
		fixedOrder: []string{"devname", "srcip", "dstip", "action"},
	}.Encode(ev)
}

// QianxinNGFW encodes events as Qianxin NGFW log entries.
type QianxinNGFW struct{}

func init() {
	encoder.Register("qianxin-ngfw", QianxinNGFW{})
}

func (QianxinNGFW) Name() string       { return "qianxin-ngfw" }
func (QianxinNGFW) ContentType() string { return "text/plain" }
func (QianxinNGFW) Encode(ev event.Event) ([]byte, error) {
	return vendorLogEncoder{
		name:       "qianxin-ngfw",
		content:    "text/plain",
		prefix:     "qianxin",
		deviceKey:  "dev_name",
		required:   []string{"devname", "srcip", "dstip", "action"},
		optional:   []string{"srcport", "dstport", "service", "level", "msg"},
		fixedOrder: []string{"devname", "srcip", "dstip", "action"},
	}.Encode(ev)
}

// HillstoneNGFW encodes events as Hillstone NGFW log entries.
type HillstoneNGFW struct{}

func init() {
	encoder.Register("hillstone-ngfw", HillstoneNGFW{})
}

func (HillstoneNGFW) Name() string       { return "hillstone-ngfw" }
func (HillstoneNGFW) ContentType() string { return "text/plain" }
func (HillstoneNGFW) Encode(ev event.Event) ([]byte, error) {
	return vendorLogEncoder{
		name:       "hillstone-ngfw",
		content:    "text/plain",
		prefix:     "hillstone",
		deviceKey:  "devname",
		required:   []string{"devname", "srcip", "dstip", "action"},
		optional:   []string{"srcport", "dstport", "service", "level", "msg"},
		fixedOrder: []string{"devname", "srcip", "dstip", "action"},
	}.Encode(ev)
}
