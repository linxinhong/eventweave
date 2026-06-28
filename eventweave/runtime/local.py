"""Local runtime that replays an event plan through a sink."""

from __future__ import annotations

import json
from pathlib import Path

from eventweave.core.event import Event
from eventweave.runtime.clock import RuntimeClock
from eventweave.runtime.scheduler import sort_events
from eventweave.runtime.sink import Sink
from eventweave.runtime.sinks.stdout import StdoutSink
from eventweave.runtime.stats import RuntimeStats


class LocalRuntime:
    """Replay a compiled event plan through a sink."""

    def __init__(
        self,
        plan_dir: str | Path,
        sink: Sink | None = None,
        speed: float = 1.0,
        no_wait: bool = False,
        limit: int | None = None,
    ) -> None:
        self.plan_dir = Path(plan_dir)
        self.sink = sink or StdoutSink()
        self.speed = speed
        self.no_wait = no_wait
        self.limit = limit
        self.stats = RuntimeStats()

    def _load_events(self) -> list[Event]:
        path = self.plan_dir / "event_plan.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Event plan not found: {path}")
        events: list[Event] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(Event.model_validate(json.loads(line)))
        return events

    def _count_unresolved_refs(self, events: list[Event]) -> int:
        count = 0
        for event in events:
            if any(ref.startswith("semantic://") for ref in event.semantic_refs):
                count += 1
        return count

    def run(self) -> RuntimeStats:
        """Run the local runtime and return statistics."""
        events = sort_events(self._load_events())
        if self.limit is not None:
            events = events[: self.limit]
        if not events:
            self.stats.finish()
            return self.stats

        self.stats.unresolved_refs = self._count_unresolved_refs(events)
        clock = RuntimeClock(
            start_time=events[0].event_time,
            speed=self.speed,
            no_wait=self.no_wait,
        )

        self.sink.open()
        try:
            for event in events:
                clock.wait_until(event.event_time)
                self.sink.write(event)
                self.stats.emitted += 1
            self.sink.flush()
        finally:
            self.sink.close()

        self.stats.failed = self.sink.failed()
        self.stats.finish()
        return self.stats
