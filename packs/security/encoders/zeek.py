"""Zeek conn.log and dns.log encoders."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder
from packs.security.encoders._helpers import event_time_str, format_tsv


@encoder("zeek-conn", content_type="text/plain")
class ZeekConnEncoder(Encoder):
    """Encode events as Zeek conn.log TSV records."""

    name = "zeek-conn"
    content_type = "text/plain"
    description = "Zeek conn.log TSV network connection format."
    required_fields = ["uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "proto"]
    optional_fields = [
        "service",
        "duration",
        "orig_bytes",
        "resp_bytes",
        "conn_state",
    ]
    supported_event_types = ["network.connection"]
    _columns = [
        "ts",
        "uid",
        "id.orig_h",
        "id.orig_p",
        "id.resp_h",
        "id.resp_p",
        "proto",
        "service",
        "duration",
        "orig_bytes",
        "resp_bytes",
        "conn_state",
    ]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        values: list[object] = [event_time_str(event)]
        for col in self._columns[1:]:
            values.append(event.attributes.get(col))
        return self._ok(format_tsv(values))


@encoder("zeek-dns", content_type="text/plain")
class ZeekDNSEncoder(Encoder):
    """Encode events as Zeek dns.log TSV records."""

    name = "zeek-dns"
    content_type = "text/plain"
    description = "Zeek dns.log TSV DNS query/response format."
    required_fields = ["uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "query"]
    optional_fields = [
        "proto",
        "trans_id",
        "qtype_name",
        "rcode_name",
        "answers",
    ]
    supported_event_types = ["network.dns"]
    _columns = [
        "ts",
        "uid",
        "id.orig_h",
        "id.orig_p",
        "id.resp_h",
        "id.resp_p",
        "proto",
        "trans_id",
        "query",
        "qtype_name",
        "rcode_name",
        "answers",
    ]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        values: list[object] = [event_time_str(event)]
        for col in self._columns[1:]:
            value = event.attributes.get(col)
            if col == "answers" and isinstance(value, list):
                value = ",".join(str(v) for v in value)
            values.append(value)
        return self._ok(format_tsv(values))
