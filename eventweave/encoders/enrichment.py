"""Encoder field enrichment / auto-fill profiles.

Enrichment creates a temporary encoder-friendly view of a canonical event
without mutating the original event. It is applied immediately before
encoding.

Priority:
1. Existing target attribute on the event.
2. Mapped source attribute (if target is missing and source exists).
3. Default value (if target is still missing).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from eventweave.core.event import Event


class EnrichmentProfile(BaseModel):
    """Describes how to enrich canonical events for one encoder."""

    encoder: str = Field(..., description="Encoder name this profile applies to.")
    defaults: dict[str, Any] = Field(
        default_factory=dict,
        description="Default values applied when a field is missing.",
    )
    mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Target field -> source field mappings.",
    )
    description: str | None = Field(
        default=None, description="Human-readable profile description."
    )


class EnrichmentRegistry:
    """Loads and caches enrichment profiles from packs."""

    def __init__(self, packs_dir: str | Path | None = None) -> None:
        self._profiles: dict[str, EnrichmentProfile] | None = None
        if packs_dir is None:
            self.packs_dir = Path(__file__).parent.parent.parent / "packs"
        else:
            self.packs_dir = Path(packs_dir)

    def get(self, encoder_name: str) -> EnrichmentProfile | None:
        """Return the enrichment profile for *encoder_name*, if any."""
        if self._profiles is None:
            self._profiles = self._load_profiles()
        return self._profiles.get(encoder_name)

    def list_profiles(self) -> list[str]:
        """Return all encoder names with enrichment profiles."""
        if self._profiles is None:
            self._profiles = self._load_profiles()
        return sorted(self._profiles.keys())

    def _load_profiles(self) -> dict[str, EnrichmentProfile]:
        profiles: dict[str, EnrichmentProfile] = {}
        if not self.packs_dir.exists():
            return profiles

        for pack_path in sorted(self.packs_dir.iterdir()):
            if not pack_path.is_dir():
                continue
            enrichment_file = pack_path / "encoders" / "enrichment.yaml"
            if not enrichment_file.exists():
                continue
            loaded = self._load_file(enrichment_file)
            if loaded is None:
                continue
            for profile in loaded:
                profiles[profile.encoder] = profile
        return profiles

    def _load_file(self, path: Path) -> list[EnrichmentProfile] | None:
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        profiles: list[EnrichmentProfile] = []
        for encoder_name, raw in data.get("profiles", {}).items():
            profile = EnrichmentProfile(
                encoder=encoder_name,
                defaults=raw.get("defaults", {}),
                mappings=raw.get("mappings", {}),
                description=raw.get("description"),
            )
            profiles.append(profile)
        return profiles


def enrich_event(event: Event, profile: EnrichmentProfile) -> Event:
    """Return a new event with enrichment applied.

    The original *event* is not modified.
    """
    new_attributes = dict(event.attributes)

    # Apply mappings: copy from source field to target field only when target
    # is missing and source exists.
    for target, source in profile.mappings.items():
        if target not in new_attributes and source in new_attributes:
            new_attributes[target] = copy.deepcopy(new_attributes[source])

    # Apply defaults only for still-missing target fields.
    for target, value in profile.defaults.items():
        if target not in new_attributes:
            new_attributes[target] = copy.deepcopy(value)

    return event.model_copy(update={"attributes": new_attributes})


# Global default registry.
_default_registry: EnrichmentRegistry = EnrichmentRegistry()


def get_enrichment_profile(encoder_name: str) -> EnrichmentProfile | None:
    """Look up the default enrichment profile for an encoder."""
    return _default_registry.get(encoder_name)


def list_enrichment_profiles() -> list[str]:
    """List all encoder names with enrichment profiles."""
    return _default_registry.list_profiles()
