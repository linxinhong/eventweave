"""Domain-agnostic event model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """A canonical event produced by EventWeave."""

    event_id: str = Field(..., description="Unique event identifier.")
    scenario_id: str = Field(..., description="Scenario this event belongs to.")
    flow_id: str | None = Field(
        default=None,
        description="Flow instance id, e.g. order_id or incident_id.",
    )
    source_id: str = Field(..., description="Source that emits the event.")
    event_type: str = Field(..., description="Event type, e.g. order.created.")
    event_time: datetime = Field(..., description="When the event occurred in scenario time.")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    emit_time: datetime | None = Field(
        default=None,
        description="When the runtime emits the event.",
    )
    ingest_time: datetime | None = Field(
        default=None,
        description="When the downstream system receives the event.",
    )
    entity_refs: dict[str, str] = Field(
        default_factory=dict,
        description="Map of role -> entity id referenced by this event.",
    )
    attributes: dict[str, Any] = Field(default_factory=dict)
    semantic_refs: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    ground_truth: dict[str, Any] = Field(default_factory=dict)
