"""Compile scenarios into runtime plans."""

from __future__ import annotations

import random
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from eventweave.compiler.pack_loader import PackRegistry
from eventweave.core.entity import Entity
from eventweave.core.event import Event
from eventweave.core.relation import Relation
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario
from eventweave.core.timeline import TimelineItem


class CompileError(Exception):
    """Raised when a scenario cannot be compiled into a runtime plan."""


class EntityGenerator:
    """Generate entity instances from a scenario definition."""

    def __init__(self, scenario: Scenario, seed: int | None = None) -> None:
        self.scenario = scenario
        self.rng = random.Random(seed)
        self._counter: dict[str, int] = {}

    def generate(self) -> list[Entity]:
        entities: list[Entity] = []
        for entity_type, template in self.scenario.entities.items():
            for _ in range(template.count):
                entity_id = self._next_id(entity_type)
                entity = Entity(
                    id=entity_id,
                    type=template.type or entity_type,
                    domain=self.scenario.domain,
                    attributes=dict(template.attributes),
                    tags=list(template.tags),
                )
                entities.append(entity)
        return entities

    def _next_id(self, entity_type: str) -> str:
        self._counter[entity_type] = self._counter.get(entity_type, 0) + 1
        idx = self._counter[entity_type]
        return f"{entity_type}_{idx:03d}"


class TimelineExpander:
    """Expand scenario-level timeline templates into concrete events."""

    def __init__(
        self,
        scenario: Scenario,
        entities: list[Entity],
        seed: int | None = None,
    ) -> None:
        self.scenario = scenario
        self.entities = entities
        self.rng = random.Random(seed)
        self.start_time = datetime.now(UTC)
        self._event_counter = 0
        self._event_index: dict[str, list[Event]] = {}

    def expand(self) -> tuple[list[Event], list[Relation]]:
        events: list[Event] = []
        relations: list[Relation] = []

        # Group entities by type for easy lookup.
        by_type: dict[str, list[Entity]] = {}
        for entity in self.entities:
            by_type.setdefault(entity.type, []).append(entity)

        # Determine the primary entity type for the timeline flow.
        primary_type = self._primary_entity_type()
        primary_entities = by_type.get(primary_type, [])

        for entity in primary_entities:
            flow_events = self._expand_flow(entity, by_type)
            events.extend(flow_events)

        # Sort events globally by event_time.
        events.sort(key=lambda e: e.event_time)
        return events, relations

    def _primary_entity_type(self) -> str:
        # Infer primary entity type from the first timeline event type,
        # e.g. order.created -> order. Each primary entity instance becomes a flow.
        if not self.scenario.timeline:
            return ""
        first = self.scenario.timeline[0]
        return first.event.split(".", 1)[0]

    def _expand_flow(
        self,
        primary_entity: Entity,
        by_type: dict[str, list[Entity]],
    ) -> list[Event]:
        flow_events: list[Event] = []
        flow_id = primary_entity.id
        current_time = self.start_time
        last_event_by_type: dict[str, Event] = {}

        for item in self.scenario.timeline:
            # Probability check.
            if self.rng.random() > item.probability:
                continue

            # Advance time.
            if item.at is not None:
                current_time = self.start_time + self._parse_duration(item.at)
            elif item.after is not None and item.delay is not None:
                base = last_event_by_type.get(item.after)
                base_time = base.event_time if base is not None else current_time
                current_time = base_time + self._parse_delay(item.delay)

            # Resolve source id.
            source_id = item.source or self._default_source_id()

            # Build entity refs.
            entity_refs = self._resolve_entity_refs(
                item, primary_entity, by_type, last_event_by_type
            )

            event = Event(
                event_id=self._next_event_id(),
                scenario_id=self.scenario.id,
                flow_id=flow_id,
                source_id=source_id,
                event_type=item.event,
                event_time=current_time,
                entity_refs=entity_refs,
                attributes=dict(item.attributes),
                labels=list(item.labels),
                ground_truth={
                    "is_key_event": True,
                    **item.ground_truth,
                },
            )
            flow_events.append(event)
            last_event_by_type[item.event] = event
            self._event_index.setdefault(item.event, []).append(event)

        return flow_events

    def _resolve_entity_refs(
        self,
        item: TimelineItem,
        primary_entity: Entity,
        by_type: dict[str, list[Entity]],
        last_event_by_type: dict[str, Event],
    ) -> dict[str, str]:
        refs: dict[str, str] = {"primary": primary_entity.id}

        # Use explicit refs from timeline item.
        for role, ref_spec in item.entity_refs.items():
            if ref_spec == "primary":
                refs[role] = primary_entity.id
            elif ref_spec in by_type:
                # Pick a random entity of the requested type.
                candidates = by_type[ref_spec]
                refs[role] = self.rng.choice(candidates).id if candidates else ""
            elif "." in ref_spec:
                # e.g. "order.created.order" -> last order.created event's ref
                parts = ref_spec.split(".")
                event_type = ".".join(parts[:-1])
                ref_role = parts[-1]
                prev = last_event_by_type.get(event_type)
                if prev and ref_role in prev.entity_refs:
                    refs[role] = prev.entity_refs[ref_role]
            else:
                refs[role] = ref_spec

        # Auto-fill refs from event schema if primary matches.
        refs.setdefault("self", primary_entity.id)
        return refs

    def _default_source_id(self) -> str:
        if self.scenario.sources:
            return self.scenario.sources[0].id
        return "default"

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"evt_{self._event_counter:06d}"

    def _parse_duration(self, value: str) -> timedelta:
        return _parse_duration(value)

    def _parse_delay(self, value: str) -> timedelta:
        if ".." in value:
            low, high = value.split("..", 1)
            low_td = _parse_duration(low)
            high_td = _parse_duration(high)
            seconds = self.rng.uniform(low_td.total_seconds(), high_td.total_seconds())
            return timedelta(seconds=seconds)
        return _parse_duration(value)


class ScenarioPlanner:
    """Top-level planner that compiles a scenario into a runtime plan."""

    def __init__(self, packs_dir: str | Path | None = None) -> None:
        self.pack_registry = PackRegistry(packs_dir)

    def compile(self, scenario: Scenario, seed: int | None = None) -> RuntimePlan:
        # Load packs for validation context (raises if packs are missing).
        self.pack_registry.load_with_dependencies(scenario.domain)

        # Generate entities.
        entity_gen = EntityGenerator(scenario, seed=seed)
        entities = entity_gen.generate()

        # Expand timeline.
        expander = TimelineExpander(scenario, entities, seed=seed)
        events, relations = expander.expand()

        # Collect sources.
        sources = list(scenario.sources)

        return RuntimePlan(
            scenario=scenario,
            entities=entities,
            relations=relations,
            events=events,
            sources=sources,
        )


_DURATION_RE = re.compile(
    r"^\s*(?:(?P<hours>\d+)h)?\s*(?:(?P<minutes>\d+)m)?\s*(?:(?P<seconds>\d+(?:\.\d+)?)s)?\s*$"
)

_HMS_RE = re.compile(r"^(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2}(?:\.\d+)?)$")


def _parse_duration(value: str) -> timedelta:
    value = value.strip()

    # HH:MM:SS format, e.g. 00:01:30
    hms_match = _HMS_RE.match(value)
    if hms_match:
        hours = float(hms_match.group("hours"))
        minutes = float(hms_match.group("minutes"))
        seconds = float(hms_match.group("seconds"))
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    # Compact format, e.g. 1h30m10s, 5m, 30s
    match = _DURATION_RE.match(value)
    if match and any(match.groupdict().values()):
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    raise CompileError(f"Invalid duration format: {value!r}")
