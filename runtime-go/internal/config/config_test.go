package config

import (
	"strings"
	"testing"
	"time"
)

func validConfig() RuntimeConfig {
	return RuntimeConfig{
		PlanDir: "/tmp/plan",
		Sink:    "stdout",
		Speed:   1,
		Timeout: 5 * time.Second,
	}
}

func TestValidateDefaultSink(t *testing.T) {
	cfg := validConfig()
	if err := cfg.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestValidateRequiresPlanDir(t *testing.T) {
	cfg := validConfig()
	cfg.PlanDir = ""
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for missing plan dir")
	}
}

func TestValidateUnknownSink(t *testing.T) {
	cfg := validConfig()
	cfg.Sink = "unknown"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for unknown sink")
	}
}

func TestValidateHTTPSinkRequiresURL(t *testing.T) {
	cfg := validConfig()
	cfg.Sink = "http"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for missing url")
	}
}

func TestValidateFileSinkRequiresOutput(t *testing.T) {
	cfg := validConfig()
	cfg.Sink = "file"
	cfg.Output = ""
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for missing output")
	}
}

func TestValidateKafkaSinkRequiresBrokersAndTopic(t *testing.T) {
	cfg := validConfig()
	cfg.Sink = "kafka"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for missing brokers")
	}
	cfg.Brokers = "localhost:9092"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for missing topic")
	}
	cfg.Topic = "events"
	if err := cfg.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestValidateSyslogSinkRequiresAddrAndProtocol(t *testing.T) {
	cfg := validConfig()
	cfg.Sink = "syslog"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for missing syslog addr")
	}
	cfg.SyslogAddr = "127.0.0.1:514"
	cfg.SyslogProto = "xxx"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for invalid protocol")
	}
	cfg.SyslogProto = "udp"
	if err := cfg.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestValidateSpeedMustBePositive(t *testing.T) {
	cfg := validConfig()
	cfg.Speed = 0
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for non-positive speed")
	}
	cfg.NoWait = true
	if err := cfg.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestValidateRateConflicts(t *testing.T) {
	cfg := validConfig()
	cfg.Rate = 100
	if err := cfg.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	cfg.NoWait = true
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for rate + no-wait")
	}
	cfg.NoWait = false

	cfg.Speed = 2
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for rate + speed")
	}
}

func TestValidateRateMustBePositive(t *testing.T) {
	cfg := validConfig()
	cfg.Rate = -1
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for negative rate")
	}
}

func TestValidateNoWaitConflictsWithSpeed(t *testing.T) {
	cfg := validConfig()
	cfg.NoWait = true
	cfg.Speed = 2
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for no-wait + speed")
	}
}

func TestValidateMaxFailuresMustBeNonNegative(t *testing.T) {
	cfg := validConfig()
	cfg.MaxFailures = -1
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for negative max-failures")
	}
	cfg.MaxFailures = 5
	if err := cfg.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}
func TestValidateUnknownEncoder(t *testing.T) {
	cfg := validConfig()
	cfg.Encoder = "no-such-encoder"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected error for unknown encoder")
	}
}

func TestValidateKnownEncoder(t *testing.T) {
	cfg := validConfig()
	cfg.Encoder = "jsonl"
	if err := cfg.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestValidateUpperBounds(t *testing.T) {
	cases := []struct {
		name   string
		apply  func(*RuntimeConfig)
		errMsg string
	}{
		{"rate", func(c *RuntimeConfig) { c.Rate = 2_000_000 }, "rate"},
		{"speed", func(c *RuntimeConfig) { c.Speed = 20_000 }, "speed"},
		{"workers", func(c *RuntimeConfig) { c.Workers = 2048 }, "workers"},
		{"queue-size", func(c *RuntimeConfig) { c.QueueSize = 2_000_000 }, "queue-size"},
		{"batch-size", func(c *RuntimeConfig) { c.BatchSize = 200_000 }, "batch-size"},
		{"batch-timeout", func(c *RuntimeConfig) { c.BatchTimeout = 10 * time.Minute }, "batch-timeout"},
		{"retries", func(c *RuntimeConfig) { c.Retries = 200 }, "retries"},
		{"max-retry-duration", func(c *RuntimeConfig) { c.MaxRetryDuration = 10 * time.Minute }, "max-retry-duration"},
		{"backoff-factor", func(c *RuntimeConfig) { c.BackoffFactor = 100 }, "backoff-factor"},
		{"timeout", func(c *RuntimeConfig) { c.Timeout = 10 * time.Minute }, "timeout"},
		{"limit", func(c *RuntimeConfig) { c.Limit = 200_000_000 }, "limit"},
		{"syslog-facility", func(c *RuntimeConfig) { c.Facility = 30 }, "syslog-facility"},
		{"syslog-severity", func(c *RuntimeConfig) { c.Severity = 10 }, "syslog-severity"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cfg := validConfig()
			tc.apply(&cfg)
			if err := cfg.Validate(); err == nil {
				t.Fatalf("expected error for %s upper bound", tc.name)
			} else if !strings.Contains(err.Error(), tc.errMsg) {
				t.Fatalf("expected error to mention %q, got %v", tc.errMsg, err)
			}
		})
	}
}
