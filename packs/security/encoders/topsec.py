"""Topsec NGFW encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import event_time_str


@encoder("topsec-ngfw", content_type="text/plain")
class TopsecNGFWEncoder(Encoder):
    """Encode events as Topsec NGFW key-value logs."""

    name = "topsec-ngfw"
    content_type = "text/plain"
    description = "Topsec NGFW key-value traffic log format."
    required_fields = ["devname", "srcip", "dstip", "action"]
    optional_fields = ["time", "srcport", "dstport", "proto", "policy", "app"]
    supported_event_types = ["firewall.traffic"]
    _fields: list[tuple[str, str]] = [
        ("topsec_time", "time"),
        ("topsec_devname", "devname"),
        ("topsec_srcip", "srcip"),
        ("topsec_dstip", "dstip"),
        ("topsec_srcport", "srcport"),
        ("topsec_dstport", "dstport"),
        ("topsec_proto", "proto"),
        ("topsec_action", "action"),
        ("topsec_policy", "policy"),
        ("topsec_app", "app"),
    ]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        attrs = dict(event.attributes)
        if "time" not in attrs:
            attrs["time"] = event_time_str(event)

        parts: list[str] = []
        for out_key, attr_name in self._fields:
            value = attrs.get(attr_name)
            if value is None:
                continue
            if isinstance(value, (int, float)):
                parts.append(f"{out_key}={value}")
            else:
                parts.append(f'{out_key}="{value}"')
        return self._ok(" ".join(parts))
