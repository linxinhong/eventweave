"""Null sink that counts events without writing them."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.runtime.sink import Sink


class NullSink(Sink):
    """Count events without emitting them. Useful for dry-runs and tests."""

    def __init__(self) -> None:
        self._count = 0

    def open(self) -> None:
        pass

    def write(self, event: Event) -> None:
        self._count += 1

    def close(self) -> None:
        pass

    def flush(self) -> None:
        pass

    def count(self) -> int:
        return self._count
