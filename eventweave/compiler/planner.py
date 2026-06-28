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

    def new_entity(self, entity_type: str, domain: str) -> Entity:
        """Create an additional entity on demand during timeline expansion."""
        entity_id = self._next_id(entity_type)
        return Entity(
            id=entity_id,
            type=entity_type,
            domain=domain,
        )

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
        self.warnings: list[str] = []
        self._entity_gen = EntityGenerator(scenario, seed=seed)

    def expand(self) -> tuple[list[Event], list[Relation], list[str]]:
        events: list[Event] = []
        relations: list[Relation] = []

        # Group entities by type for easy lookup.
        by_type: dict[str, list[Entity]] = {}
        for entity in self.entities:
            by_type.setdefault(entity.type, []).append(entity)

        # Determine the primary entity type for the timeline flow.
        primary_type = self._primary_entity_type()
        primary_entities = by_type.get(primary_type, [])

        for flow_index, entity in enumerate(primary_entities, start=1):
            flow_events = self._expand_flow(
                flow_index=flow_index,
                primary_entity=entity,
                by_type=by_type,
            )
            events.extend(flow_events)

        # Stable global sort: event_time, then deterministic event_id.
        events.sort(key=lambda e: (e.event_time, e.event_id))
        return events, relations, self.warnings

    def _primary_entity_type(self) -> str:
        if self.scenario.for_each:
            return self.scenario.for_each

        if not self.scenario.timeline:
            return ""

        # Fallback: infer from the first timeline event type.
        first = self.scenario.timeline[0]
        inferred = first.event.split(".", 1)[0]
        self.warnings.append(
            f"for_each is not set; inferred primary entity {inferred!r} "
            f"from first event_type {first.event!r}"
        )
        return inferred

    def _expand_flow(
        self,
        flow_index: int,
        primary_entity: Entity,
        by_type: dict[str, list[Entity]],
    ) -> list[Event]:
        flow_events: list[Event] = []
        flow_id = primary_entity.id
        current_time = self.start_time

        # Track previous events by step id (preferred) and event type (fallback).
        last_event_by_id: dict[str, Event] = {}
        last_event_by_type: dict[str, Event] = {}

        # Flow-local entities created on demand via $new.<type>.
        flow_entities: dict[str, Entity] = {"flow": primary_entity}

        for step_index, item in enumerate(self.scenario.timeline, start=1):
            # Probability check.
            if self.rng.random() > item.probability:
                continue

            step_id = item.id or item.event

            # Advance time.
            if item.at is not None:
                current_time = self.start_time + self._parse_duration(item.at)
            elif item.after is not None and item.delay is not None:
                base = last_event_by_id.get(item.after) or last_event_by_type.get(item.after)
                base_time = base.event_time if base is not None else current_time
                current_time = base_time + self._parse_delay(item.delay)

            # Resolve source id.
            source_id = item.source or self._default_source_id()

            # Build entity refs.
            entity_refs = self._resolve_entity_refs(
                item=item,
                primary_entity=primary_entity,
                by_type=by_type,
                flow_entities=flow_entities,
                last_event_by_id=last_event_by_id,
            )

            event = Event(
                event_id=self._next_event_id(flow_index, step_index),
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
            last_event_by_id[step_id] = event
            last_event_by_type[item.event] = event

        return flow_events

    def _resolve_entity_refs(
        self,
        item: TimelineItem,
        primary_entity: Entity,
        by_type: dict[str, list[Entity]],
        flow_entities: dict[str, Entity],
        last_event_by_id: dict[str, Event],
    ) -> dict[str, str]:
        refs: dict[str, str] = {"flow": primary_entity.id}

        for role, ref_spec in item.entity_refs.items():
            refs[role] = self._resolve_ref(
                ref_spec=ref_spec,
                primary_entity=primary_entity,
                by_type=by_type,
                flow_entities=flow_entities,
                last_event_by_id=last_event_by_id,
            )

        return refs

    def _resolve_ref(
        self,
        ref_spec: str,
        primary_entity: Entity,
        by_type: dict[str, list[Entity]],
        flow_entities: dict[str, Entity],
        last_event_by_id: dict[str, Event],
    ) -> str:
        # $flow -> current flow primary entity.
        if ref_spec == "$flow":
            return primary_entity.id

        # $entity.<type> -> pick a random entity from the scenario pool.
        if ref_spec.startswith("$entity."):
            entity_type = ref_spec.split(".", 1)[1]
            candidates = by_type.get(entity_type, [])
            if candidates:
                return self.rng.choice(candidates).id
            self.warnings.append(f"No entity of type {entity_type!r} available for $entity ref")
            return ""

        # $new.<type> -> create a new entity for this flow.
        if ref_spec.startswith("$new."):
            entity_type = ref_spec.split(".", 1)[1]
            entity = self._entity_gen.new_entity(entity_type, self.scenario.domain)
            self.entities.append(entity)
            by_type.setdefault(entity_type, []).append(entity)
            flow_entities[entity_type] = entity
            return entity.id

        # $ref.<step_id>.<role> -> reference a previous step's entity ref.
        if ref_spec.startswith("$ref."):
            parts = ref_spec.split(".")
            if len(parts) >= 3:
                step_id = ".".join(parts[1:-1])
                ref_role = parts[-1]
                prev = last_event_by_id.get(step_id)
                if prev and ref_role in prev.entity_refs:
                    return prev.entity_refs[ref_role]
            self.warnings.append(f"Could not resolve ref spec {ref_spec!r}")
            return ""

        # Plain entity type -> random entity of that type (legacy fallback).
        if ref_spec in by_type:
            candidates = by_type[ref_spec]
            return self.rng.choice(candidates).id if candidates else ""

        # Literal id.
        return ref_spec

    def _default_source_id(self) -> str:
        if self.scenario.sources:
            return self.scenario.sources[0].id
        return "default"

    def _next_event_id(self, flow_index: int, step_index: int) -> str:
        scenario_slug = self.scenario.id.replace("_", "-")
        return f"evt-{scenario_slug}-{flow_index:03d}-{step_index:03d}"

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

    def compile(
        self,
        scenario: Scenario,
        seed: int | None = None,
    ) -> tuple[RuntimePlan, list[str]]:
        # Load packs for validation context (raises if packs are missing).
        self.pack_registry.load_with_dependencies(scenario.domain)

        # Generate entities.
        entity_gen = EntityGenerator(scenario, seed=seed)
        entities = entity_gen.generate()

        # Expand timeline.
        expander = TimelineExpander(scenario, entities, seed=seed)
        events, relations, warnings = expander.expand()

        # Collect sources.
        sources = list(scenario.sources)

        plan = RuntimePlan(
            scenario=scenario,
            entities=entities,
            relations=relations,
            events=events,
            sources=sources,
        )
        return plan, warnings


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
