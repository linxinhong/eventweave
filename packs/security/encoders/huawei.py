"""Huawei USG encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import event_time_str


@encoder("huawei-usg", content_type="text/plain")
class HuaweiUSGEncoder(Encoder):
    """Encode events as Huawei USG firewall key-value logs."""

    name = "huawei-usg"
    content_type = "text/plain"

    _required = ["devname", "srcip", "dstip", "action"]
    _fields: list[tuple[str, str]] = [
        ("huawei_time", "time"),
        ("huawei_devname", "devname"),
        ("huawei_srcip", "srcip"),
        ("huawei_dstip", "dstip"),
        ("huawei_srcport", "srcport"),
        ("huawei_dstport", "dstport"),
        ("huawei_proto", "proto"),
        ("huawei_action", "action"),
        ("huawei_policy", "policy"),
        ("huawei_app", "app"),
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
