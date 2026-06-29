package security

import (
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func makeEvent(attrs map[string]any) event.Event {
	return event.Event{
		EventID:    "evt-001",
		ScenarioID: "test",
		SourceID:   "sensor",
		EventType:  "alert",
		EventTime:  time.Date(2026, 6, 29, 12, 0, 0, 0, time.UTC),
		Attributes: attrs,
	}
}

func mustGet(t *testing.T, name string) encoder.Encoder {
	t.Helper()
	enc, err := encoder.Get(name)
	if err != nil {
		t.Fatalf("encoder %q not registered: %v", name, err)
	}
	return enc
}

func TestFortinetFortiGate(t *testing.T) {
	enc := mustGet(t, "fortinet-fortigate")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname": "fw-01",
		"type":    "traffic",
		"subtype": "forward",
		"srcip":   "10.0.0.5",
		"dstip":   "8.8.8.8",
		"action":  "accept",
		"service": "HTTPS",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	line := string(out)
	if !strings.Contains(line, `devname="fw-01"`) || !strings.Contains(line, `action="accept"`) {
		t.Fatalf("unexpected output: %s", line)
	}

	_, err = enc.Encode(makeEvent(map[string]any{"devname": "fw-01"}))
	if err == nil {
		t.Fatal("expected missing fields error")
	}
}

func TestPaloAltoTraffic(t *testing.T) {
	enc := mustGet(t, "paloalto-traffic")
	out, err := enc.Encode(makeEvent(map[string]any{
		"receive_time": "2026/06/29 12:00:30",
		"serial":       "001234567890",
		"src":          "10.0.0.5",
		"dst":          "8.8.8.8",
		"sport":        54321,
		"dport":        443,
		"proto":        "tcp",
		"action":       "allow",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	parts := strings.Split(string(out), ",")
	if len(parts) != 8 || parts[0] != "2026/06/29 12:00:30" {
		t.Fatalf("unexpected output: %s", out)
	}

	_, err = enc.Encode(makeEvent(map[string]any{"serial": "x"}))
	if err == nil {
		t.Fatal("expected missing fields error")
	}
}

func TestZeekConn(t *testing.T) {
	enc := mustGet(t, "zeek-conn")
	out, err := enc.Encode(makeEvent(map[string]any{
		"uid":          "C1234567890abcdef",
		"id.orig_h":    "10.0.0.5",
		"id.orig_p":    54321,
		"id.resp_h":    "8.8.8.8",
		"id.resp_p":    443,
		"proto":        "tcp",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	parts := strings.Split(string(out), "\t")
	if len(parts) != 7 || parts[1] != "C1234567890abcdef" {
		t.Fatalf("unexpected output: %s", out)
	}

	_, err = enc.Encode(makeEvent(map[string]any{"uid": "x"}))
	if err == nil {
		t.Fatal("expected missing fields error")
	}
}

func TestZeekDNS(t *testing.T) {
	enc := mustGet(t, "zeek-dns")
	out, err := enc.Encode(makeEvent(map[string]any{
		"uid":          "C1234567890abcdef",
		"id.orig_h":    "10.0.0.5",
		"id.orig_p":    12345,
		"id.resp_h":    "8.8.8.8",
		"id.resp_p":    53,
		"query":        "example.com",
		"qtype_name":   "A",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	if !strings.Contains(string(out), "example.com") {
		t.Fatalf("unexpected output: %s", out)
	}
}

func TestDNSJSON(t *testing.T) {
	enc := mustGet(t, "dns-json")
	out, err := enc.Encode(makeEvent(map[string]any{
		"client_ip": "10.0.0.5",
		"query":     "example.com",
		"qtype":     "A",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	var parsed map[string]any
	if err := json.Unmarshal(out, &parsed); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if parsed["client_ip"] != "10.0.0.5" || parsed["query"] != "example.com" {
		t.Fatalf("unexpected json: %v", parsed)
	}

	_, err = enc.Encode(makeEvent(map[string]any{}))
	if err == nil {
		t.Fatal("expected missing fields error")
	}
}

func TestSangforAF(t *testing.T) {
	enc := mustGet(t, "sangfor-af")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname": "af-01",
		"srcip":   "10.0.0.5",
		"dstip":   "8.8.8.8",
		"action":  "allow",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	if !strings.Contains(string(out), `sangfor_devname="af-01"`) {
		t.Fatalf("unexpected output: %s", out)
	}
}

func TestHuaweiUSG(t *testing.T) {
	enc := mustGet(t, "huawei-usg")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname": "usg-01",
		"srcip":   "10.0.0.5",
		"dstip":   "8.8.8.8",
		"action":  "allow",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	if !strings.Contains(string(out), `huawei_devname="usg-01"`) {
		t.Fatalf("unexpected output: %s", out)
	}
}

func TestH3CSecPath(t *testing.T) {
	enc := mustGet(t, "h3c-secpath")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname": "secpath-01",
		"srcip":   "10.0.0.5",
		"dstip":   "8.8.8.8",
		"action":  "allow",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	if !strings.Contains(string(out), `h3c_devName="secpath-01"`) {
		t.Fatalf("unexpected output: %s", out)
	}
}

func TestTopsecNGFW(t *testing.T) {
	enc := mustGet(t, "topsec-ngfw")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname": "topsec-01",
		"srcip":   "10.0.0.5",
		"dstip":   "8.8.8.8",
		"action":  "allow",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	if !strings.Contains(string(out), `topsec_devname="topsec-01"`) {
		t.Fatalf("unexpected output: %s", out)
	}
}

func TestQianxinNGFW(t *testing.T) {
	enc := mustGet(t, "qianxin-ngfw")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname": "qx-01",
		"srcip":   "10.0.0.5",
		"dstip":   "8.8.8.8",
		"action":  "allow",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	if !strings.Contains(string(out), `qianxin_dev_name="qx-01"`) {
		t.Fatalf("unexpected output: %s", out)
	}
}

func TestHillstoneNGFW(t *testing.T) {
	enc := mustGet(t, "hillstone-ngfw")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname": "hill-01",
		"srcip":   "10.0.0.5",
		"dstip":   "8.8.8.8",
		"action":  "allow",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	if !strings.Contains(string(out), `hillstone_devname="hill-01"`) {
		t.Fatalf("unexpected output: %s", out)
	}
}

func TestDBAPPSecurityWAF(t *testing.T) {
	enc := mustGet(t, "dbappsecurity-waf")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname":     "waf-01",
		"srcip":       "10.0.0.5",
		"dstip":       "8.8.8.8",
		"url":         "/login",
		"attack_type": "SQL Injection",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	var parsed map[string]any
	if err := json.Unmarshal(out, &parsed); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if parsed["attack_type"] != "SQL Injection" {
		t.Fatalf("unexpected json: %v", parsed)
	}

	_, err = enc.Encode(makeEvent(map[string]any{"devname": "waf-01"}))
	if err == nil {
		t.Fatal("expected missing fields error")
	}
}

func TestNSFOCUSIPS(t *testing.T) {
	enc := mustGet(t, "nsfocus-ips")
	out, err := enc.Encode(makeEvent(map[string]any{
		"devname":     "ips-01",
		"srcip":       "10.0.0.5",
		"dstip":       "8.8.8.8",
		"attack_name": "SQL Injection",
		"severity":    "high",
	}))
	if err != nil {
		t.Fatalf("encode failed: %v", err)
	}
	var parsed map[string]any
	if err := json.Unmarshal(out, &parsed); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if parsed["attack_name"] != "SQL Injection" {
		t.Fatalf("unexpected json: %v", parsed)
	}
}
