package http

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

var (
	forbiddenHosts = map[string]struct{}{
		"localhost":                   {},
		"metadata":                    {},
		"metadata.google.internal":    {},
		"metadata.google.internal.":   {},
	}
	forbiddenSuffixes = []string{".local", ".internal", ".localhost"}
)

// isForbiddenHost reports whether the host is a known internal name.
func isForbiddenHost(host string) bool {
	lower := strings.ToLower(strings.TrimRight(host, "."))
	if _, ok := forbiddenHosts[lower]; ok {
		return true
	}
	for _, suffix := range forbiddenSuffixes {
		if strings.HasSuffix(lower, suffix) {
			return true
		}
	}
	return false
}

// isForbiddenIP reports whether the address is loopback, link-local, private,
// multicast, reserved, or one of the commonly exploited documentation ranges.
func isForbiddenIP(ip net.IP) bool {
	if ip.IsLoopback() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() ||
		ip.IsPrivate() || ip.IsMulticast() || ip.IsUnspecified() {
		return true
	}

	forbiddenRanges := []string{
		"192.0.0.0/24",
		"192.0.2.0/24",
		"198.51.100.0/24",
		"203.0.113.0/24",
		"233.252.0.0/24",
		"198.18.0.0/15",
		"240.0.0.0/4",
		"255.255.255.255/32",
		"fc00::/7",
		"fe80::/10",
	}
	for _, cidr := range forbiddenRanges {
		_, network, err := net.ParseCIDR(cidr)
		if err != nil {
			continue
		}
		if network.Contains(ip) {
			return true
		}
	}
	return false
}

// IsSafeURL validates that rawURL is an http(s) endpoint and not an internal
// or reserved address. Set allowInternal to skip the host/IP checks for
// trusted test environments.
func IsSafeURL(rawURL string, allowInternal bool) error {
	if allowInternal {
		return nil
	}

	parsed, err := url.Parse(rawURL)
	if err != nil {
		return fmt.Errorf("invalid URL: %w", err)
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return fmt.Errorf("http sink only supports http/https URLs, got %q", parsed.Scheme)
	}

	host := parsed.Hostname()
	if host == "" {
		return errors.New("http sink URL is missing a host")
	}
	if isForbiddenHost(host) {
		return fmt.Errorf("http sink URL points to forbidden host: %s", host)
	}

	if ip := net.ParseIP(host); ip != nil {
		if isForbiddenIP(ip) {
			return fmt.Errorf("http sink URL points to forbidden IP address: %s", host)
		}
	}

	return nil
}

// Sink posts events as JSON to a URL.
type Sink struct {
	url              string
	client           *http.Client
	retries          int
	maxRetryDuration time.Duration
	backoffFactor    float64
	count            int
	failed           int
	allowInternal    bool
}

// New creates an HTTP sink.
func New(url string, timeout, maxRetryDuration time.Duration, retries int, backoffFactor float64, allowInternal bool) (*Sink, error) {
	if err := IsSafeURL(url, allowInternal); err != nil {
		return nil, err
	}
	return &Sink{
		url: url,
		client: &http.Client{
			Timeout: timeout,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				return errors.New("http sink redirects are disabled")
			},
		},
		retries:          retries,
		maxRetryDuration: maxRetryDuration,
		backoffFactor:    backoffFactor,
		allowInternal:    allowInternal,
	}, nil
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

	start := time.Now()
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
			if s.shouldRetry(attempt, start) {
				s.sleep(attempt)
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
		// Retry on 429 and 5xx server errors.
		if (resp.StatusCode == 429 || (resp.StatusCode >= 500 && resp.StatusCode < 600)) && s.shouldRetry(attempt, start) {
			s.sleep(attempt)
			attempt++
			continue
		}
		s.failed++
		return fmt.Errorf("http sink received status %d", resp.StatusCode)
	}
}

func (s *Sink) shouldRetry(attempt int, start time.Time) bool {
	if attempt >= s.retries {
		return false
	}
	if s.maxRetryDuration > 0 && time.Since(start) >= s.maxRetryDuration {
		return false
	}
	return true
}

func (s *Sink) sleep(attempt int) {
	delay := s.backoffFactor * math.Pow(2, float64(attempt))
	if delay > 30 {
		delay = 30
	}
	time.Sleep(time.Duration(delay) * time.Second)
}

// Flush is a no-op.
func (s *Sink) Flush() error { return nil }

// Close is a no-op.
func (s *Sink) Close() error { return nil }

// Count returns successful posts.
func (s *Sink) Count() int { return s.count }

// Failed returns failed posts.
func (s *Sink) Failed() int { return s.failed }
