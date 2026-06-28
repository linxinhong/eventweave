"""File sink that appends events to a JSONL file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from eventweave.core.event import Event
from eventweave.runtime.sink import Sink


class FileSink(Sink):
    """Append events to a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
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
