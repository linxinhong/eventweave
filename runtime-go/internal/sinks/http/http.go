package http

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// Sink posts events as JSON to a URL.
type Sink struct {
	url     string
	client  *http.Client
	retries int
	count   int
	failed  int
}

// New creates an HTTP sink.
func New(url string, timeout time.Duration, retries int) *Sink {
	return &Sink{
		url:     url,
		client:  &http.Client{Timeout: timeout},
		retries: retries,
	}
}

// Open initializes the sink.
func (s *Sink) Open() error { return nil }

// Write posts one event.
func (s *Sink) Write(ev event.Event) error {
	body, err := json.Marshal(ev)
	if err != nil {
		s.failed++
		return err
	}

	attempt := 0
	for {
		req, err := http.NewRequest(http.MethodPost, s.url, bytes.NewReader(body))
		if err != nil {
			s.failed++
			return err
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := s.client.Do(req)
		if err != nil {
			if attempt < s.retries {
				attempt++
				continue
			}
			s.failed++
			return err
		}
		resp.Body.Close()

		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			s.count++
			return nil
		}
		// Retry only on 5xx server errors.
		if resp.StatusCode >= 500 && resp.StatusCode < 600 && attempt < s.retries {
			attempt++
			continue
		}
		s.failed++
		return fmt.Errorf("http sink received status %d", resp.StatusCode)
	}
}

// Flush is a no-op.
func (s *Sink) Flush() error { return nil }

// Close is a no-op.
func (s *Sink) Close() error { return nil }

// Count returns successful posts.
func (s *Sink) Count() int { return s.count }

// Failed returns failed posts.
func (s *Sink) Failed() int { return s.failed }
