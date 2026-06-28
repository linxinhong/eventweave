"""Timeline template model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TimelineItem(BaseModel):
    """A single item in a scenario-level timeline template."""

    event: str = Field(..., description="Event type to emit, e.g. order.created.")
    source: str | None = Field(default=None, description="Source id or role.")
    at: str | None = Field(
        default=None,
        description="Absolute offset from scenario start, e.g. 00:01:00.",
    )
    after: str | None = Field(
        default=None,
        description="Event type that this item must follow.",
    )
    delay: str | None = Field(
        default=None,
        description="Delay range after the predecessor, e.g. 1m..5m.",
    )
    probability: float = Field(default=1.0, ge=0, le=1)
    repeat: int = Field(default=1, ge=1)
    semantic: dict[str, Any] | None = Field(default=None)
    attributes: dict[str, Any] = Field(default_factory=dict)
    entity_refs: dict[str, str] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    ground_truth: dict[str, Any] = Field(default_factory=dict)
