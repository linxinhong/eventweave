"""Syslog RFC3164 and RFC5424 encoders."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from eventweave.encoders.base import Encoder, EncodeResult
from eventweave.encoders.registry import encoder


def _priority(event: Event) -> int:
    facility = event.attributes.get("syslog_facility", 16)
    severity = event.attributes.get("syslog_severity", 6)
    return int(facility) * 8 + int(severity)


def _message(event: Event) -> str:
    return str(
        event.attributes.get(
            "message",
            json.dumps(event.attributes, default=str, ensure_ascii=False),
        )
    )


def _hostname(event: Event) -> str:
    return str(event.attributes.get("hostname", event.source_id))


def _tag(event: Event) -> str:
    return str(event.attributes.get("syslog_tag", event.source_id))


@encoder("syslog-rfc3164", content_type="text/plain")
class Rfc3164Encoder(Encoder):
    """Encode an event as an RFC3164-style syslog message."""

    name = "syslog-rfc3164"
    content_type = "text/plain"

    def encode(self, event: Event) -> EncodeResult:
        try:
            priority = _priority(event)
        except (TypeError, ValueError) as exc:
            return self._fail(f"invalid syslog priority: {exc}")

        timestamp = event.event_time.strftime("%b %d %H:%M:%S")
        hostname = _hostname(event)
        tag = _tag(event)
        message = _message(event)
        line = f"<{priority}>{timestamp} {hostname} {tag}: {message}"
        return self._ok(line)


@encoder("syslog-rfc5424", content_type="text/plain")
class Rfc5424Encoder(Encoder):
    """Encode an event as an RFC5424-style syslog message."""

    name = "syslog-rfc5424"
    content_type = "text/plain"

    def encode(self, event: Event) -> EncodeResult:
        try:
            priority = _priority(event)
        except (TypeError, ValueError) as exc:
            return self._fail(f"invalid syslog priority: {exc}")

        timestamp = event.event_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        hostname = _hostname(event)
        app_name = event.source_id
        procid = event.flow_id or "-"
        msgid = event.event_type
        message = _message(event)
        line = (
            f"<{priority}>1 {timestamp} {hostname} {app_name} "
            f"{procid} {msgid} - {message}"
        )
        return self._ok(line)
