"""Deterministic background noise generation for compiled scenarios."""

from __future__ import annotations

import random
from datetime import timedelta

from eventweave.compiler.duration import parse_duration
from eventweave.core.entity import Entity
from eventweave.core.event import Event
from eventweave.core.noise import NoiseEventSpec
from eventweave.core.scenario import Scenario


class NoiseGenerator:
    """Generate deterministic background noise events for a scenario."""

    def __init__(
        self,
        scenario: Scenario,
        entities: list[Entity],
        seed: int | None = None,
    ) -> None:
        self.scenario = scenario
        self.entities = entities
        # Salt the RNG so noise is independent from timeline expansion.
        self.rng = random.Random((seed or 0) + 42)
        self._counter = 0
        self._by_type: dict[str, list[Entity]] = {}
        for entity in entities:
            self._by_type.setdefault(entity.type, []).append(entity)

    def generate(self, timeline_events: list[Event]) -> list[Event]:
        """Produce noise events to surround the ground-truth timeline."""
        config = self.scenario.noise
        if config is None or not config.enabled or not config.events:
            return []

        if not timeline_events:
            return []

        count = max(0, round(len(timeline_events) * config.ratio))
        if count == 0:
            return []

        weighted = _build_weighted_specs(config.events)
        source_ids = [s.id for s in self.scenario.sources] or ["default"]

        start_time = min(e.event_time for e in timeline_events)
        duration = parse_duration(self.scenario.duration)

        noise_events: list[Event] = []
        for _ in range(count):
            spec = self.rng.choice(weighted)
            source_id = spec.source or self.rng.choice(source_ids)
            event_time = start_time + timedelta(
                seconds=self.rng.uniform(0.0, duration.total_seconds())
            )

            event = Event(
                event_id=self._next_event_id(),
                scenario_id=self.scenario.id,
                flow_id=None,
                source_id=source_id,
                event_type=spec.event,
                event_time=event_time,
                entity_refs=self._resolve_refs(spec.entity_refs),
                attributes=dict(spec.attributes),
                ground_truth={"noise": True},
            )
            noise_events.append(event)

        return noise_events

    def _next_event_id(self) -> str:
        self._counter += 1
        scenario_slug = self.scenario.id.replace("_", "-")
        return f"evt-{scenario_slug}-noise-{self._counter:05d}"

    def _resolve_refs(self, refs: dict[str, str]) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for role, spec in refs.items():
            resolved[role] = self._resolve_ref(spec)
        return resolved

    def _resolve_ref(self, spec: str) -> str:
        if spec.startswith("$entity."):
            entity_type = spec.split(".", 1)[1]
            candidates = self._by_type.get(entity_type, [])
            if candidates:
                return self.rng.choice(candidates).id
            return ""
        if spec == "$flow":
            candidates = self._by_type.get(self.scenario.for_each or "", [])
            if candidates:
                return self.rng.choice(candidates).id
            return ""
        return spec


def _build_weighted_specs(specs: list[NoiseEventSpec]) -> list[NoiseEventSpec]:
    weighted: list[NoiseEventSpec] = []
    for spec in specs:
        weighted.extend([spec] * spec.weight)
    return weighted
