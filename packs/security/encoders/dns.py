"""DNS JSON encoder."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import format_json


@encoder("dns-json", content_type="application/x-ndjson")
class DnsJsonEncoder(Encoder):
    """Encode events as DNS query/response JSON."""

    name = "dns-json"
    content_type = "application/x-ndjson"
    description = "DNS query/response JSON format."
    required_fields = ["client_ip", "query"]
    optional_fields = ["qtype", "rcode", "answers", "resolver", "action"]
    supported_event_types = ["network.dns"]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        record: dict[str, object] = {
            "client_ip": event.attributes["client_ip"],
            "query": event.attributes["query"],
        }
        optional = ["qtype", "rcode", "answers", "resolver", "action"]
        for key in optional:
            if key in event.attributes:
                record[key] = event.attributes[key]
        return self._ok(format_json(event, record))
