package server

import (
	"bufio"
	"net"
	"strings"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestSyslogTCPServerEmitsFilteredEvents(t *testing.T) {
	addr := "127.0.0.1:18082"
	srv := NewSyslogServer("syslog_tcp_test", addr, "tcp", 16, 6, "eventweave")
	if err := srv.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	defer srv.Close()

	time.Sleep(50 * time.Millisecond)

	conn, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer conn.Close()

	time.Sleep(50 * time.Millisecond)

	_ = srv.Write(event.Event{EventID: "1", SourceID: "edr-001", EventType: "user.login"})

	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	reader := bufio.NewReader(conn)
	line, err := reader.ReadString('\n')
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if !strings.Contains(line, "\"event_id\":\"1\"") {
		t.Fatalf("expected event id 1 in %q", line)
	}

	stats := srv.Stats()
	if stats.Emitted != 1 {
		t.Fatalf("expected 1 emitted, got %d", stats.Emitted)
	}
}

func TestSyslogUDPServerEmitsFilteredEvents(t *testing.T) {
	addr := "127.0.0.1:18083"
	srv := NewSyslogServer("syslog_udp_test", addr, "udp", 16, 6, "eventweave")
	if err := srv.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}
	defer srv.Close()

	time.Sleep(50 * time.Millisecond)

	clientAddr, _ := net.ResolveUDPAddr("udp", addr)
	clientConn, err := net.DialUDP("udp", nil, clientAddr)
	if err != nil {
		t.Fatalf("dial udp: %v", err)
	}
	defer clientConn.Close()

	// Send registration packet so server learns our address.
	_, _ = clientConn.Write([]byte("register"))

	time.Sleep(100 * time.Millisecond)

	_ = srv.Write(event.Event{EventID: "2", SourceID: "firewall-001", EventType: "firewall.allow"})

	buf := make([]byte, 4096)
	clientConn.SetReadDeadline(time.Now().Add(2 * time.Second))
	n, _, err := clientConn.ReadFromUDP(buf)
	if err != nil {
		t.Fatalf("read udp: %v", err)
	}
	line := string(buf[:n])
	if !strings.Contains(line, "\"event_id\":\"2\"") {
		t.Fatalf("expected event id 2 in %q", line)
	}

	stats := srv.Stats()
	if stats.Emitted != 1 {
		t.Fatalf("expected 1 emitted, got %d", stats.Emitted)
	}
}


