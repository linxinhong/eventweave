"""Tests for the nginx access log encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import NginxAccessEncoder


def make_event(**attrs: object) -> Event:
    return Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="nginx",
        event_type="http.request",
        event_time="2026-06-29T12:00:00+00:00",
        attributes=attrs,
    )


def test_nginx_combined_log() -> None:
    event = make_event(
        remote_addr="192.168.1.1",
        request="GET /index.html HTTP/1.1",
        status=200,
        body_bytes_sent=1234,
    )
    result = NginxAccessEncoder().encode(event)
    assert result.success
    assert result.output.startswith('192.168.1.1 - - [29/Jun/2026:12:00:00 +0000]')
    assert '"GET /index.html HTTP/1.1" 200 1234' in result.output


def test_nginx_missing_fields() -> None:
    event = make_event(remote_addr="192.168.1.1")
    result = NginxAccessEncoder().encode(event)
    assert not result.success
    assert "missing required fields" in result.error_reason
