package metrics

import (
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/stats"
)

func TestMetricsServerStarts(t *testing.T) {
	RecordEventsLoaded("run", 5)

	ms := NewServer("127.0.0.1:19090")
	if err := ms.Start(); err != nil {
		t.Fatalf("start metrics server: %v", err)
	}
	defer ms.Stop(nil)

	// Wait for server to be ready.
	time.Sleep(50 * time.Millisecond)

	resp, err := http.Get("http://127.0.0.1:19090/metrics")
	if err != nil {
		t.Fatalf("get metrics: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected status 200, got %d", resp.StatusCode)
	}
	body, _ := io.ReadAll(resp.Body)
	if !strings.Contains(string(body), "eventweave_runtime_events_loaded_total") {
		t.Fatalf("expected eventweave metrics, got %q", string(body))
	}
}

func TestHealthzReturnsOK(t *testing.T) {
	ms := NewServer("127.0.0.1:19091")
	ms.SetHealth(HealthStatus{Status: "ok", Mode: "serve", Servers: 3})
	if err := ms.Start(); err != nil {
		t.Fatalf("start metrics server: %v", err)
	}
	defer ms.Stop(nil)

	time.Sleep(50 * time.Millisecond)

	resp, err := http.Get("http://127.0.0.1:19091/healthz")
	if err != nil {
		t.Fatalf("get healthz: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected status 200, got %d", resp.StatusCode)
	}

	var health HealthStatus
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		t.Fatalf("decode healthz: %v", err)
	}
	if health.Status != "ok" || health.Mode != "serve" || health.Servers != 3 {
		t.Fatalf("unexpected health: %+v", health)
	}
}

func TestRecordRuntimeStats(t *testing.T) {
	st := stats.New()
	st.LoadedEvents = 10
	st.Emitted = 8
	st.Failed = 2
	st.UnresolvedRefs = 1
	st.Finish("null", "null")

	RecordRuntimeStats("run", "null", st)

	// We cannot easily read Prometheus counters back, but we can verify no panic.
}

func TestLabelValue(t *testing.T) {
	if LabelValue("") != "none" {
		t.Fatal("expected none for empty label")
	}
	if LabelValue("http") != "http" {
		t.Fatal("expected http")
	}
}
