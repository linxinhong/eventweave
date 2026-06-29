package metrics

import (
	"context"
	"encoding/json"
	"net/http"
	"sync"

	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// HealthStatus is the JSON response for /healthz.
type HealthStatus struct {
	Status  string `json:"status"`
	Mode    string `json:"mode"`
	Servers int    `json:"servers"`
}

// MetricsServer exposes /metrics and /healthz.
type MetricsServer struct {
	addr    string
	server  *http.Server
	mu      sync.RWMutex
	health  HealthStatus
	started bool
}

// NewServer creates a metrics server for the given bind address.
func NewServer(addr string) *MetricsServer {
	return &MetricsServer{
		addr: addr,
		health: HealthStatus{
			Status:  "ok",
			Mode:    "unknown",
			Servers: 0,
		},
	}
}

// Start launches the metrics server in a background goroutine.
func (m *MetricsServer) Start() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.started {
		return nil
	}

	Register(nil)

	mux := http.NewServeMux()
	mux.HandleFunc("/metrics", promhttp.Handler().ServeHTTP)
	mux.HandleFunc("/healthz", m.handleHealthz)

	m.server = &http.Server{
		Addr:    m.addr,
		Handler: mux,
	}
	m.started = true

	go func() {
		_ = m.server.ListenAndServe()
	}()

	return nil
}

// Stop shuts down the metrics server.
func (m *MetricsServer) Stop(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.started || m.server == nil {
		return nil
	}

	m.started = false
	return m.server.Shutdown(ctx)
}

// SetHealth updates the health status returned by /healthz.
func (m *MetricsServer) SetHealth(health HealthStatus) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.health = health
}

// Health returns the current health status.
func (m *MetricsServer) Health() HealthStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.health
}

func (m *MetricsServer) handleHealthz(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	m.mu.RLock()
	health := m.health
	m.mu.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(health)
}

// Addr returns the configured address.
func (m *MetricsServer) Addr() string {
	return m.addr
}
