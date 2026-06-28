"""Ground truth model for agent evaluation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExpectedFinding(BaseModel):
    """An expected finding for agent evaluation."""

    model_config = ConfigDict(populate_by_name=True)

    type: str
    entities: list[str] = Field(default_factory=list)
    stage: str | None = None
    evidence_event_ids: list[str] = Field(
        default_factory=list,
        alias="evidence_events",
    )
    attributes: dict[str, Any] = Field(default_factory=dict)


class GroundTruth(BaseModel):
    """Lightweight ground truth for a scenario."""

    scenario_id: str
    expected_findings: list[ExpectedFinding] = Field(default_factory=list)
    expected_summary: str | None = None
    key_event_ids: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
