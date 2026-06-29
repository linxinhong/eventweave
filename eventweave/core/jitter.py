"""Time jitter configuration for scenarios."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JitterConfig(BaseModel):
    """Configuration for deterministic timestamp jitter."""

    enabled: bool = Field(default=True)
    max_offset: str = Field(
        default="10s",
        description="Maximum time offset to add or subtract, e.g. 5s or 1m.",
    )
    preserve_order: bool = Field(
        default=True,
        description="Ensure events within a flow never move ahead of a predecessor.",
    )
