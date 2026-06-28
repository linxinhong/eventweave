package runtime

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/linxinhong/eventweave/runtime-go/internal/config"
)

func writeEventPlan(t *testing.T, dir string) {
	t.Helper()
	content := `{"event_id":"e2","scenario_id":"sc1","source_id":"src1","event_type":"logout","event_time":"2024-01-01T00:00:01Z","entity_refs":{},"attributes":{},"semantic_refs":[],"labels":[],"ground_truth":{}}
{"event_id":"e1","scenario_id":"sc1","source_id":"src1","event_type":"login","event_time":"2024-01-01T00:00:00Z","entity_refs":{},"attributes":{},"semantic_refs":[],"labels":[],"ground_truth":{}}
{"event_id":"e3","scenario_id":"sc1","source_id":"src1","event_type":"click","event_time":"2024-01-01T00:00:00Z","entity_refs":{},"attributes":{},"semantic_refs":[],"labels":[],"ground_truth":{}}
`
	if err := os.WriteFile(filepath.Join(dir, "event_plan.jsonl"), []byte(content), 0o644); err != nil {
		t.Fatalf("write event plan: %v", err)
	}
}

func TestLocalRuntimeNoWait(t *testing.T) {
	dir := t.TempDir()
	writeEventPlan(t, dir)

	rt, err := New(config.RuntimeConfig{
		PlanDir: dir,
		Sink:    "null",
		NoWait:  true,
	})
	if err != nil {
		t.Fatalf("new runtime: %v", err)
	}
	stats, err := rt.Run()
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	if stats.Emitted != 3 {
		t.Fatalf("expected 3 emitted, got %d", stats.Emitted)
	}
	if stats.Duration().Seconds() > 1.0 {
		t.Fatalf("no-wait should be fast, took %s", stats.Duration())
	}
}

func TestLocalRuntimeLimit(t *testing.T) {
	dir := t.TempDir()
	writeEventPlan(t, dir)

	rt, err := New(config.RuntimeConfig{
		PlanDir: dir,
		Sink:    "null",
		NoWait:  true,
		Limit:   2,
	})
	if err != nil {
		t.Fatalf("new runtime: %v", err)
	}
	stats, err := rt.Run()
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	if stats.Emitted != 2 {
		t.Fatalf("expected 2 emitted, got %d", stats.Emitted)
	}
}

func TestLocalRuntimeWarnsUnresolvedRefs(t *testing.T) {
	dir := t.TempDir()
	content := `{"event_id":"e1","scenario_id":"sc1","source_id":"src1","event_type":"login","event_time":"2024-01-01T00:00:00Z","entity_refs":{},"attributes":{},"semantic_refs":["semantic://task"],"labels":[],"ground_truth":{}}
`
	if err := os.WriteFile(filepath.Join(dir, "event_plan.jsonl"), []byte(content), 0o644); err != nil {
		t.Fatalf("write event plan: %v", err)
	}

	rt, err := New(config.RuntimeConfig{
		PlanDir: dir,
		Sink:    "null",
		NoWait:  true,
	})
	if err != nil {
		t.Fatalf("new runtime: %v", err)
	}
	stats, err := rt.Run()
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	if stats.UnresolvedRefs != 1 {
		t.Fatalf("expected 1 unresolved ref, got %d", stats.UnresolvedRefs)
	}
}

func TestLocalRuntimeKafkaSink(t *testing.T) {
	dir := t.TempDir()
	writeEventPlan(t, dir)

	rt, err := New(config.RuntimeConfig{
		PlanDir: dir,
		Sink:    "kafka",
		Brokers: "localhost:9092",
		Topic:   "events",
		NoWait:  true,
	})
	if err != nil {
		t.Fatalf("new runtime: %v", err)
	}
	if rt.Target() != "localhost:9092/events" {
		t.Fatalf("unexpected target: %s", rt.Target())
	}
}

func TestLocalRuntimeSyslogSink(t *testing.T) {
	dir := t.TempDir()
	writeEventPlan(t, dir)

	rt, err := New(config.RuntimeConfig{
		PlanDir:     dir,
		Sink:        "syslog",
		SyslogAddr:  "127.0.0.1:514",
		SyslogProto: "udp",
		NoWait:      true,
	})
	if err != nil {
		t.Fatalf("new runtime: %v", err)
	}
	if rt.Target() != "udp://127.0.0.1:514" {
		t.Fatalf("unexpected target: %s", rt.Target())
	}
}
