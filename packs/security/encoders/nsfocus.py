"""NSFOCUS IPS encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import format_json


@encoder("nsfocus-ips", content_type="application/x-ndjson")
class NSFOCUSIPSEncoder(Encoder):
    """Encode events as NSFOCUS IPS/WAF JSON alert logs."""

    name = "nsfocus-ips"
    content_type = "application/x-ndjson"

    _required = ["devname", "srcip", "dstip", "attack_name"]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self._required if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        record: dict[str, object] = {
            "devname": event.attributes["devname"],
            "srcip": event.attributes["srcip"],
            "dstip": event.attributes["dstip"],
            "attack_name": event.attributes["attack_name"],
        }
        optional = ["sport", "dport", "proto", "severity", "category", "rule_id"]
        for key in optional:
            if key in event.attributes:
                record[key] = event.attributes[key]
        return self._ok(format_json(event, record))
