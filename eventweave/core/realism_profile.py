"""Pack-level realism profile models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from eventweave.core.jitter import JitterConfig
from eventweave.core.noise import NoiseConfig


class RealismProfile(BaseModel):
    """A reusable noise / jitter template owned by a domain pack."""

    id: str | None = Field(
        default=None,
        description="Profile identifier. If omitted, inferred from the YAML key.",
    )
    description: str | None = Field(
        default=None, description="Human-readable description of the profile."
    )
    noise: NoiseConfig | None = Field(
        default=None, description="Background noise configuration."
    )
    jitter: JitterConfig | None = Field(
        default=None, description="Timestamp jitter configuration."
    )


class RealismProfileBundle(BaseModel):
    """Container for all realism profiles defined in a single pack."""

    profiles: dict[str, RealismProfile] = Field(
        default_factory=dict,
        description="Map of profile id -> RealismProfile.",
    )
