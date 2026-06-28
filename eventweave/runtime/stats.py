"""Runtime statistics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RuntimeStats:
    """Summary of a local runtime execution."""

    emitted: int = 0
    failed: int = 0
    unresolved_refs: int = 0
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None

    def finish(self) -> None:
        """Mark the runtime as finished."""
        self.end_time = time.monotonic()

    @property
    def duration(self) -> float:
        """Return elapsed real time in seconds."""
        end = self.end_time if self.end_time is not None else time.monotonic()
        return end - self.start_time

    def summary(self) -> dict[str, object]:
        """Return a JSON-serializable summary."""
        return {
            "events_emitted": self.emitted,
            "events_failed": self.failed,
            "duration_seconds": round(self.duration, 3),
            "unresolved_semantic_refs": self.unresolved_refs,
        }
