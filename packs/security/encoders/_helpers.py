"""Small formatting helpers for security-pack encoders."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from eventweave.core.event import Event


def event_time_str(event: Event, fmt: str = "%Y-%m-%dT%H:%M:%S.%fZ") -> str:
    """Return the event time formatted as a string."""
    return event.event_time.strftime(fmt)


def format_kv(
    event: Event,
    fields: list[tuple[str, str]],
    missing: str = "-",
) -> str:
    """Build a key-value line from ordered (key, attr) pairs.

    *fields* maps output key names to event attribute names. Boolean/numeric
    values are emitted unquoted; strings are quoted.
    """
    parts: list[str] = []
    for out_key, attr_name in fields:
        value = event.attributes.get(attr_name)
        if value is None:
            parts.append(f"{out_key}={missing}")
        elif isinstance(value, bool):
            parts.append(f"{out_key}={str(value).lower()}")
        elif isinstance(value, (int, float)):
            parts.append(f"{out_key}={value}")
        else:
            parts.append(f'{out_key}="{value}"')
    return " ".join(parts)


def format_csv(values: list[Any]) -> str:
    """Build a CSV line from values, quoting strings containing commas."""
    rendered: list[str] = []
    for value in values:
        if value is None:
            rendered.append("")
        elif isinstance(value, str) and ("," in value or '"' in value):
            escaped = value.replace('"', '""')
            rendered.append(f'"{escaped}"')
        else:
            rendered.append(str(value))
    return ",".join(rendered)


def format_tsv(values: list[Any]) -> str:
    """Build a TSV line from values, using '-' for missing values."""
    rendered: list[str] = []
    for value in values:
        if value is None:
            rendered.append("-")
        else:
            rendered.append(str(value))
    return "\t".join(rendered)


def format_json(event: Event, record: dict[str, Any]) -> str:
    """Return a JSON line mixing the record with the event time."""
    record["timestamp"] = event_time_str(event)
    return json.dumps(record, default=str, ensure_ascii=False)
