// Package ratelimit provides pluggable rate control for event emission.
package ratelimit

import (
	"errors"
	"time"
)

// Limiter controls the pace of event emission.
type Limiter interface {
	Wait() error
}

// NoWaitLimiter returns immediately.
type NoWaitLimiter struct{}

// Wait implements Limiter.
func (n *NoWaitLimiter) Wait() error { return nil }

// RateLimiter paces events at a fixed events-per-second rate.
type RateLimiter struct {
	interval time.Duration
	last     time.Time
}

// NewRateLimiter creates a limiter for the given events-per-second rate.
func NewRateLimiter(rate float64) (*RateLimiter, error) {
	if rate <= 0 {
		return nil, errors.New("rate must be positive")
	}
	interval := time.Duration(float64(time.Second) / rate)
	if interval <= 0 {
		interval = time.Nanosecond
	}
	return &RateLimiter{interval: interval, last: time.Now()}, nil
}

// Wait sleeps until the next event slot.
func (r *RateLimiter) Wait() error {
	next := r.last.Add(r.interval)
	now := time.Now()
	if next.After(now) {
		time.Sleep(next.Sub(now))
	}
	r.last = next
	return nil
}
