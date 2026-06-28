"""JSONL exporter for event streams."""

from __future__ import annotations

import json
from pathlib import Path

from eventweave.core.event import Event


class JsonlExporter:
    """Export canonical events as newline-delimited JSON."""

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)

    def export(self, events: list[Event]) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event.model_dump(), default=str, ensure_ascii=False) + "\n")
        return self.output_path


def export_events(events: list[Event], output_path: str | Path) -> Path:
    """Convenience function to export events to JSONL."""
    return JsonlExporter(output_path).export(events)
