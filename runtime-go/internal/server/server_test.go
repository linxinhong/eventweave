package server

import (
	"bufio"
	"context"
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/loader"
)

func TestRuntimeServerRoutesByFilter(t *testing.T) {
	dir := t.TempDir()

	// Write a small event plan.
	events := []event.Event{
		{EventID: "e1", SourceID: "edr-001", EventType: "user.login"},
		{EventID: "e2", SourceID: "firewall-001", EventType: "firewall.allow"},
		{EventID: "e3", SourceID: "edr-001", EventType: "process.start"},
	}
	planFile := filepath.Join(dir, "event_plan.jsonl")
	f, err := os.Create(planFile)
	if err != nil {
		t.Fatal(err)
	}
	for _, ev := range events {
		b, _ := json.Marshal(ev)
		_, _ = f.Write(b)
		_, _ = f.WriteString("\n")
	}
	_ = f.Close()

	cfg := `
servers:
  - id: edr_http
    protocol: http
    bind: 127.0.0.1
    port: 28081
    path: /events
    source_filter:
      source_id: edr-001
`
	cfgFile := filepath.Join(dir, "server.yaml")
	if err := os.WriteFile(cfgFile, []byte(cfg), 0o644); err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	rs := NewRuntimeServer(dir, cfgFile, 0, "")
	serverDone := make(chan *ServerStats, 1)
	go func() {
		stats, err := rs.RunWithContext(ctx)
		if err != nil {
			t.Errorf("run: %v", err)
		}
		serverDone <- stats
	}()

	// Connect client as soon as the server is ready (during its startup delay).
	var resp *http.Response
	for i := 0; i < 100; i++ {
		resp, err = http.Get("http://127.0.0.1:28081/events")
		if err == nil {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if err != nil {
		t.Fatalf("connect client: %v", err)
	}

	loaded, err := loader.LoadEventPlan(planFile)
	if err != nil {
		t.Fatal(err)
	}
	for _, ev := range loaded {
		t.Logf("loaded event: id=%s source_id=%s type=%s", ev.EventID, ev.SourceID, ev.EventType)
	}

	// Consume the stream in the background so we can cancel the server.
	linesDone := make(chan int, 1)
	go func() {
		defer close(linesDone)
		scanner := bufio.NewScanner(resp.Body)
		count := 0
		for scanner.Scan() {
			count++
		}
		_ = resp.Body.Close()
		linesDone <- count
	}()

	// Wait until the client has received the expected events or times out.
	select {
	case <-linesDone:
	case <-time.After(500 * time.Millisecond):
		_ = resp.Body.Close()
	}
	cancel()

	stats := <-serverDone
	if stats == nil {
		t.Fatal("server stats is nil")
	}

	if stats.LoadedEvents != 3 {
		t.Fatalf("expected 3 loaded events, got %d", stats.LoadedEvents)
	}
	t.Logf("endpoints stats: %+v", stats.Endpoints)
	if stats.Endpoints["edr_http"].Emitted != 2 {
		t.Fatalf("expected 2 emitted for edr_http, got %d", stats.Endpoints["edr_http"].Emitted)
	}
}

func TestRuntimeServerStatsJSON(t *testing.T) {
	dir := t.TempDir()

	events := []event.Event{
		{EventID: "e1", SourceID: "edr-001", EventType: "user.login"},
	}
	planFile := filepath.Join(dir, "event_plan.jsonl")
	f, err := os.Create(planFile)
	if err != nil {
		t.Fatal(err)
	}
	for _, ev := range events {
		b, _ := json.Marshal(ev)
		_, _ = f.Write(b)
		_, _ = f.WriteString("\n")
	}
	_ = f.Close()

	cfg := `
servers:
  - id: all_events
    protocol: http
    bind: 127.0.0.1
    port: 28082
    path: /events
`
	cfgFile := filepath.Join(dir, "server.yaml")
	if err := os.WriteFile(cfgFile, []byte(cfg), 0o644); err != nil {
		t.Fatal(err)
	}

	statsFile := filepath.Join(dir, "stats.json")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	rs := NewRuntimeServer(dir, cfgFile, 0, statsFile)
	serverDone := make(chan *ServerStats, 1)
	go func() {
		stats, err := rs.RunWithContext(ctx)
		if err != nil {
			t.Errorf("run: %v", err)
		}
		serverDone <- stats
	}()

	time.Sleep(150 * time.Millisecond)
	resp, err := http.Get("http://127.0.0.1:28082/events")
	if err != nil {
		t.Fatalf("connect client: %v", err)
	}

	linesDone := make(chan int, 1)
	go func() {
		defer close(linesDone)
		scanner := bufio.NewScanner(resp.Body)
		count := 0
		for scanner.Scan() {
			count++
		}
		_ = resp.Body.Close()
		linesDone <- count
	}()

	select {
	case <-linesDone:
	case <-time.After(500 * time.Millisecond):
		_ = resp.Body.Close()
	}
	cancel()

	<-serverDone

	if _, err := os.Stat(statsFile); err != nil {
		t.Fatalf("stats json not written: %v", err)
	}
}
