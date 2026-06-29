"""Windows Event Log JSON encoder."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from eventweave.encoders.base import Encoder, EncodeResult
from eventweave.encoders.registry import encoder


@encoder("windows-event-json", content_type="application/x-ndjson")
class WindowsEventJsonEncoder(Encoder):
    """Encode an event as a Windows Event Log JSON record."""

    name = "windows-event-json"
    content_type = "application/x-ndjson"
    description = "Windows Event Log JSON record format."
    required_fields = ["EventID"]
    optional_fields = [
        "ProviderName",
        "ProviderGuid",
        "Version",
        "Level",
        "Task",
        "Opcode",
        "Keywords",
        "EventRecordID",
        "Computer",
        "Channel",
    ]
    supported_event_types = ["windows.event"]

    def encode(self, event: Event) -> EncodeResult:
        missing = [f for f in self.required_fields if f not in event.attributes]
        if missing:
            return self._fail(f"missing required fields: {', '.join(missing)}")

        system: dict[str, object] = {
            "Provider": {
                "Name": event.attributes.get("ProviderName", event.source_id),
                "Guid": event.attributes.get("ProviderGuid", ""),
            },
            "EventID": event.attributes["EventID"],
            "Version": event.attributes.get("Version", 0),
            "Level": event.attributes.get("Level", 0),
            "Task": event.attributes.get("Task", 0),
            "Opcode": event.attributes.get("Opcode", 0),
            "Keywords": event.attributes.get("Keywords", "0x0"),
            "TimeCreated": {
                "SystemTime": event.event_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            },
            "EventRecordID": event.attributes.get("EventRecordID", event.event_id),
            "Computer": event.attributes.get("Computer", event.source_id),
            "Channel": event.attributes.get("Channel", "Security"),
        }

        record: dict[str, object] = {"Event": {"System": system}}

        event_data: dict[str, object] = {}
        for key, value in event.attributes.items():
            if key not in {
                "EventID",
                "Version",
                "Level",
                "Task",
                "Opcode",
                "Keywords",
                "EventRecordID",
                "Computer",
                "Channel",
                "ProviderName",
                "ProviderGuid",
            }:
                event_data[key] = value

        if event_data:
            record["Event"]["EventData"] = event_data

        return self._ok(json.dumps(record, default=str, ensure_ascii=False))
