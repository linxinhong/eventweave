"""Suricata EVE JSON encoder."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from eventweave.encoders.base import Encoder, EncodeResult
from eventweave.encoders.registry import encoder


@encoder("suricata-eve", content_type="application/x-ndjson")
class SuricataEveEncoder(Encoder):
    """Encode an event as Suricata EVE JSON."""

    name = "suricata-eve"
    content_type = "application/x-ndjson"
    description = "Suricata EVE JSON alert and network event format."
    required_fields = ["event_type", "src_ip", "dest_ip"]
    optional_fields = [
        "src_port",
        "dest_port",
        "proto",
        "alert",
        "http",
        "dns",
        "flow_id",
        "in_iface",
        "vlan",
    ]
    supported_event_types = ["network.connection", "network.dns", "ids.alert", "web.request"]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        record: dict[str, object] = {
            "timestamp": event.event_time.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "event_type": event.attributes["event_type"],
            "src_ip": event.attributes["src_ip"],
            "dest_ip": event.attributes["dest_ip"],
        }
        optional = [
            "src_port",
            "dest_port",
            "proto",
            "alert",
            "http",
            "dns",
            "flow_id",
            "in_iface",
            "vlan",
        ]
        for key in optional:
            if key in event.attributes:
                record[key] = event.attributes[key]

        # Pull in any extra attributes that are not already covered.
        for key, value in event.attributes.items():
            if key not in record and key not in optional:
                record[key] = value

        return self._ok(json.dumps(record, default=str, ensure_ascii=False))
