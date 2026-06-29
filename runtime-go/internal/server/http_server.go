package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

const (
	httpChannelBuffer   = 1000
	httpWriteTimeout    = 100 * time.Millisecond
	httpReplayBuffer    = 1000
)

// HTTPServer streams events over HTTP as newline-delimited JSON.
type HTTPServer struct {
	id       string
	addr     string
	path     string
	enc      encoder.Encoder
	server   *http.Server
	mu       sync.RWMutex
	subs     []chan event.Event
	buffer   []event.Event
	stats    EndpointStats
	statsMu  sync.RWMutex
	ctx      context.Context
	cancel   context.CancelFunc
	listener net.Listener
}

// NewHTTPServer creates an HTTP endpoint.
func NewHTTPServer(id, addr, path string, enc encoder.Encoder) *HTTPServer {
	if path == "" {
		path = "/events"
	}
	ctx, cancel := context.WithCancel(context.Background())
	return &HTTPServer{
		id:     id,
		addr:   addr,
		path:   path,
		enc:    enc,
		ctx:    ctx,
		cancel: cancel,
	}
}

// ID returns the endpoint identifier.
func (s *HTTPServer) ID() string { return s.id }

// Open starts the HTTP server.
func (s *HTTPServer) Open() error {
	mux := http.NewServeMux()
	mux.HandleFunc(s.path, s.handleEvents)

	s.server = &http.Server{
		Addr:    s.addr,
		Handler: mux,
	}

	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return fmt.Errorf("http listener %s: %w", s.addr, err)
	}
	s.listener = ln

	go func() {
		_ = s.server.Serve(s.listener)
	}()

	return nil
}

// Close stops the HTTP server.
func (s *HTTPServer) Close() error {
	s.cancel()
	if s.server != nil {
		_ = s.server.Close()
	}
	if s.listener != nil {
		_ = s.listener.Close()
	}
	s.mu.Lock()
	for _, ch := range s.subs {
		close(ch)
	}
	s.subs = nil
	s.mu.Unlock()
	return nil
}

// Write broadcasts an event to all connected HTTP clients and retains it for replay.
func (s *HTTPServer) Write(ev event.Event) error {
	if _, err := s.encode(ev); err != nil {
		s.incrFailed()
		return err
	}

	s.mu.Lock()
	s.buffer = append(s.buffer, ev)
	if len(s.buffer) > httpReplayBuffer {
		s.buffer = s.buffer[len(s.buffer)-httpReplayBuffer:]
	}
	subs := make([]chan event.Event, len(s.subs))
	copy(subs, s.subs)
	s.mu.Unlock()

	sent := 0
	for _, ch := range subs {
		select {
		case ch <- ev:
			sent++
		case <-time.After(httpWriteTimeout):
			// slow client; drop event for this subscriber
		}
	}

	if len(subs) == 0 {
		// No active client, but event is buffered for replay.
		return nil
	}

	if sent > 0 {
		s.incrEmitted()
	} else {
		s.incrFailed()
		return fmt.Errorf("no client consumed event")
	}
	return nil
}

func (s *HTTPServer) encode(ev event.Event) ([]byte, error) {
	if s.enc != nil {
		return s.enc.Encode(ev)
	}
	return json.Marshal(ev)
}

// Stats returns endpoint counters.
func (s *HTTPServer) Stats() EndpointStats {
	s.statsMu.RLock()
	defer s.statsMu.RUnlock()
	return s.stats
}

func (s *HTTPServer) incrEmitted() {
	s.statsMu.Lock()
	s.stats.Emitted++
	s.statsMu.Unlock()
}

func (s *HTTPServer) incrFailed() {
	s.statsMu.Lock()
	s.stats.Failed++
	s.statsMu.Unlock()
}

func (s *HTTPServer) handleEvents(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if s.enc != nil {
		w.Header().Set("Content-Type", s.enc.ContentType())
	} else {
		w.Header().Set("Content-Type", "text/event-stream")
	}
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.WriteHeader(http.StatusOK)
	if f, ok := w.(http.Flusher); ok {
		f.Flush()
	}

	ch := make(chan event.Event, httpChannelBuffer)
	s.mu.Lock()
	// Replay buffered events to the new client.
	replay := make([]event.Event, len(s.buffer))
	copy(replay, s.buffer)
	s.subs = append(s.subs, ch)
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		for i, sub := range s.subs {
			if sub == ch {
				s.subs = append(s.subs[:i], s.subs[i+1:]...)
				break
			}
		}
		s.mu.Unlock()
	}()

	writeEvent := func(ev event.Event) bool {
		body, err := s.encode(ev)
		if err != nil {
			return true
		}
		_, _ = fmt.Fprintf(w, "data: %s\n\n", body)
		if f, ok := w.(http.Flusher); ok {
			f.Flush()
		}
		return true
	}

	for _, ev := range replay {
		if !writeEvent(ev) {
			return
		}
	}

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-r.Context().Done():
			return
		case ev, ok := <-ch:
			if !ok {
				return
			}
			writeEvent(ev)
		}
	}
}
