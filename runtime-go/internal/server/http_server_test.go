package server

import (
	"bufio"
	"context"
	"fmt"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestHTTPServerUsesEncoder(t *testing.T) {
	addr := "127.0.0.1:18086"
	enc, err := encoder.Get("nginx-access")
	if err != nil {
		t.Fatalf("get encoder: %v", err)
	}
	srv := NewHTTPServer("http_enc_test", addr, "/events", enc)
	if err := srv.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	defer srv.Close()

	time.Sleep(50 * time.Millisecond)

	clientCtx, cancel := context.WithCancel(context.Background())
	defer cancel()

	lines := make(chan string, 10)
	go func() {
		req, _ := http.NewRequestWithContext(clientCtx, http.MethodGet, fmt.Sprintf("http://%s/events", addr), nil)
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			return
		}
		defer resp.Body.Close()
		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			lines <- scanner.Text()
		}
	}()

	time.Sleep(100 * time.Millisecond)

	_ = srv.Write(event.Event{
		EventID:   "1",
		SourceID:  "nginx",
		EventType: "http.request",
		Attributes: map[string]any{
			"remote_addr":     "192.168.1.1",
			"request":         "GET / HTTP/1.1",
			"status":          200,
			"body_bytes_sent": 42,
		},
	})

	select {
	case line := <-lines:
		if !strings.HasPrefix(line, "data: ") {
			t.Fatalf("expected SSE data frame, got %q", line)
		}
		payload := strings.TrimPrefix(line, "data: ")
		if !strings.Contains(payload, "192.168.1.1") {
			t.Fatalf("expected encoded nginx log to contain remote_addr, got %q", payload)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout waiting for event")
	}

	stats := srv.Stats()
	if stats.Emitted != 1 {
		t.Fatalf("expected 1 emitted, got %d", stats.Emitted)
	}
}

func TestHTTPServerServesFilteredEvents(t *testing.T) {
	addr := "127.0.0.1:18081"
	srv := NewHTTPServer("http_test", addr, "/events", nil)
	if err := srv.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	defer srv.Close()

	// Wait for listener to be ready.
	time.Sleep(50 * time.Millisecond)

	// Start client before writing events.
	clientCtx, cancel := context.WithCancel(context.Background())
	defer cancel()

	lines := make(chan string, 10)
	go func() {
		req, _ := http.NewRequestWithContext(clientCtx, http.MethodGet, fmt.Sprintf("http://%s/events", addr), nil)
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			return
		}
		defer resp.Body.Close()
		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			lines <- scanner.Text()
		}
	}()

	time.Sleep(100 * time.Millisecond)

	_ = srv.Write(event.Event{EventID: "1", SourceID: "edr-001", EventType: "user.login"})
	_ = srv.Write(event.Event{EventID: "2", SourceID: "firewall-001", EventType: "firewall.allow"})

	select {
	case line := <-lines:
		if !strings.HasPrefix(line, "data: ") {
			t.Fatalf("expected SSE data frame, got %q", line)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout waiting for event")
	}

	stats := srv.Stats()
	if stats.Emitted < 1 {
		t.Fatalf("expected at least 1 emitted, got %d", stats.Emitted)
	}
}
