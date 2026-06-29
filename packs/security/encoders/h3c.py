"""H3C SecPath encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import event_time_str


@encoder("h3c-secpath", content_type="text/plain")
class H3CSecPathEncoder(Encoder):
    """Encode events as H3C SecPath firewall key-value logs."""

    name = "h3c-secpath"
    content_type = "text/plain"
    description = "H3C SecPath firewall key-value traffic log format."
    required_fields = ["devname", "srcip", "dstip", "action"]
    optional_fields = ["time", "srcport", "dstport", "proto", "policy", "app"]
    supported_event_types = ["firewall.traffic"]
    _fields: list[tuple[str, str]] = [
        ("h3c_time", "time"),
        ("h3c_devName", "devname"),
        ("h3c_srcIp", "srcip"),
        ("h3c_dstIp", "dstip"),
        ("h3c_srcPort", "srcport"),
        ("h3c_dstPort", "dstport"),
        ("h3c_protocol", "proto"),
        ("h3c_action", "action"),
        ("h3c_policy", "policy"),
        ("h3c_app", "app"),
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
