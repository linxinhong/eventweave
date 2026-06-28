"""Schedule events from a runtime plan."""

from __future__ import annotations

from eventweave.core.event import Event


def sort_events(events: list[Event]) -> list[Event]:
    """Return events sorted by scenario time and deterministic event id."""
    return sorted(events, key=lambda e: (e.event_time, e.event_id))
