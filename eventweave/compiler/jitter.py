"""Deterministic timestamp jitter for compiled events."""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta

from eventweave.compiler.duration import parse_duration
from eventweave.core.event import Event
from eventweave.core.scenario import Scenario


class JitterApplier:
    """Apply deterministic timestamp jitter to a list of events."""

    def __init__(self, scenario: Scenario, seed: int | None = None) -> None:
        self.scenario = scenario
        # Salt the RNG so jitter is independent from timeline expansion and noise.
        self.rng = random.Random((seed or 0) + 99)

    def apply(self, events: list[Event]) -> list[Event]:
        """Return events with jittered event_time values."""
        config = self.scenario.jitter
        if config is None or not config.enabled:
            return events

        max_offset = parse_duration(config.max_offset)
        max_seconds = max_offset.total_seconds()

        if config.preserve_order:
            return self._apply_preserve_order(events, max_seconds)

        for event in events:
            offset = self.rng.uniform(-max_seconds, max_seconds)
            event.event_time = event.event_time + timedelta(seconds=offset)
        return events

    def _apply_preserve_order(self, events: list[Event], max_seconds: float) -> list[Event]:
        # Group by flow to maintain per-flow order; noise with no flow_id is independent.
        by_flow: dict[str | None, list[Event]] = defaultdict(list)
        for event in events:
            by_flow[event.flow_id].append(event)

        jittered: list[Event] = []
        for _flow_id, flow_events in by_flow.items():
            # Sort by original time to establish the canonical order.
            ordered = sorted(flow_events, key=lambda e: (e.event_time, e.event_id))
            prev_time: datetime | None = None
            for event in ordered:
                offset = self.rng.uniform(-max_seconds, max_seconds)
                new_time = event.event_time + timedelta(seconds=offset)
                if prev_time is not None:
                    # Clamp to at least 1 microsecond after the previous event.
                    min_time = prev_time + timedelta(microseconds=1)
                    if new_time < min_time:
                        new_time = min_time
                event.event_time = new_time
                prev_time = new_time
            jittered.extend(ordered)

        return jittered
