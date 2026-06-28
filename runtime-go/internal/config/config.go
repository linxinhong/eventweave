package config

import (
	"errors"
	"strings"
	"time"
)

// RuntimeConfig holds CLI options for the local runtime.
type RuntimeConfig struct {
	PlanDir string
	Sink    string
	Output  string
	URL     string
	Speed   float64
	NoWait  bool
	Limit   int
	Timeout     time.Duration
	Retries     int
	Brokers     string
	Topic       string
	KeyField    string
	Facility    int
	Severity    int
	Tag         string
	SyslogProto string
	SyslogAddr  string
}

// Validate checks that the config is usable.
func (c *RuntimeConfig) Validate() error {
	if c.PlanDir == "" {
		return errors.New("plan directory is required")
	}
	switch c.Sink {
	case "stdout", "file", "null", "http", "kafka", "syslog":
	default:
		return errors.New("sink must be one of: stdout, file, null, http, kafka, syslog")
	}
	if c.Sink == "http" && c.URL == "" {
		return errors.New("--url is required for http sink")
	}
	if c.Sink == "file" && c.Output == "" {
		return errors.New("--output is required for file sink")
	}
	if c.Sink == "kafka" && c.Brokers == "" {
		return errors.New("--brokers is required for kafka sink")
	}
	if c.Sink == "kafka" && c.Topic == "" {
		return errors.New("--topic is required for kafka sink")
	}
	if c.Sink == "syslog" && c.SyslogAddr == "" {
		return errors.New("--syslog-addr is required for syslog sink")
	}
	if c.Sink == "syslog" {
		p := strings.ToLower(c.SyslogProto)
		if p != "udp" && p != "tcp" {
			return errors.New("--syslog-proto must be udp or tcp")
		}
	}
	if !c.NoWait && c.Speed <= 0 {
		return errors.New("--speed must be positive unless --no-wait is set")
	}
	return nil
}
