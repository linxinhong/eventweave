"""Qianxin NGFW encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import event_time_str


@encoder("qianxin-ngfw", content_type="text/plain")
class QianxinNGFWEncoder(Encoder):
    """Encode events as Qianxin NGFW key-value logs."""

    name = "qianxin-ngfw"
    content_type = "text/plain"

    _required = ["devname", "srcip", "dstip", "action"]
    _fields: list[tuple[str, str]] = [
        ("qianxin_time", "time"),
        ("qianxin_dev_name", "devname"),
        ("qianxin_srcip", "srcip"),
        ("qianxin_dstip", "dstip"),
        ("qianxin_srcport", "srcport"),
        ("qianxin_dstport", "dstport"),
        ("qianxin_proto", "proto"),
        ("qianxin_action", "action"),
        ("qianxin_policy", "policy"),
        ("qianxin_app", "app"),
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
