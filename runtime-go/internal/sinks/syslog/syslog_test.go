package syslog

import (
	"bufio"
	"encoding/json"
	"errors"
	"net"
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func eventWithID(id string) event.Event {
	return event.Event{
		EventID:    id,
		ScenarioID: "sc1",
		SourceID:   "src1",
		EventType:  "login",
		EventTime:  time.Now(),
	}
}

func startUDPServer(t *testing.T) (*net.UDPConn, chan string) {
	t.Helper()
	addr, err := net.ResolveUDPAddr("udp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("resolve udp: %v", err)
	}
	conn, err := net.ListenUDP("udp", addr)
	if err != nil {
		t.Fatalf("listen udp: %v", err)
	}
	messages := make(chan string, 10)
	go func() {
		defer close(messages)
		buf := make([]byte, 65535)
		for {
			n, _, err := conn.ReadFromUDP(buf)
			if err != nil {
				return
			}
			messages <- string(buf[:n])
		}
	}()
	return conn, messages
}

func startTCPServer(t *testing.T) (net.Listener, chan string) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen tcp: %v", err)
	}
	messages := make(chan string, 10)
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			scanner := bufio.NewScanner(conn)
			for scanner.Scan() {
				messages <- scanner.Text()
			}
			conn.Close()
		}
	}()
	return ln, messages
}

func TestSyslogUDPSendsMessage(t *testing.T) {
	server, messages := startUDPServer(t)
	defer server.Close()

	sink := New(server.LocalAddr().String(), "udp", 16, 6, "eventweave")
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	defer sink.Close()

	ev := eventWithID("e1")
	if err := sink.Write(ev); err != nil {
		t.Fatalf("write: %v", err)
	}

	select {
	case msg := <-messages:
		if !strings.Contains(msg, "eventweave") {
			t.Fatalf("expected tag in message: %s", msg)
		}
		if !strings.Contains(msg, "\"event_id\":\"e1\"") {
			t.Fatalf("expected json body in message: %s", msg)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout waiting for udp message")
	}
}

func TestSyslogTCPSendsMessage(t *testing.T) {
	server, messages := startTCPServer(t)
	defer server.Close()

	sink := New(server.Addr().String(), "tcp", 16, 6, "eventweave")
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	defer sink.Close()

	ev := eventWithID("e1")
	if err := sink.Write(ev); err != nil {
		t.Fatalf("write: %v", err)
	}

	select {
	case msg := <-messages:
		if !strings.Contains(msg, "eventweave") {
			t.Fatalf("expected tag in message: %s", msg)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout waiting for tcp message")
	}
}

func TestSyslogFormatterContainsTagAndJSON(t *testing.T) {
	sink := newSink("127.0.0.1:514", "udp", 16, 6, "eventweave", nil)
	msg := sink.format(`{"event_id":"e1"}`)
	if !strings.HasPrefix(msg, "<134>") {
		t.Fatalf("expected priority prefix, got: %s", msg)
	}
	if !strings.Contains(msg, "eventweave") {
		t.Fatalf("expected tag, got: %s", msg)
	}
	idx := strings.Index(msg, "{")
	if idx < 0 {
		t.Fatalf("expected json body in message: %s", msg)
	}
	var decoded map[string]string
	if err := json.Unmarshal([]byte(msg[idx:]), &decoded); err != nil {
		t.Fatalf("unmarshal body: %v", msg)
	}
	if decoded["event_id"] != "e1" {
		t.Fatalf("unexpected body: %v", decoded)
	}
}

func TestSyslogCountsFailure(t *testing.T) {
	dialer := &failingDialer{}
	sink := newSink("127.0.0.1:514", "udp", 16, 6, "eventweave", dialer)
	if err := sink.Open(); err == nil {
		t.Fatal("expected open error")
	}
	if sink.Count() != 0 || sink.Failed() != 0 {
		t.Fatalf("unexpected counts: count=%d failed=%d", sink.Count(), sink.Failed())
	}
}

func TestSyslogRequiresAddress(t *testing.T) {
	if err := ValidateConfig("", "udp"); err == nil {
		t.Fatal("expected error for missing address")
	}
	if err := ValidateConfig("127.0.0.1:514", "xxx"); err == nil {
		t.Fatal("expected error for unsupported protocol")
	}
	if err := ValidateConfig("127.0.0.1:514", "udp"); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

type failingDialer struct{}

func (f *failingDialer) Dial(network, address string) (net.Conn, error) {
	return nil, errors.New("dial failed")
}
