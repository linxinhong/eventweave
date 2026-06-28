from datetime import UTC, datetime

import pytest

from eventweave.runtime.clock import RuntimeClock


def test_clock_no_wait_returns_start_time():
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    clock = RuntimeClock(start, speed=1.0, no_wait=True)
    assert clock.now() == start


def test_clock_invalid_speed_raises():
    with pytest.raises(ValueError):
        RuntimeClock(datetime.now(UTC), speed=0.0, no_wait=False)


def test_clock_no_wait_wait_until_returns_immediately():
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    clock = RuntimeClock(start, speed=1.0, no_wait=True)
    # Should not raise or sleep.
    clock.wait_until(datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC))
