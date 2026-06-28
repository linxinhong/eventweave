package config

import (
	"errors"
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
	Timeout time.Duration
	Retries int
}

// Validate checks that the config is usable.
func (c *RuntimeConfig) Validate() error {
	if c.PlanDir == "" {
		return errors.New("plan directory is required")
	}
	switch c.Sink {
	case "stdout", "file", "null", "http":
	default:
		return errors.New("sink must be one of: stdout, file, null, http")
	}
	if c.Sink == "http" && c.URL == "" {
		return errors.New("--url is required for http sink")
	}
	if c.Sink == "file" && c.Output == "" {
		return errors.New("--output is required for file sink")
	}
	if !c.NoWait && c.Speed <= 0 {
		return errors.New("--speed must be positive unless --no-wait is set")
	}
	return nil
}
