"""Load domain packs for EventWeave."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from eventweave.core.realism_profile import RealismProfile, RealismProfileBundle
from eventweave.encoders.registry import _default_registry


class PackLoadError(Exception):
    """Raised when a pack cannot be loaded or parsed."""


def _optional_path(value: str | None) -> Path | None:
    """Convert a manifest path value to a Path, treating '' as None."""
    if value is None or value == "":
        return None
    return Path(value)


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


class EncoderMetadata(BaseModel):
    """Encoder mapping declared by a pack."""

    name: str
    description: str | None = None
    required_fields: list[str] = Field(default_factory=list)
    supported_event_types: list[str] = Field(default_factory=list)


class Pack(BaseModel):
    """A domain pack containing schemas and rules."""

    id: str
    name: str | None = None
    version: str = "1.0"
    description: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    entities: dict[str, EntitySchema] = Field(default_factory=dict)
    events: dict[str, EventSchema] = Field(default_factory=dict)
    rules: list[PackRule] = Field(default_factory=list)
    realism_profiles: dict[str, RealismProfile] = Field(default_factory=dict)
    encoders: list[EncoderMetadata] = Field(default_factory=list)
    # Paths are populated by the registry; not part of pack.yaml directly.
    entities_path: Path = Field(default=Path("entities"))
    events_path: Path = Field(default=Path("events"))
    rules_path: Path = Field(default=Path("rules.yaml"))
    semantic_path: Path | None = Field(default=Path("semantic"))
    examples_path: Path | None = Field(default=Path("examples"))
    realism_path: Path | None = Field(default=Path("realism"))
    encoders_path: Path | None = Field(default=Path("encoders"))


class PackRegistry:
    """Registry of loaded domain packs."""

    def __init__(self, packs_dir: str | Path | None = None) -> None:
        if packs_dir:
            self.packs_dir = Path(packs_dir)
        else:
            self.packs_dir = Path(__file__).parent.parent.parent / "packs"
        self._packs: dict[str, Pack] = {}

    def list_packs(self) -> list[Pack]:
        """List all packs found in the packs directory.

        Only pack metadata is loaded; entities, events and rules are not.
        """
        packs: list[Pack] = []
        if not self.packs_dir.exists():
            return packs

        for path in sorted(self.packs_dir.iterdir()):
            if not path.is_dir():
                continue
            pack_file = path / "pack.yaml"
            if not pack_file.exists():
                continue
            try:
                packs.append(self._load_metadata(path))
            except PackLoadError:
                continue
        return packs

    def load_metadata(self, domain: str) -> Pack:
        """Load only pack.yaml metadata for a given domain id."""
        pack_path = self.packs_dir / domain
        if not pack_path.exists():
            raise PackLoadError(f"Pack not found: {domain} at {pack_path}")
        return self._load_metadata(pack_path)

    def _load_metadata(self, pack_path: Path) -> Pack:
        pack_file = pack_path / "pack.yaml"
        if not pack_file.exists():
            raise PackLoadError(f"Pack metadata missing: {pack_file}")

        with pack_file.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        return Pack(
            id=meta.get("id", pack_path.name),
            name=meta.get("name"),
            version=meta.get("version", "1.0"),
            description=meta.get("description"),
            depends_on=meta.get("depends_on", []),
            entities_path=Path(meta.get("entities_path", "entities")),
            events_path=Path(meta.get("events_path", "events")),
            rules_path=Path(meta.get("rules_path", "rules.yaml")),
            semantic_path=_optional_path(meta.get("semantic_path", "semantic")),
            examples_path=_optional_path(meta.get("examples_path", "examples")),
            realism_path=_optional_path(meta.get("realism_path", "realism")),
            encoders_path=_optional_path(meta.get("encoders_path", "encoders")),
            encoders=[
                EncoderMetadata.model_validate(item)
                for item in meta.get("encoders", [])
            ],
        )

    def load(self, domain: str) -> Pack:
        """Load a pack by domain id."""
        if domain in self._packs:
            return self._packs[domain]

        pack = self.load_metadata(domain)
        pack_path = self.packs_dir / domain

        pack.entities = self._load_entities(pack_path / pack.entities_path)
        pack.events = self._load_events(pack_path / pack.events_path)
        pack.rules = self._load_rules(pack_path / pack.rules_path)
        if pack.realism_path is not None:
            pack.realism_profiles = self._load_realism_profiles(
                pack_path / pack.realism_path
            )

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

    def validate_pack(self, domain: str) -> list[str]:
        """Validate a pack by id and return a list of issue messages.

        Issues prefixed with ``ERROR:`` are fatal; ``WARNING:`` are not.
        """
        issues: list[str] = []
        pack_path = self.packs_dir / domain

        if not pack_path.exists():
            return [f"ERROR: Pack directory not found: {pack_path}"]

        pack_file = pack_path / "pack.yaml"
        if not pack_file.exists():
            return [f"ERROR: Pack metadata missing: {pack_file}"]

        try:
            meta = self._load_metadata(pack_path)
        except Exception as exc:  # noqa: BLE001
            return [f"ERROR: Failed to parse pack.yaml: {exc}"]

        if not meta.name:
            issues.append("ERROR: Missing required field 'name' in pack.yaml")
        if not meta.version:
            issues.append("ERROR: Missing required field 'version' in pack.yaml")
        if meta.id != domain:
            issues.append(
                f"WARNING: Pack id '{meta.id}' does not match directory '{domain}'"
            )

        for dep in meta.depends_on:
            if not (self.packs_dir / dep / "pack.yaml").exists():
                issues.append(f"ERROR: Dependency pack not found: {dep}")

        entities_dir = pack_path / meta.entities_path
        if not entities_dir.exists() or not entities_dir.is_dir():
            issues.append(f"ERROR: Entities directory missing: {entities_dir}")

        events_dir = pack_path / meta.events_path
        if not events_dir.exists() or not events_dir.is_dir():
            issues.append(f"WARNING: Events directory missing: {events_dir}")

        rules_file = pack_path / meta.rules_path
        if not rules_file.exists():
            issues.append(f"WARNING: Rules file missing: {rules_file}")
        else:
            try:
                with rules_file.open("r", encoding="utf-8") as f:
                    rules_data = yaml.safe_load(f) or {}
                if "rules" not in rules_data:
                    issues.append("ERROR: Rules file must contain a top-level 'rules' key")
                elif not isinstance(rules_data["rules"], list):
                    issues.append("ERROR: 'rules' must be a list")
            except Exception as exc:  # noqa: BLE001
                issues.append(f"ERROR: Failed to parse rules.yaml: {exc}")

        # Load full pack to inspect schema keys and realism profiles.
        try:
            full_pack = self.load(domain)
        except Exception as exc:  # noqa: BLE001
            issues.append(f"ERROR: Failed to load pack contents: {exc}")
            return issues

        realism_path = full_pack.realism_path
        if realism_path is not None:
            realism_dir = pack_path / realism_path
            profiles_file = realism_dir / "profiles.yaml"
            if profiles_file.exists():
                try:
                    with profiles_file.open("r", encoding="utf-8") as f:
                        RealismProfileBundle.model_validate(yaml.safe_load(f) or {})
                except Exception as exc:  # noqa: BLE001
                    issues.append(f"ERROR: Invalid realism profiles: {exc}")

        for entity_type, entity_schema in full_pack.entities.items():
            if entity_schema.type != entity_type:
                issues.append(
                    f"ERROR: Entity schema type mismatch: {entity_type} != {entity_schema.type}"
                )

        for event_type, event_schema in full_pack.events.items():
            if event_schema.type != event_type:
                issues.append(
                    f"ERROR: Event schema type mismatch: {event_type} != {event_schema.type}"
                )

        # Validate encoder metadata against the global encoder registry.
        for encoder_meta in full_pack.encoders:
            if not _default_registry.has(encoder_meta.name):
                issues.append(
                    f"ERROR: Encoder '{encoder_meta.name}' declared in pack.yaml "
                    "is not registered"
                )
                continue
            for event_type in encoder_meta.supported_event_types:
                if event_type not in full_pack.events:
                    issues.append(
                        f"ERROR: Encoder '{encoder_meta.name}' references unknown "
                        f"event type '{event_type}'"
                    )

        # Validate examples compile.
        if meta.examples_path:
            examples_dir = pack_path / meta.examples_path
            if examples_dir.exists() and examples_dir.is_dir():
                for example_path in sorted(examples_dir.glob("*.yaml")):
                    try:
                        from eventweave.compiler.engine import compile_scenario_file

                        result = compile_scenario_file(example_path, packs_dir=self.packs_dir)
                        if result.errors:
                            issues.append(
                                f"ERROR: Example {example_path.name} failed to compile: "
                                + "; ".join(result.errors)
                            )
                    except Exception as exc:  # noqa: BLE001
                        issues.append(
                            f"ERROR: Example {example_path.name} failed to compile: {exc}"
                        )

        return issues

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

    def _load_realism_profiles(
        self, realism_dir: Path | None
    ) -> dict[str, RealismProfile]:
        """Load realism profiles from <realism_dir>/profiles.yaml if it exists."""
        if realism_dir is None:
            return {}

        profiles_file = realism_dir / "profiles.yaml"
        if not profiles_file.exists():
            return {}

        with profiles_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        bundle = RealismProfileBundle.model_validate(data)
        profiles = bundle.profiles
        for profile_id, profile in profiles.items():
            if profile.id is None:
                profile.id = profile_id
        return profiles
