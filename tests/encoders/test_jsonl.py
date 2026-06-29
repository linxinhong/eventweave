"""Tests for the canonical JSONL encoder."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from eventweave.encoders import JsonlEncoder


def make_event(**attrs: object) -> Event:
    return Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="svc",
        event_type="test.event",
        event_time="2026-06-29T12:00:00+00:00",
        attributes=attrs,
    )


def test_jsonl_encoder_roundtrip() -> None:
    event = make_event(foo="bar", count=1)
    result = JsonlEncoder().encode(event)
    assert result.success
    parsed = json.loads(result.output)
    assert parsed["event_id"] == "evt-001"
    assert parsed["attributes"] == {"foo": "bar", "count": 1}
