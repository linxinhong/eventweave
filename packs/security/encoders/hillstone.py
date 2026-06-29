"""Hillstone NGFW encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import event_time_str


@encoder("hillstone-ngfw", content_type="text/plain")
class HillstoneNGFWEncoder(Encoder):
    """Encode events as Hillstone NGFW key-value logs."""

    name = "hillstone-ngfw"
    content_type = "text/plain"

    _required = ["devname", "srcip", "dstip", "action"]
    _fields: list[tuple[str, str]] = [
        ("hillstone_time", "time"),
        ("hillstone_devname", "devname"),
        ("hillstone_srcip", "srcip"),
        ("hillstone_dstip", "dstip"),
        ("hillstone_srcport", "srcport"),
        ("hillstone_dstport", "dstport"),
        ("hillstone_proto", "proto"),
        ("hillstone_action", "action"),
        ("hillstone_policy", "policy"),
        ("hillstone_app", "app"),
    ]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self._required if f not in event.attributes]
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
