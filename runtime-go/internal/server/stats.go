package server

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
)

// EndpointStats holds counters for a single endpoint.
type EndpointStats struct {
	Emitted int
	Failed  int
}

// ServerStats aggregates counters across all endpoints.
type ServerStats struct {
	LoadedEvents      int
	UnresolvedRefs    int
	Endpoints         map[string]EndpointStats
	EndpointProtocols map[string]string `json:"-"`
	mu                sync.RWMutex
}

// NewStats creates empty server stats.
func NewStats() *ServerStats {
	return &ServerStats{
		Endpoints:         make(map[string]EndpointStats),
		EndpointProtocols: make(map[string]string),
	}
}

// IncrEmitted increments the emitted counter for an endpoint.
func (s *ServerStats) IncrEmitted(endpointID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	stats := s.Endpoints[endpointID]
	stats.Emitted++
	s.Endpoints[endpointID] = stats
}

// IncrFailed increments the failed counter for an endpoint.
func (s *ServerStats) IncrFailed(endpointID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	stats := s.Endpoints[endpointID]
	stats.Failed++
	s.Endpoints[endpointID] = stats
}

// Snapshot returns a copy of the endpoint stats.
func (s *ServerStats) Snapshot() map[string]EndpointStats {
	s.mu.RLock()
	defer s.mu.RUnlock()
	copy := make(map[string]EndpointStats, len(s.Endpoints))
	for k, v := range s.Endpoints {
		copy[k] = v
	}
	return copy
}

// Print outputs server stats in a human-readable format.
func (s *ServerStats) Print() {
	fmt.Println("Server finished")
	fmt.Printf("Events loaded: %d\n", s.LoadedEvents)
	snapshot := s.Snapshot()
	fmt.Printf("Endpoints active: %d\n", len(snapshot))
	for id, stats := range snapshot {
		fmt.Printf("  %s: emitted=%d failed=%d\n", id, stats.Emitted, stats.Failed)
	}
}

// WriteJSON writes server stats to a JSON file.
func (s *ServerStats) WriteJSON(path string) error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0o644)
}
