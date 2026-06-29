"""DBAPPSecurity WAF encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import format_json


@encoder("dbappsecurity-waf", content_type="application/x-ndjson")
class DBAPPSecurityWAFEncoder(Encoder):
    """Encode events as DBAPPSecurity WAF JSON attack logs."""

    name = "dbappsecurity-waf"
    content_type = "application/x-ndjson"
    description = "DBAPPSecurity WAF JSON attack log format."
    required_fields = ["devname", "srcip", "dstip", "url", "attack_type"]
    optional_fields = ["method", "severity", "policy", "rule_id", "payload"]
    supported_event_types = ["waf.attack", "web.request"]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        record: dict[str, object] = {
            "devname": event.attributes["devname"],
            "srcip": event.attributes["srcip"],
            "dstip": event.attributes["dstip"],
            "url": event.attributes["url"],
            "attack_type": event.attributes["attack_type"],
        }
        optional = ["method", "severity", "policy", "rule_id", "payload"]
        for key in optional:
            if key in event.attributes:
                record[key] = event.attributes[key]
        return self._ok(format_json(event, record))
