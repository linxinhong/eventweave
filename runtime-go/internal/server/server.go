package server

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/loader"
	"github.com/linxinhong/eventweave/runtime-go/internal/metrics"
	"github.com/linxinhong/eventweave/runtime-go/internal/scheduler"
)

// RuntimeServer loads a plan, starts endpoints, and routes events.
type RuntimeServer struct {
	planDir    string
	configPath string
	limit      int
	statsJSON  string
}

// NewRuntimeServer creates a server instance.
func NewRuntimeServer(planDir, configPath string, limit int, statsJSON string) *RuntimeServer {
	return &RuntimeServer{
		planDir:    planDir,
		configPath: configPath,
		limit:      limit,
		statsJSON:  statsJSON,
	}
}

// Run executes the server until interrupted by a signal.
func (rs *RuntimeServer) Run() (*ServerStats, error) {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	return rs.RunWithContext(ctx)
}

// RunWithContext executes the server until the context is canceled.
func (rs *RuntimeServer) RunWithContext(ctx context.Context) (*ServerStats, error) {
	events, err := loader.LoadEventPlan(fmt.Sprintf("%s/event_plan.jsonl", rs.planDir))
	if err != nil {
		return nil, fmt.Errorf("load event plan: %w", err)
	}

	cfg, err := LoadConfig(rs.configPath)
	if err != nil {
		return nil, fmt.Errorf("load server config: %w", err)
	}

	sorted := scheduler.SortEvents(events)
	if rs.limit > 0 && len(sorted) > rs.limit {
		sorted = sorted[:rs.limit]
	}

	stats := NewStats()
	stats.LoadedEvents = len(sorted)
	stats.UnresolvedRefs = countUnresolvedRefs(sorted)
	rs.recordEndpointProtocols(stats, cfg)

	metrics.RecordEventsLoaded("serve", stats.LoadedEvents)
	metrics.RecordUnresolvedRefs("serve", stats.UnresolvedRefs)

	endpoints, err := rs.buildEndpoints(cfg)
	if err != nil {
		return nil, err
	}

	for _, ep := range endpoints {
		if err := ep.Open(); err != nil {
			rs.closeAll(endpoints)
			return nil, fmt.Errorf("open endpoint %s: %w", ep.ID(), err)
		}
	}

	// Allow clients a moment to connect before emitting events.
	select {
	case <-ctx.Done():
		rs.closeAll(endpoints)
		return stats, nil
	case <-time.After(100 * time.Millisecond):
	}

ServerLoop:
	for _, ev := range sorted {
		select {
		case <-ctx.Done():
			break ServerLoop
		default:
		}

		for _, ep := range endpoints {
			filter := cfg.endpointFilter(ep.ID())
			if !filter.Match(ev) {
				continue
			}
			protocol := stats.EndpointProtocols[ep.ID()]
			if err := ep.Write(ev); err != nil {
				metrics.RecordEndpointFailure(ep.ID(), protocol)
				metrics.RecordEndpointEvent(ep.ID(), protocol, "failed")
			} else {
				metrics.RecordEndpointEvent(ep.ID(), protocol, "success")
			}
		}

		// Small pacing to give clients time to consume and to avoid
		// overwhelming endpoints in server mode.
		select {
		case <-ctx.Done():
			break ServerLoop
		case <-time.After(1 * time.Millisecond):
		}
	}

	// Keep endpoints open so late clients can replay buffered events.
	<-ctx.Done()

	rs.closeAll(endpoints)

	// Sync endpoint counters into stats map.
	for _, ep := range endpoints {
		s := ep.Stats()
		stats.Endpoints[ep.ID()] = s
	}

	if rs.statsJSON != "" {
		if err := stats.WriteJSON(rs.statsJSON); err != nil {
			return stats, fmt.Errorf("write stats json: %w", err)
		}
	}

	return stats, nil
}

func (rs *RuntimeServer) buildEndpoints(cfg *ServerConfig) ([]Endpoint, error) {
	endpoints := make([]Endpoint, 0, len(cfg.Servers))
	for _, srv := range cfg.Servers {
		addr := srv.Address()
		switch srv.ProtocolName() {
		case "http":
			endpoints = append(endpoints, NewHTTPServer(srv.ID, addr, srv.Path))
		case "syslog_udp":
			endpoints = append(endpoints, NewSyslogServer(srv.ID, addr, "udp", 16, 6, "eventweave"))
		case "syslog_tcp":
			endpoints = append(endpoints, NewSyslogServer(srv.ID, addr, "tcp", 16, 6, "eventweave"))
		default:
			return nil, fmt.Errorf("unknown protocol for endpoint %s: %s", srv.ID, srv.Protocol)
		}
	}
	return endpoints, nil
}

func (rs *RuntimeServer) recordEndpointProtocols(stats *ServerStats, cfg *ServerConfig) {
	for _, srv := range cfg.Servers {
		stats.EndpointProtocols[srv.ID] = srv.ProtocolName()
	}
}

func (rs *RuntimeServer) closeAll(endpoints []Endpoint) {
	for _, ep := range endpoints {
		_ = ep.Close()
	}
}

// endpointFilter returns the source filter for a configured endpoint.
func (c *ServerConfig) endpointFilter(id string) SourceFilter {
	for _, srv := range c.Servers {
		if srv.ID == id {
			return srv.SourceFilter
		}
	}
	return SourceFilter{}
}

func countUnresolvedRefs(events []event.Event) int {
	count := 0
	for _, ev := range events {
		for _, ref := range ev.SemanticRefs {
			if strings.HasPrefix(ref, "semantic://") {
				count++
				break
			}
		}
	}
	return count
}
