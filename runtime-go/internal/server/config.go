// Package server provides a multi-source, multi-port runtime server.
package server

import (
	"fmt"
	"net"
	"os"
	"strings"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"gopkg.in/yaml.v3"
)

// ServerConfig is the top-level server configuration.
type ServerConfig struct {
	Servers []EndpointConfig `yaml:"servers"`
}

// EndpointConfig describes one listener endpoint.
type EndpointConfig struct {
	ID             string       `yaml:"id"`
	Protocol       string       `yaml:"protocol"`
	Bind           string       `yaml:"bind"`
	Port           int          `yaml:"port"`
	Path           string       `yaml:"path"`
	Encoder        string       `yaml:"encoder,omitempty"`
	Enrich         bool         `yaml:"enrich,omitempty"`
	SourceFilter   SourceFilter `yaml:"source_filter"`
	AllowedClients []string     `yaml:"allowed_clients,omitempty"`
}

// SourceFilter selects events for an endpoint.
type SourceFilter struct {
	SourceID   string `yaml:"source_id"`
	SourceType string `yaml:"source_type"`
	EventType  string `yaml:"event_type"`
}

// LoadConfig reads a server configuration from a YAML file.
func LoadConfig(path string) (*ServerConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read server config: %w", err)
	}

	var cfg ServerConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse server config: %w", err)
	}

	if err := cfg.Validate(); err != nil {
		return nil, err
	}

	return &cfg, nil
}

// Validate checks the server configuration.
func (c *ServerConfig) Validate() error {
	if len(c.Servers) == 0 {
		return fmt.Errorf("server config must define at least one server")
	}

	seen := make(map[string]struct{})
	for i, srv := range c.Servers {
		if srv.ID == "" {
			return fmt.Errorf("server at index %d is missing id", i)
		}
		if _, ok := seen[srv.ID]; ok {
			return fmt.Errorf("duplicate server id: %s", srv.ID)
		}
		seen[srv.ID] = struct{}{}

		if err := srv.Validate(); err != nil {
			return fmt.Errorf("server %s: %w", srv.ID, err)
		}
	}

	// Check for duplicate bind+port across all endpoints.
	addresses := make(map[string]string)
	for _, srv := range c.Servers {
		addr := net.JoinHostPort(srv.Bind, fmt.Sprintf("%d", srv.Port))
		if otherID, ok := addresses[addr]; ok {
			return fmt.Errorf(
				"servers %s and %s both bind to %s",
				otherID, srv.ID, addr,
			)
		}
		addresses[addr] = srv.ID
	}

	return nil
}

// Validate checks a single endpoint configuration.
func (e *EndpointConfig) Validate() error {
	proto := strings.ToLower(e.Protocol)
	switch proto {
	case "http", "syslog_udp", "syslog_tcp":
		// ok
	default:
		return fmt.Errorf("unsupported protocol: %s (use http, syslog_udp, or syslog_tcp)", e.Protocol)
	}

	if e.Bind == "" {
		e.Bind = "127.0.0.1"
	}

	if e.Bind == "0.0.0.0" {
		return fmt.Errorf("binding to 0.0.0.0 requires explicit configuration; ensure this is intentional")
	}

	if e.Port <= 0 || e.Port > 65535 {
		return fmt.Errorf("invalid port: %d", e.Port)
	}

	if e.Port < 1024 {
		return fmt.Errorf("privileged port %d requires elevated permissions; use port >= 1024", e.Port)
	}

	if proto == "http" && e.Path == "" {
		e.Path = "/events"
	}

	if e.Encoder != "" {
		if _, err := encoder.Get(e.Encoder); err != nil {
			return fmt.Errorf("unknown encoder %q: %w", e.Encoder, err)
		}
	}
	if e.Enrich && e.Encoder == "" {
		return fmt.Errorf("enrich requires encoder on endpoint %s", e.ID)
	}

	return nil
}

// Protocol returns the normalized protocol name.
func (e *EndpointConfig) ProtocolName() string {
	return strings.ToLower(e.Protocol)
}

// Address returns the bind address string.
func (e *EndpointConfig) Address() string {
	return net.JoinHostPort(e.Bind, fmt.Sprintf("%d", e.Port))
}
