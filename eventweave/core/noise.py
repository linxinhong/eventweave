"""Background noise configuration for scenarios."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NoiseEventSpec(BaseModel):
    """A single noise event template."""

    event: str = Field(..., description="Event type for noise events.")
    weight: int = Field(default=1, ge=1, description="Relative selection weight.")
    source: str | None = Field(
        default=None, description="Source id; falls back to a scenario source."
    )
    attributes: dict[str, Any] = Field(default_factory=dict)
    entity_refs: dict[str, str] = Field(default_factory=dict)


class NoiseConfig(BaseModel):
    """Configuration for deterministic background noise generation."""

    enabled: bool = Field(default=True)
    ratio: float = Field(default=1.0, ge=0, description="Noise events per timeline event.")
    events: list[NoiseEventSpec] = Field(default_factory=list)
