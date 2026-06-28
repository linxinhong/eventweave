package ratelimit

import (
	"testing"
	"time"
)

func TestNoWaitLimiterIsInstant(t *testing.T) {
	lim := &NoWaitLimiter{}
	start := time.Now()
	for i := 0; i < 100; i++ {
		if err := lim.Wait(); err != nil {
			t.Fatalf("wait: %v", err)
		}
	}
	if time.Since(start) > 10*time.Millisecond {
		t.Fatalf("no-wait should be fast, took %s", time.Since(start))
	}
}

func TestRateLimiterPacesEvents(t *testing.T) {
	lim, err := NewRateLimiter(100) // 100 events/sec -> 10ms each
	if err != nil {
		t.Fatalf("new limiter: %v", err)
	}
	start := time.Now()
	for i := 0; i < 5; i++ {
		if err := lim.Wait(); err != nil {
			t.Fatalf("wait: %v", err)
		}
	}
	elapsed := time.Since(start)
	// 5 events at 100 eps should take ~40ms (4 intervals)
	if elapsed < 35*time.Millisecond || elapsed > 120*time.Millisecond {
		t.Fatalf("unexpected elapsed: %s", elapsed)
	}
}

func TestRateLimiterRejectsNonPositiveRate(t *testing.T) {
	if _, err := NewRateLimiter(0); err == nil {
		t.Fatal("expected error for zero rate")
	}
	if _, err := NewRateLimiter(-1); err == nil {
		t.Fatal("expected error for negative rate")
	}
}
