"""Tests for syslog encoders."""

from __future__ import annotations

import re

from eventweave.core.event import Event
from eventweave.encoders import Rfc3164Encoder, Rfc5424Encoder


def make_event(**attrs: object) -> Event:
    base = {
        "syslog_facility": 16,
        "syslog_severity": 6,
        "hostname": "host01",
        "syslog_tag": "app",
        "message": "hello",
    }
    base.update(attrs)
    return Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="svc",
        event_type="test.event",
        event_time="2026-06-29T12:00:00+00:00",
        attributes=base,
    )


def test_rfc3164_basic() -> None:
    result = Rfc3164Encoder().encode(make_event())
    assert result.success
    assert re.match(r"<134>\w+ \d+ \d+:\d+:\d+ host01 app: hello", result.output)


def test_rfc5424_basic() -> None:
    result = Rfc5424Encoder().encode(make_event())
    assert result.success
    assert result.output.startswith("<134>1 2026-06-29T12:00:00.000000Z host01 svc")


def test_invalid_priority() -> None:
    result = Rfc3164Encoder().encode(make_event(syslog_facility="bad"))
    assert not result.success
    assert "invalid syslog priority" in result.error_reason
