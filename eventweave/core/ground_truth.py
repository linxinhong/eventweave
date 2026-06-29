"""Ground truth model for agent evaluation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ExpectedTimelineStage(BaseModel):
    """An expected timeline stage with the event ids that support it."""

    stage: str
    event_ids: list[str] = Field(default_factory=list)


class GroundTruth(BaseModel):
    """Lightweight ground truth for a scenario."""

    scenario_id: str
    expected_findings: list[ExpectedFinding] = Field(default_factory=list)
    expected_timeline_stages: list[ExpectedTimelineStage] = Field(default_factory=list)
    expected_summary: str | None = None
    key_event_ids: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _derive_timeline_stages(self) -> GroundTruth:
        """Derive expected timeline stages from expected findings when not provided."""
        if self.expected_timeline_stages:
            return self

        stage_events: dict[str, set[str]] = {}
        for finding in self.expected_findings:
            if finding.stage is None:
                continue
            stage_events.setdefault(finding.stage, set()).update(finding.evidence_event_ids)

        self.expected_timeline_stages = [
            ExpectedTimelineStage(stage=stage, event_ids=sorted(event_ids))
            for stage, event_ids in sorted(stage_events.items())
        ]
        return self
