"""Fortinet FortiGate encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import event_time_str


@encoder("fortinet-fortigate", content_type="text/plain")
class FortinetFortigateEncoder(Encoder):
    """Encode events as FortiGate key-value traffic logs."""

    name = "fortinet-fortigate"
    content_type = "text/plain"

    _required = ["devname", "type", "subtype", "srcip", "dstip", "action"]
    _fields: list[tuple[str, str]] = [
        ("date", "date"),
        ("time", "time"),
        ("devname", "devname"),
        ("type", "type"),
        ("subtype", "subtype"),
        ("srcip", "srcip"),
        ("dstip", "dstip"),
        ("srcport", "srcport"),
        ("dstport", "dstport"),
        ("proto", "proto"),
        ("action", "action"),
        ("service", "service"),
        ("policyid", "policyid"),
        ("sentbyte", "sentbyte"),
        ("rcvdbyte", "rcvdbyte"),
        ("eventtime", "eventtime"),
    ]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self._required if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        attrs = dict(event.attributes)
        if "date" not in attrs:
            attrs["date"] = event.event_time.strftime("%Y-%m-%d")
        if "time" not in attrs:
            attrs["time"] = event.event_time.strftime("%H:%M:%S")
        if "eventtime" not in attrs:
            attrs["eventtime"] = str(int(event.event_time.timestamp() * 1000))

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
