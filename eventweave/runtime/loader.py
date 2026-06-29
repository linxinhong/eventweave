"""Streaming loaders for compiled runtime plan artifacts."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from eventweave.core.event import Event


def iter_event_plan(path: str | Path) -> Iterator[Event]:
    """Yield events from a JSONL event plan file without loading all into memory.

    This is intended for large event plans where holding the entire list would
    be prohibitive. Callers that need sorted events must still collect and sort
    the output.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Event plan not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield Event.model_validate(json.loads(line))
