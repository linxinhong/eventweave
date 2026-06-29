"""Stdout sink that prints events as JSON lines."""

from __future__ import annotations

import json

from eventweave.core.event import Event
from eventweave.encoders.base import Encoder
from eventweave.runtime.sink import Sink


class StdoutSink(Sink):
    """Print each event to stdout as JSON or via an encoder."""

    def __init__(self, encoder: Encoder | None = None) -> None:
        self.encoder = encoder
        self._count = 0
        self._failed = 0

    def open(self) -> None:
        pass

    def write(self, event: Event) -> None:
        if self.encoder is not None:
            result = self.encoder.encode(event)
            if not result.success:
                self._failed += 1
                raise RuntimeError(f"encode failed: {result.error_reason}")
            print(result.output)
        else:
            print(json.dumps(event.model_dump(), default=str, ensure_ascii=False))
        self._count += 1

    def close(self) -> None:
        pass

    def flush(self) -> None:
        pass

    def count(self) -> int:
        return self._count

    def failed(self) -> int:
        return self._failed
