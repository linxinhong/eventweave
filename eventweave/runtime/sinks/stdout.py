"""Stdout sink that prints events as JSON lines."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from eventweave.runtime.sink import Sink


class StdoutSink(Sink):
    """Print each event to stdout as JSON."""

    def __init__(self) -> None:
        self._count = 0

    def open(self) -> None:
        pass

    def write(self, event: Event) -> None:
        print(json.dumps(event.model_dump(), default=str, ensure_ascii=False))
        self._count += 1

    def close(self) -> None:
        pass

    def flush(self) -> None:
        pass

    def count(self) -> int:
        return self._count
