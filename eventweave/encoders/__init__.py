"""Vendor/log encoders for EventWeave."""

from __future__ import annotations

from eventweave.encoders.base import EncodeError, Encoder, EncodeResult
from eventweave.encoders.jsonl import JsonlEncoder
from eventweave.encoders.nginx import NginxAccessEncoder
from eventweave.encoders.registry import encoder, get_encoder, list_encoders
from eventweave.encoders.syslog import Rfc3164Encoder, Rfc5424Encoder

__all__ = [
    "Encoder",
    "EncodeError",
    "EncodeResult",
    "encoder",
    "get_encoder",
    "list_encoders",
    "JsonlEncoder",
    "Rfc3164Encoder",
    "Rfc5424Encoder",
    "NginxAccessEncoder",
]
