"""Evaluation report models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityEventResult(BaseModel):
    """Recall and precision for a matched finding's entity or event set."""

    recall: float = 0.0
    precision: float = 0.0


class FindingResult(BaseModel):
    """Per-finding evaluation result."""

    expected_type: str
    expected_stage: str | None = None
    matched: bool = False
    matched_type: str | None = None
    matched_stage: str | None = None
    entity_recall: float = 0.0
    event_recall: float = 0.0


class MatchedFinding(BaseModel):
    """A successfully matched expected/agent finding pair."""

    expected_type: str
    expected_stage: str | None = None
    matched_type: str
    matched_stage: str | None = None
    entity: EntityEventResult
    event: EntityEventResult


class MissedFinding(BaseModel):
    """An expected finding that the agent did not report."""

    expected_type: str
    expected_stage: str | None = None


class ExtraFinding(BaseModel):
    """An agent finding that does not match any expected finding."""

    matched_type: str
    matched_stage: str | None = None


class EvaluationReport(BaseModel):
    """Deterministic evaluation report for an agent run."""

    scenario_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    finding_results: list[FindingResult] = Field(default_factory=list)
    matched_findings: list[MatchedFinding] = Field(default_factory=list)
    missed_findings: list[MissedFinding] = Field(default_factory=list)
    extra_findings: list[ExtraFinding] = Field(default_factory=list)
    summary: str = ""
