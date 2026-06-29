package http

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestHTTPSinkPostsEvents(t *testing.T) {
	var received int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		var ev event.Event
		if err := json.Unmarshal(body, &ev); err != nil {
			t.Errorf("unmarshal: %v", err)
		}
		received++
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	sink, err := New(server.URL, 5*time.Second, 0, true)
	if err != nil {
		t.Fatalf("new: %v", err)
	}
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	if err := sink.Write(event.Event{EventID: "e1"}); err != nil {
		t.Fatalf("write: %v", err)
	}
	if sink.Count() != 1 || sink.Failed() != 0 || received != 1 {
		t.Fatalf("unexpected counts: count=%d failed=%d received=%d", sink.Count(), sink.Failed(), received)
	}
}

func TestHTTPSinkCountsFailures(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	sink, err := New(server.URL, 5*time.Second, 0, true)
	if err != nil {
		t.Fatalf("new: %v", err)
	}
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	if err := sink.Write(event.Event{EventID: "e1"}); err == nil {
		t.Fatal("expected error for 500 response")
	}
	if sink.Count() != 0 || sink.Failed() != 1 {
		t.Fatalf("unexpected counts: count=%d failed=%d", sink.Count(), sink.Failed())
	}
}

func TestHTTPSinkRetriesOn5xx(t *testing.T) {
	requests := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests++
		if requests == 1 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	sink, err := New(server.URL, 5*time.Second, 1, true)
	if err != nil {
		t.Fatalf("new: %v", err)
	}
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	if err := sink.Write(event.Event{EventID: "e1"}); err != nil {
		t.Fatalf("write: %v", err)
	}
	if sink.Count() != 1 || sink.Failed() != 0 || requests != 2 {
		t.Fatalf("unexpected counts: count=%d failed=%d requests=%d", sink.Count(), sink.Failed(), requests)
	}
}

func TestHTTPSinkNoRetryOn4xx(t *testing.T) {
	requests := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests++
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	sink, err := New(server.URL, 5*time.Second, 2, true)
	if err != nil {
		t.Fatalf("new: %v", err)
	}
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	if err := sink.Write(event.Event{EventID: "e1"}); err == nil {
		t.Fatal("expected error for 404 response")
	}
	if requests != 1 {
		t.Fatalf("expected 1 request, got %d", requests)
	}
}

func TestIsSafeURLRejectsInternal(t *testing.T) {
	cases := []string{
		"http://127.0.0.1/events",
		"http://10.0.0.1/events",
		"http://192.168.1.1/events",
		"http://172.16.0.1/events",
		"http://169.254.169.254/latest/meta-data/",
		"http://[::1]/events",
		"http://localhost/events",
		"http://metadata/events",
		"http://metadata.google.internal/",
		"http://my-service.local/events",
		"http://my-service.internal/events",
		"file:///etc/passwd",
		"ftp://example.com/events",
	}
	for _, raw := range cases {
		if err := IsSafeURL(raw, false); err == nil {
			t.Errorf("expected rejection for %q", raw)
		}
	}
}

func TestIsSafeURLAcceptsWhenAllowed(t *testing.T) {
	if err := IsSafeURL("http://127.0.0.1/events", true); err != nil {
		t.Fatalf("expected allowed: %v", err)
	}
}

func TestHTTPSinkNewRejectsInternal(t *testing.T) {
	if _, err := New("http://127.0.0.1/events", 5*time.Second, 0, false); err == nil {
		t.Fatal("expected error for internal URL")
	}
}
