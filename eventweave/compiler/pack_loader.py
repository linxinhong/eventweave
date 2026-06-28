"""Load domain packs for EventWeave."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PackLoadError(Exception):
    """Raised when a pack cannot be loaded or parsed."""


class FieldSchema(BaseModel):
    """Schema for a single field in an entity or event."""

    type: str | None = None
    format: str | None = None
    enum: list[Any] | None = None
    default: Any = None
    description: str | None = None
    required: bool = True


class EntitySchema(BaseModel):
    """Schema definition for an entity type."""

    type: str
    fields: dict[str, FieldSchema] = Field(default_factory=dict)
    refs: dict[str, str] = Field(default_factory=dict)
    description: str | None = None


class EventSchema(BaseModel):
    """Schema definition for an event type."""

    type: str
    fields: dict[str, FieldSchema] = Field(default_factory=dict)
    entity_refs: dict[str, str] = Field(default_factory=dict)
    description: str | None = None


class PackRule(BaseModel):
    """A declarative rule defined by a pack."""

    id: str
    type: str
    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Pack(BaseModel):
    """A domain pack containing schemas and rules."""

    id: str
    name: str | None = None
    version: str = "1.0"
    depends_on: list[str] = Field(default_factory=list)
    entities: dict[str, EntitySchema] = Field(default_factory=dict)
    events: dict[str, EventSchema] = Field(default_factory=dict)
    rules: list[PackRule] = Field(default_factory=list)


class PackRegistry:
    """Registry of loaded domain packs."""

    def __init__(self, packs_dir: str | Path | None = None) -> None:
        if packs_dir:
            self.packs_dir = Path(packs_dir)
        else:
            self.packs_dir = Path(__file__).parent.parent.parent / "packs"
        self._packs: dict[str, Pack] = {}

    def load(self, domain: str) -> Pack:
        """Load a pack by domain id."""
        if domain in self._packs:
            return self._packs[domain]

        pack_path = self.packs_dir / domain
        if not pack_path.exists():
            raise PackLoadError(f"Pack not found: {domain} at {pack_path}")

        pack_file = pack_path / "pack.yaml"
        if not pack_file.exists():
            raise PackLoadError(f"Pack metadata missing: {pack_file}")

        with pack_file.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        pack = Pack(
            id=meta.get("id", domain),
            name=meta.get("name"),
            version=meta.get("version", "1.0"),
            depends_on=meta.get("depends_on", []),
        )

        pack.entities = self._load_entities(pack_path / "entities")
        pack.events = self._load_events(pack_path / "events")
        pack.rules = self._load_rules(pack_path / "rules.yaml")

        self._packs[domain] = pack
        return pack

    def load_with_dependencies(self, domain: str) -> dict[str, Pack]:
        """Load a pack and all its transitive dependencies."""
        result: dict[str, Pack] = {}
        stack = [domain]
        visited: set[str] = set()

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            pack = self.load(current)
            result[current] = pack
            for dep in pack.depends_on:
                if dep not in visited:
                    stack.append(dep)

        return result

    def _load_entities(self, entities_dir: Path) -> dict[str, EntitySchema]:
        entities: dict[str, EntitySchema] = {}
        if not entities_dir.exists():
            return entities

        for file_path in sorted(entities_dir.glob("*.yaml")):
            with file_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for entity_type, schema_data in data.items():
                entities[entity_type] = EntitySchema.model_validate(
                    {"type": entity_type, **schema_data}
                )
        return entities

    def _load_events(self, events_dir: Path) -> dict[str, EventSchema]:
        events: dict[str, EventSchema] = {}
        if not events_dir.exists():
            return events

        for file_path in sorted(events_dir.glob("*.yaml")):
            with file_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for event_type, schema_data in data.items():
                events[event_type] = EventSchema.model_validate(
                    {"type": event_type, **schema_data}
                )
        return events

    def _load_rules(self, rules_file: Path) -> list[PackRule]:
        if not rules_file.exists():
            return []

        with rules_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        rules_data = data.get("rules", [])
        return [PackRule.model_validate(rule) for rule in rules_data]
