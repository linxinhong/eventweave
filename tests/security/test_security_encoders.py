"""Tests for security pack encoders."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from packs.security.encoders.suricata_eve import SuricataEveEncoder
from packs.security.encoders.windows_event import WindowsEventJsonEncoder


def make_event(**attrs: object) -> Event:
    return Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="sensor",
        event_type="alert",
        event_time="2026-06-29T12:00:00+00:00",
        attributes=attrs,
    )


def test_suricata_eve_basic() -> None:
    event = make_event(
        event_type="alert",
        src_ip="10.0.0.1",
        dest_ip="10.0.0.2",
        src_port=12345,
        dest_port=80,
        proto="TCP",
    )
    result = SuricataEveEncoder().encode(event)
    assert result.success
    parsed = json.loads(result.output)
    assert parsed["event_type"] == "alert"
    assert parsed["src_ip"] == "10.0.0.1"
    assert parsed["dest_ip"] == "10.0.0.2"


def test_suricata_eve_missing_fields() -> None:
    result = SuricataEveEncoder().encode(make_event())
    assert not result.success
    assert "missing required fields" in result.error_reason


def test_windows_event_json_basic() -> None:
    event = make_event(EventID=4624, ProviderName="Microsoft-Windows-Security-Auditing")
    result = WindowsEventJsonEncoder().encode(event)
    assert result.success
    parsed = json.loads(result.output)
    assert parsed["Event"]["System"]["EventID"] == 4624
    assert parsed["Event"]["System"]["Computer"] == "sensor"


def test_windows_event_json_missing_event_id() -> None:
    result = WindowsEventJsonEncoder().encode(make_event())
    assert not result.success
    assert "missing required fields: EventID" in result.error_reason
