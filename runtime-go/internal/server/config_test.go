package server

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "server.yaml")
	data := `
servers:
  - id: http_1
    protocol: http
    bind: 127.0.0.1
    port: 18081
    path: /events
    source_filter:
      source_id: edr-001
`
	if err := os.WriteFile(path, []byte(data), 0o644); err != nil {
		t.Fatal(err)
	}

	cfg, err := LoadConfig(path)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	if len(cfg.Servers) != 1 {
		t.Fatalf("expected 1 server, got %d", len(cfg.Servers))
	}
	if cfg.Servers[0].ID != "http_1" {
		t.Fatalf("expected id http_1, got %s", cfg.Servers[0].ID)
	}
	if cfg.Servers[0].Bind != "127.0.0.1" {
		t.Fatalf("expected bind 127.0.0.1, got %s", cfg.Servers[0].Bind)
	}
	if cfg.Servers[0].SourceFilter.SourceID != "edr-001" {
		t.Fatalf("expected source_id edr-001, got %s", cfg.Servers[0].SourceFilter.SourceID)
	}
}

func TestConfigRejectsDuplicatePorts(t *testing.T) {
	cfg := &ServerConfig{
		Servers: []EndpointConfig{
			{ID: "a", Protocol: "http", Bind: "127.0.0.1", Port: 18081},
			{ID: "b", Protocol: "syslog_tcp", Bind: "127.0.0.1", Port: 18081},
		},
	}
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected duplicate port error")
	}
}

func TestConfigRejectsDuplicateIDs(t *testing.T) {
	cfg := &ServerConfig{
		Servers: []EndpointConfig{
			{ID: "a", Protocol: "http", Bind: "127.0.0.1", Port: 18081},
			{ID: "a", Protocol: "http", Bind: "127.0.0.1", Port: 18082},
		},
	}
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected duplicate id error")
	}
}

func TestConfigRejectsPrivilegedPort(t *testing.T) {
	cfg := &ServerConfig{
		Servers: []EndpointConfig{
			{ID: "a", Protocol: "http", Bind: "127.0.0.1", Port: 80},
		},
	}
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected privileged port error")
	}
}

func TestConfigRejectsWildcardBind(t *testing.T) {
	cfg := &ServerConfig{
		Servers: []EndpointConfig{
			{ID: "a", Protocol: "http", Bind: "0.0.0.0", Port: 18081},
		},
	}
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected wildcard bind warning/error")
	}
}

func TestConfigAcceptsKnownEncoder(t *testing.T) {
	cfg := &ServerConfig{
		Servers: []EndpointConfig{
			{ID: "a", Protocol: "http", Bind: "127.0.0.1", Port: 18081, Encoder: "nginx-access"},
		},
	}
	if err := cfg.Validate(); err != nil {
		t.Fatalf("expected valid config, got %v", err)
	}
}

func TestConfigRejectsUnknownEncoder(t *testing.T) {
	cfg := &ServerConfig{
		Servers: []EndpointConfig{
			{ID: "a", Protocol: "http", Bind: "127.0.0.1", Port: 18081, Encoder: "not-real"},
		},
	}
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected unknown encoder error")
	}
}
