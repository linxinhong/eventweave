"""Duration parsing utilities for the scenario compiler."""

from __future__ import annotations

import re
from datetime import timedelta


class DurationParseError(Exception):
    """Raised when a duration string cannot be parsed."""


_DURATION_RE = re.compile(
    r"^\s*(?:(?P<hours>\d+)h)?\s*(?:(?P<minutes>\d+)m)?\s*(?:(?P<seconds>\d+(?:\.\d+)?)s)?\s*$"
)

_HMS_RE = re.compile(r"^(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2}(?:\.\d+)?)$")


def parse_duration(value: str) -> timedelta:
    """Parse a duration string into a timedelta.

    Supports ``HH:MM:SS`` and compact forms such as ``1h30m10s``, ``5m``, ``30s``.
    """
    value = value.strip()

    hms_match = _HMS_RE.match(value)
    if hms_match:
        hours = float(hms_match.group("hours"))
        minutes = float(hms_match.group("minutes"))
        seconds = float(hms_match.group("seconds"))
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    match = _DURATION_RE.match(value)
    if match and any(match.groupdict().values()):
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    raise DurationParseError(f"Invalid duration format: {value!r}")
