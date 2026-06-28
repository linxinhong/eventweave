"""Agent output schema for evaluation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentFinding(BaseModel):
    """A single finding reported by an agent."""

    type: str
    entities: list[str] = Field(default_factory=list)
    stage: str | None = None
    evidence_event_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)


class AgentTimelineStage(BaseModel):
    """A timeline stage reconstructed by an agent."""

    stage: str
    event_ids: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """Expected output format for an evaluated agent."""

    scenario_id: str
    findings: list[AgentFinding] = Field(default_factory=list)
    key_event_ids: list[str] = Field(default_factory=list)
    timeline_stages: list[AgentTimelineStage] = Field(default_factory=list)
    summary: str | None = None
