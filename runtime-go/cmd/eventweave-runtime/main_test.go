package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func writeTempPlan(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	ev := event.Event{
		EventID:   "e1",
		ScenarioID: "test",
		SourceID:  "test",
		EventType: "test.event",
		EventTime: time.Now(),
	}
	data, err := json.Marshal(ev)
	if err != nil {
		t.Fatalf("marshal event: %v", err)
	}
	planPath := filepath.Join(dir, "event_plan.jsonl")
	if err := os.WriteFile(planPath, append(data, '\n'), 0o644); err != nil {
		t.Fatalf("write event plan: %v", err)
	}
	return dir
}

func TestRunCmdWarnsOnAllowInternalURL(t *testing.T) {
	planDir := writeTempPlan(t)

	cmd := runCmd()
	var stderr bytes.Buffer
	cmd.SetErr(&stderr)
	cmd.SetOut(&stderr)
	cmd.SetArgs([]string{
		planDir,
		"--sink", "http",
		"--url", "http://127.0.0.1:1/events",
		"--allow-internal-url",
		"--no-wait",
		"--timeout", "100ms",
		"--retries", "0",
		"--limit", "1",
	})

	_ = cmd.Execute()

	out := stderr.String()
	if !strings.Contains(out, "--allow-internal-url disables SSRF protection") {
		t.Fatalf("expected SSRF warning in stderr, got:\n%s", out)
	}
}

func TestBenchCmdWarnsOnAllowInternalURL(t *testing.T) {
	planDir := writeTempPlan(t)

	cmd := benchCmd()
	var stderr bytes.Buffer
	cmd.SetErr(&stderr)
	cmd.SetOut(&stderr)
	cmd.SetArgs([]string{
		planDir,
		"--sink", "http",
		"--url", "http://127.0.0.1:1/events",
		"--allow-internal-url",
		"--timeout", "100ms",
		"--retries", "0",
		"--limit", "1",
	})

	_ = cmd.Execute()

	out := stderr.String()
	if !strings.Contains(out, "--allow-internal-url disables SSRF protection") {
		t.Fatalf("expected SSRF warning in stderr, got:\n%s", out)
	}
}
