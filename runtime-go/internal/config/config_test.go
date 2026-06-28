package config

import (
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
