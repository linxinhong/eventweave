"""File sink that appends events to a JSONL file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from eventweave.core.event import Event
from eventweave.runtime.sink import Sink


def _resolve_within_output_dir(target: Path, output_dir: Path) -> Path:
    """Resolve *target* against *output_dir* and ensure it stays within it."""
    base = output_dir.expanduser().resolve()
    resolved = target.resolve() if target.is_absolute() else (base / target).resolve()

    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(
            f"file sink path {target} escapes output directory {output_dir}"
        ) from exc

    return resolved


class FileSink(Sink):
    """Append events to a JSONL file within a constrained output directory."""

    def __init__(
        self,
        path: str | Path,
        output_dir: str | Path,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.path = _resolve_within_output_dir(Path(path), self.output_dir)
        self._count = 0
        self._file: TextIO | None = None

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8")

    def write(self, event: Event) -> None:
        if self._file is None:
            raise RuntimeError("FileSink is not open")
        self._file.write(json.dumps(event.model_dump(), default=str, ensure_ascii=False) + "\n")
        self._count += 1

    def flush(self) -> None:
        if self._file is not None:
            self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def count(self) -> int:
        return self._count
