package clock

import (
	"context"
	"errors"
	"time"
)

// RuntimeClock maps scenario time to real time with optional acceleration.
type RuntimeClock struct {
	scenarioStart time.Time
	realStart     time.Time
	speed         float64
	noWait        bool
}

// New creates a clock starting at the given scenario time.
func New(start time.Time, speed float64, noWait bool) (*RuntimeClock, error) {
	if speed <= 0 && !noWait {
		return nil, errors.New("speed must be positive unless no-wait is enabled")
	}
	return &RuntimeClock{
		scenarioStart: start,
		realStart:     time.Now(),
		speed:         speed,
		noWait:        noWait,
	}, nil
}

// WaitUntil sleeps until the real time corresponding to target scenario time.
// It returns ctx.Err() if the context is cancelled before the target time.
func (c *RuntimeClock) WaitUntil(ctx context.Context, target time.Time) error {
	if c.noWait {
		return nil
	}
	delta := target.Sub(c.scenarioStart).Seconds()
	realDelta := delta / c.speed
	targetReal := c.realStart.Add(time.Duration(realDelta * float64(time.Second)))
	sleep := time.Until(targetReal)
	if sleep <= 0 {
		return nil
	}

	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(sleep):
		return nil
	}
}
