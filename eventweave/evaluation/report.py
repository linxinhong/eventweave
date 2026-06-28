"""Evaluation report models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FindingResult(BaseModel):
    """Per-finding evaluation result."""

    expected_type: str
    expected_stage: str | None = None
    matched: bool = False
    matched_type: str | None = None
    matched_stage: str | None = None
    entity_recall: float = 0.0
    event_recall: float = 0.0


class EvaluationReport(BaseModel):
    """Deterministic evaluation report for an agent run."""

    scenario_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    finding_results: list[FindingResult] = Field(default_factory=list)
    summary: str = ""
