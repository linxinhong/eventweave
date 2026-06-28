"""Runtime clock with optional speed-up."""

from __future__ import annotations

import time
from datetime import datetime, timedelta


class RuntimeClock:
    """Clock that maps scenario time to real time with optional acceleration."""

    def __init__(
        self,
        start_time: datetime,
        speed: float = 1.0,
        no_wait: bool = False,
    ) -> None:
        if speed <= 0 and not no_wait:
            raise ValueError("speed must be positive unless no_wait is enabled")
        self._scenario_start = start_time
        self._real_start = time.monotonic()
        self.speed = speed
        self.no_wait = no_wait

    def now(self) -> datetime:
        """Return the current scenario time."""
        if self.no_wait:
            return self._scenario_start
        elapsed_real = time.monotonic() - self._real_start
        elapsed_scenario = elapsed_real * self.speed
        return self._scenario_start + timedelta(seconds=elapsed_scenario)

    def wait_until(self, target_time: datetime) -> None:
        """Sleep until the real time corresponding to target scenario time."""
        if self.no_wait:
            return
        delta = (target_time - self._scenario_start).total_seconds()
        real_delta = delta / self.speed
        target_real = self._real_start + real_delta
        now = time.monotonic()
        sleep_seconds = target_real - now
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
