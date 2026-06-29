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
	Timeout      time.Duration
	Retries      int
	Brokers      string
	Topic        string
	KeyField     string
	Facility     int
	Severity     int
	Tag          string
	SyslogProto  string
	SyslogAddr   string
	Rate         float64
	MaxFailures  int
	StatsJSON    string
	BatchSize    int
	BatchTimeout time.Duration
	Workers      int
	QueueSize    int
	OnQueueFull  string
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
	if err := c.validateTiming(); err != nil {
		return err
	}
	if c.MaxFailures < 0 {
		return errors.New("--max-failures must be non-negative")
	}

	// Apply defaults for optional batch/worker fields when not set.
	if c.BatchSize == 0 {
		c.BatchSize = 1
	}
	if c.BatchTimeout == 0 {
		c.BatchTimeout = 100 * time.Millisecond
	}
	if c.Workers == 0 {
		c.Workers = 1
	}
	if c.QueueSize == 0 {
		c.QueueSize = 1000
	}
	if c.OnQueueFull == "" {
		c.OnQueueFull = "block"
	}

	if c.BatchSize < 1 {
		return errors.New("--batch-size must be at least 1")
	}
	if c.BatchTimeout <= 0 {
		return errors.New("--batch-timeout must be positive")
	}
	if c.Workers < 1 {
		return errors.New("--workers must be at least 1")
	}
	if c.QueueSize < 1 {
		return errors.New("--queue-size must be at least 1")
	}
	switch c.OnQueueFull {
	case "block", "fail":
	default:
		return errors.New("--on-queue-full must be block or fail")
	}
	if c.Sink != "kafka" && c.Sink != "http" && c.Workers > 1 {
		return errors.New("--workers > 1 is only supported for kafka and http sinks")
	}
	if c.Sink != "kafka" && c.BatchSize > 1 {
		return errors.New("--batch-size > 1 is only supported for kafka sink")
	}
	return nil
}

// validateTiming enforces that --rate, --speed, and --no-wait are mutually exclusive.
func (c *RuntimeConfig) validateTiming() error {
	hasRate := c.Rate > 0
	hasSpeed := c.Speed != 1.0 && c.Speed > 0
	hasNoWait := c.NoWait

	if hasNoWait && hasRate {
		return errors.New("--no-wait and --rate are mutually exclusive")
	}
	if hasNoWait && hasSpeed {
		return errors.New("--no-wait and --speed are mutually exclusive")
	}
	if hasRate && hasSpeed {
		return errors.New("--rate and --speed are mutually exclusive")
	}
	if c.Rate < 0 {
		return errors.New("--rate must be non-negative")
	}
	if !hasNoWait && !hasRate && c.Speed <= 0 {
		return errors.New("--speed must be positive unless --no-wait or --rate is set")
	}
	return nil
}
