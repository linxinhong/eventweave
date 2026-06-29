package server

import (
	"bufio"
	"context"
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/loader"

	// Register vendor encoders for enrichment tests.
	_ "github.com/linxinhong/eventweave/runtime-go/internal/encoder/security"
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

	rs := NewRuntimeServer(dir, cfgFile, 0, "", false)
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

func TestRuntimeServerRoutesDifferentEncoders(t *testing.T) {
	dir := t.TempDir()

	events := []event.Event{
		{
			EventID:   "e1",
			SourceID:  "nginx",
			EventType: "http.request",
			Attributes: map[string]any{
				"remote_addr":     "192.168.1.1",
				"request":         "GET / HTTP/1.1",
				"status":          200,
				"body_bytes_sent": 42,
			},
		},
		{EventID: "e2", SourceID: "edr-001", EventType: "user.login"},
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
  - id: web_http
    protocol: http
    bind: 127.0.0.1
    port: 28190
    path: /events
    encoder: nginx-access
    source_filter:
      source_id: nginx
  - id: edr_http
    protocol: http
    bind: 127.0.0.1
    port: 28191
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

	rs := NewRuntimeServer(dir, cfgFile, 0, "", false)
	serverDone := make(chan *ServerStats, 1)
	go func() {
		stats, err := rs.RunWithContext(ctx)
		if err != nil {
			t.Errorf("run: %v", err)
		}
		serverDone <- stats
	}()

	var webResp, edrResp *http.Response
	for i := 0; i < 100; i++ {
		if webResp == nil {
			webResp, _ = http.Get("http://127.0.0.1:28190/events")
		}
		if edrResp == nil {
			edrResp, _ = http.Get("http://127.0.0.1:28191/events")
		}
		if webResp != nil && edrResp != nil {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if webResp == nil || edrResp == nil {
		t.Fatal("failed to connect to both endpoints")
	}

	webScanner := bufio.NewScanner(webResp.Body)
	edrScanner := bufio.NewScanner(edrResp.Body)
	var webLine, edrLine string
	webCh := make(chan string, 1)
	edrCh := make(chan string, 1)
	go func() {
		if webScanner.Scan() {
			webCh <- webScanner.Text()
		}
	}()
	go func() {
		if edrScanner.Scan() {
			edrCh <- edrScanner.Text()
		}
	}()

	select {
	case webLine = <-webCh:
	case <-time.After(500 * time.Millisecond):
	}
	select {
	case edrLine = <-edrCh:
	case <-time.After(500 * time.Millisecond):
	}

	_ = webResp.Body.Close()
	_ = edrResp.Body.Close()
	cancel()

	stats := <-serverDone
	if stats == nil {
		t.Fatal("server stats is nil")
	}
	if stats.Endpoints["web_http"].Emitted != 1 {
		t.Fatalf("expected 1 emitted for web_http, got %d", stats.Endpoints["web_http"].Emitted)
	}
	if stats.Endpoints["edr_http"].Emitted != 1 {
		t.Fatalf("expected 1 emitted for edr_http, got %d", stats.Endpoints["edr_http"].Emitted)
	}
	if !strings.Contains(webLine, "192.168.1.1") {
		t.Fatalf("expected nginx encoded output, got %q", webLine)
	}
	if !strings.Contains(edrLine, "\"event_id\":\"e2\"") {
		t.Fatalf("expected JSON output, got %q", edrLine)
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

	rs := NewRuntimeServer(dir, cfgFile, 0, statsFile, false)
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

func TestRuntimeEndpointEncoderWithEnrich(t *testing.T) {
	dir := t.TempDir()

	events := []event.Event{
		{
			EventID:   "e1",
			SourceID:  "firewall",
			EventType: "firewall.traffic",
			Attributes: map[string]any{
				"src_ip":  "10.0.0.1",
				"dest_ip": "10.0.0.2",
			},
		},
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
  - id: fortinet_http
    protocol: http
    bind: 127.0.0.1
    port: 28200
    path: /events
    encoder: fortinet-fortigate
    enrich: true
`
	cfgFile := filepath.Join(dir, "server.yaml")
	if err := os.WriteFile(cfgFile, []byte(cfg), 0o644); err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	rs := NewRuntimeServer(dir, cfgFile, 0, "", false)
	serverDone := make(chan *ServerStats, 1)
	go func() {
		stats, err := rs.RunWithContext(ctx)
		if err != nil {
			t.Errorf("run: %v", err)
		}
		serverDone <- stats
	}()

	var resp *http.Response
	for i := 0; i < 100; i++ {
		resp, err = http.Get("http://127.0.0.1:28200/events")
		if err == nil {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if err != nil {
		t.Fatalf("connect client: %v", err)
	}

	scanner := bufio.NewScanner(resp.Body)
	var line string
	if scanner.Scan() {
		line = scanner.Text()
	}
	_ = resp.Body.Close()
	cancel()

	stats := <-serverDone
	if stats == nil {
		t.Fatal("server stats is nil")
	}
	if stats.Endpoints["fortinet_http"].Emitted != 1 {
		t.Fatalf("expected 1 emitted for fortinet_http, got %d", stats.Endpoints["fortinet_http"].Emitted)
	}
	if stats.Endpoints["fortinet_http"].Failed != 0 {
		t.Fatalf("expected 0 failed for fortinet_http, got %d", stats.Endpoints["fortinet_http"].Failed)
	}
	if !strings.Contains(line, "firewall-01") {
		t.Fatalf("expected enriched devname in output, got %q", line)
	}
	if !strings.Contains(line, "10.0.0.1") {
		t.Fatalf("expected srcip in output, got %q", line)
	}
}

func TestGlobalEnrichFlag(t *testing.T) {
	dir := t.TempDir()

	events := []event.Event{
		{
			EventID:   "e1",
			SourceID:  "firewall",
			EventType: "firewall.traffic",
			Attributes: map[string]any{
				"src_ip":  "10.0.0.1",
				"dest_ip": "10.0.0.2",
			},
		},
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
  - id: fortinet_http
    protocol: http
    bind: 127.0.0.1
    port: 28202
    path: /events
    encoder: fortinet-fortigate
`
	cfgFile := filepath.Join(dir, "server.yaml")
	if err := os.WriteFile(cfgFile, []byte(cfg), 0o644); err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	rs := NewRuntimeServer(dir, cfgFile, 0, "", true)
	serverDone := make(chan *ServerStats, 1)
	go func() {
		stats, err := rs.RunWithContext(ctx)
		if err != nil {
			t.Errorf("run: %v", err)
		}
		serverDone <- stats
	}()

	var resp *http.Response
	for i := 0; i < 100; i++ {
		resp, err = http.Get("http://127.0.0.1:28202/events")
		if err == nil {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if err != nil {
		t.Fatalf("connect client: %v", err)
	}

	scanner := bufio.NewScanner(resp.Body)
	var line string
	if scanner.Scan() {
		line = scanner.Text()
	}
	_ = resp.Body.Close()
	cancel()

	stats := <-serverDone
	if stats == nil {
		t.Fatal("server stats is nil")
	}
	if stats.Endpoints["fortinet_http"].Emitted != 1 {
		t.Fatalf("expected 1 emitted for fortinet_http, got %d", stats.Endpoints["fortinet_http"].Emitted)
	}
	if stats.Endpoints["fortinet_http"].Failed != 0 {
		t.Fatalf("expected 0 failed for fortinet_http, got %d", stats.Endpoints["fortinet_http"].Failed)
	}
	if !strings.Contains(line, "firewall-01") {
		t.Fatalf("expected enriched devname in output, got %q", line)
	}
}
