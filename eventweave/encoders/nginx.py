"""Nginx access log encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders.base import Encoder, EncodeResult
from eventweave.encoders.registry import encoder


@encoder("nginx-access", content_type="text/plain")
class NginxAccessEncoder(Encoder):
    """Encode an event as an nginx combined log format line."""

    name = "nginx-access"
    content_type = "text/plain"
    description = "nginx combined log format."
    required_fields = ["remote_addr", "request", "status", "body_bytes_sent"]
    optional_fields = ["remote_user", "http_referer", "http_user_agent"]
    supported_event_types = ["http.request"]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        time_local = event.event_time.strftime("%d/%b/%Y:%H:%M:%S %z")
        remote_addr = event.attributes["remote_addr"]
        remote_user = event.attributes.get("remote_user", "-")
        request = event.attributes["request"]
        status = event.attributes["status"]
        body_bytes_sent = event.attributes["body_bytes_sent"]
        http_referer = event.attributes.get("http_referer", "-")
        http_user_agent = event.attributes.get("http_user_agent", "-")

        line = (
            f'{remote_addr} - {remote_user} [{time_local}] '
            f'"{request}" {status} {body_bytes_sent} '
            f'"{http_referer}" "{http_user_agent}"'
        )
        return self._ok(line)
