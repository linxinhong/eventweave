"""Canonical JSONL encoder."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from eventweave.encoders.base import Encoder, EncodeResult
from eventweave.encoders.registry import encoder


@encoder("jsonl", content_type="application/x-ndjson")
class JsonlEncoder(Encoder):
    """Encode an event as a single line of JSON."""

    name = "jsonl"
    content_type = "application/x-ndjson"
    description = "Canonical EventWeave JSON Lines encoder."

    def encode(self, event: Event) -> EncodeResult:
        return EncodeResult(
            success=True,
            output=json.dumps(event.model_dump(), default=str, ensure_ascii=False),
        )
