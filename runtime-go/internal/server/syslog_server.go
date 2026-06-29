package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"sync"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

const (
	udpClientTTL   = 5 * time.Minute
	udpCleanupFreq = 1 * time.Minute
)

const (
	syslogChannelBuffer = 1000
	syslogWriteTimeout  = 100 * time.Millisecond
)

// SyslogServer emits RFC3164-like syslog messages to connected clients.
type SyslogServer struct {
	id       string
	addr     string
	protocol string
	facility int
	severity int
	tag      string

	listener net.Listener
	connMu   sync.RWMutex
	conns    []net.Conn

	udpConn      *net.UDPConn
	clientsMu    sync.RWMutex
	udpClients   map[string]time.Time
	allowed      []*net.IPNet

	stats   EndpointStats
	statsMu sync.RWMutex

	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// NewSyslogServer creates a syslog server endpoint.
// Optional allowedCIDRs restrict which UDP sources may register as clients.
func NewSyslogServer(id, addr, protocol string, facility, severity int, tag string, allowedCIDRs ...string) *SyslogServer {
	ctx, cancel := context.WithCancel(context.Background())
	s := &SyslogServer{
		id:         id,
		addr:       addr,
		protocol:   protocol,
		facility:   facility,
		severity:   severity,
		tag:        tag,
		udpClients: make(map[string]time.Time),
		ctx:        ctx,
		cancel:     cancel,
	}
	for _, cidr := range allowedCIDRs {
		_, network, err := net.ParseCIDR(cidr)
		if err == nil {
			s.allowed = append(s.allowed, network)
		}
	}
	return s
}

// ID returns the endpoint identifier.
func (s *SyslogServer) ID() string { return s.id }

// Open starts the syslog listener.
func (s *SyslogServer) Open() error {
	switch s.protocol {
	case "udp":
		return s.openUDP()
	case "tcp":
		return s.openTCP()
	default:
		return fmt.Errorf("unsupported syslog protocol: %s", s.protocol)
	}
}

func (s *SyslogServer) openUDP() error {
	udpAddr, err := net.ResolveUDPAddr("udp", s.addr)
	if err != nil {
		return fmt.Errorf("resolve udp %s: %w", s.addr, err)
	}
	conn, err := net.ListenUDP("udp", udpAddr)
	if err != nil {
		return fmt.Errorf("udp listen %s: %w", s.addr, err)
	}
	s.udpConn = conn

	s.wg.Add(1)
	go s.udpRegisterLoop()
	s.wg.Add(1)
	go s.udpCleanupLoop()
	return nil
}

func (s *SyslogServer) openTCP() error {
	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return fmt.Errorf("tcp listen %s: %w", s.addr, err)
	}
	s.listener = ln

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		for {
			conn, err := ln.Accept()
			if err != nil {
				select {
				case <-s.ctx.Done():
					return
				default:
					continue
				}
			}
			s.connMu.Lock()
			s.conns = append(s.conns, conn)
			s.connMu.Unlock()
		}
	}()
	return nil
}

// Close stops the syslog listener.
func (s *SyslogServer) Close() error {
	s.cancel()
	if s.listener != nil {
		_ = s.listener.Close()
	}
	if s.udpConn != nil {
		_ = s.udpConn.Close()
	}
	s.wg.Wait()
	s.connMu.Lock()
	for _, conn := range s.conns {
		_ = conn.Close()
	}
	s.conns = nil
	s.connMu.Unlock()
	return nil
}

// Write delivers a syslog message to all connected clients.
func (s *SyslogServer) Write(ev event.Event) error {
	body, err := json.Marshal(ev)
	if err != nil {
		s.incrFailed()
		return err
	}
	msg := s.format(string(body))

	switch s.protocol {
	case "udp":
		return s.writeUDP(msg)
	case "tcp":
		return s.writeTCP(msg)
	}
	return nil
}

func (s *SyslogServer) writeTCP(msg string) error {
	s.connMu.RLock()
	conns := make([]net.Conn, len(s.conns))
	copy(conns, s.conns)
	s.connMu.RUnlock()

	if len(conns) == 0 {
		return nil
	}

	sent := 0
	var survivors []net.Conn
	for _, conn := range conns {
		_ = conn.SetWriteDeadline(time.Now().Add(syslogWriteTimeout))
		if _, err := conn.Write([]byte(msg)); err != nil {
			_ = conn.Close()
		} else {
			sent++
			survivors = append(survivors, conn)
		}
	}

	s.connMu.Lock()
	s.conns = survivors
	s.connMu.Unlock()

	if sent > 0 {
		s.incrEmitted()
	} else {
		s.incrFailed()
		return fmt.Errorf("no tcp client consumed message")
	}
	return nil
}

func (s *SyslogServer) writeUDP(msg string) error {
	if s.udpConn == nil {
		return fmt.Errorf("udp conn not open")
	}

	s.clientsMu.RLock()
	clients := make([]string, 0, len(s.udpClients))
	for addr := range s.udpClients {
		clients = append(clients, addr)
	}
	s.clientsMu.RUnlock()

	if len(clients) == 0 {
		return nil
	}

	sent := 0
	for _, addr := range clients {
		udpAddr, err := net.ResolveUDPAddr("udp", addr)
		if err != nil {
			continue
		}
		_ = s.udpConn.SetWriteDeadline(time.Now().Add(syslogWriteTimeout))
		if _, err := s.udpConn.WriteToUDP([]byte(msg), udpAddr); err == nil {
			sent++
		}
	}

	if sent > 0 {
		s.incrEmitted()
	} else {
		s.incrFailed()
		return fmt.Errorf("no udp client consumed message")
	}
	return nil
}

// isAllowed reports whether the given IP is in the allowlist.
// An empty allowlist permits all sources for backwards compatibility.
func (s *SyslogServer) isAllowed(ip net.IP) bool {
	if len(s.allowed) == 0 {
		return true
	}
	for _, network := range s.allowed {
		if network.Contains(ip) {
			return true
		}
	}
	return false
}

func (s *SyslogServer) udpRegisterLoop() {
	defer s.wg.Done()
	buf := make([]byte, 1024)
	for {
		select {
		case <-s.ctx.Done():
			return
		default:
		}

		_ = s.udpConn.SetReadDeadline(time.Now().Add(100 * time.Millisecond))
		_, addr, err := s.udpConn.ReadFromUDP(buf)
		if err != nil {
			continue
		}
		if addr == nil {
			continue
		}
		if !s.isAllowed(addr.IP) {
			continue
		}
		s.clientsMu.Lock()
		s.udpClients[addr.String()] = time.Now()
		s.clientsMu.Unlock()
	}
}

func (s *SyslogServer) cleanupClients() {
	s.clientsMu.Lock()
	defer s.clientsMu.Unlock()
	cutoff := time.Now().Add(-udpClientTTL)
	for addr, lastSeen := range s.udpClients {
		if lastSeen.Before(cutoff) {
			delete(s.udpClients, addr)
		}
	}
}

func (s *SyslogServer) udpCleanupLoop() {
	defer s.wg.Done()
	ticker := time.NewTicker(udpCleanupFreq)
	defer ticker.Stop()
	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			s.cleanupClients()
		}
	}
}

// Stats returns endpoint counters.
func (s *SyslogServer) Stats() EndpointStats {
	s.statsMu.RLock()
	defer s.statsMu.RUnlock()
	return s.stats
}

func (s *SyslogServer) incrEmitted() {
	s.statsMu.Lock()
	s.stats.Emitted++
	s.statsMu.Unlock()
}

func (s *SyslogServer) incrFailed() {
	s.statsMu.Lock()
	s.stats.Failed++
	s.statsMu.Unlock()
}

func (s *SyslogServer) format(message string) string {
	priority := s.facility*8 + s.severity
	timestamp := time.Now().Format(time.Stamp)
	return fmt.Sprintf("<%d>%s %s %s\n", priority, timestamp, s.tag, message)
}
