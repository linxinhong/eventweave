"""Palo Alto Networks traffic encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import format_csv


@encoder("paloalto-traffic", content_type="text/plain")
class PaloAltoTrafficEncoder(Encoder):
    """Encode events as PAN-OS traffic CSV-style logs."""

    name = "paloalto-traffic"
    content_type = "text/plain"

    _required = ["receive_time", "serial", "src", "dst", "sport", "dport", "proto", "action"]
    _columns = [
        "receive_time",
        "serial",
        "type",
        "subtype",
        "src",
        "dst",
        "natsrc",
        "natdst",
        "rule",
        "app",
        "from",
        "to",
        "sport",
        "dport",
        "proto",
        "action",
        "bytes",
        "packets",
    ]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self._required if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        values = [event.attributes.get(col) for col in self._columns]
        return self._ok(format_csv(values))
