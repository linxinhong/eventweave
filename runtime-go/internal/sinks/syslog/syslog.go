package syslog

import (
	"encoding/json"
	"fmt"
	"net"
	"strings"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// NetworkDialer abstracts net.Dial for testing.
type NetworkDialer interface {
	Dial(network, address string) (net.Conn, error)
}

type defaultDialer struct{}

func (d defaultDialer) Dial(network, address string) (net.Conn, error) {
	return net.Dial(network, address)
}

// Sink sends events as syslog messages.
type Sink struct {
	address  string
	protocol string
	facility int
	severity int
	tag      string
	dialer   NetworkDialer
	conn     net.Conn
	count    int
	failed   int
}

// New creates a syslog sink.
func New(address, protocol string, facility, severity int, tag string) *Sink {
	return newSink(address, protocol, facility, severity, tag, defaultDialer{})
}

func newSink(address, protocol string, facility, severity int, tag string, dialer NetworkDialer) *Sink {
	return &Sink{
		address:  address,
		protocol: protocol,
		facility: facility,
		severity: severity,
		tag:      tag,
		dialer:   dialer,
	}
}

// Open dials the syslog server.
func (s *Sink) Open() error {
	conn, err := s.dialer.Dial(s.protocol, s.address)
	if err != nil {
		return err
	}
	s.conn = conn
	return nil
}

// Write sends one event as an RFC3164-like syslog message.
func (s *Sink) Write(ev event.Event) error {
	if s.conn == nil {
		s.failed++
		return fmt.Errorf("syslog sink is not open")
	}
	body, err := json.Marshal(ev)
	if err != nil {
		s.failed++
		return err
	}
	msg := s.format(string(body))
	if _, err := s.conn.Write([]byte(msg)); err != nil {
		s.failed++
		return err
	}
	s.count++
	return nil
}

func (s *Sink) format(message string) string {
	priority := s.facility*8 + s.severity
	timestamp := time.Now().Format(time.Stamp)
	return fmt.Sprintf("<%d>%s %s %s\n", priority, timestamp, s.tag, message)
}

// Flush is a no-op.
func (s *Sink) Flush() error { return nil }

// Close closes the connection.
func (s *Sink) Close() error {
	if s.conn == nil {
		return nil
	}
	return s.conn.Close()
}

// Count returns successful writes.
func (s *Sink) Count() int { return s.count }

// Failed returns failed writes.
func (s *Sink) Failed() int { return s.failed }

// ValidateConfig checks required syslog parameters.
func ValidateConfig(address, protocol string) error {
	if address == "" {
		return fmt.Errorf("--syslog-addr is required for syslog sink")
	}
	protocol = strings.ToLower(protocol)
	if protocol != "udp" && protocol != "tcp" {
		return fmt.Errorf("unsupported syslog protocol: %s (use udp or tcp)", protocol)
	}
	return nil
}
