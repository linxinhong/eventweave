"""Benchmark suite and scorecard models for multi-scenario evaluation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from eventweave.evaluation.report import EvaluationReport


def _now_utc() -> datetime:
    return datetime.now(UTC)


class BenchmarkScenario(BaseModel):
    """A single scenario within a benchmark suite."""

    id: str
    scenario_path: Path
    ground_truth_path: Path | None = None
    agent_output_path: Path | None = None

    @field_validator("scenario_path", "ground_truth_path", "agent_output_path", mode="before")
    @classmethod
    def _convert_str_to_path(cls, value: Any) -> Any:
        if isinstance(value, str):
            return Path(value)
        return value


class BenchmarkSuite(BaseModel):
    """A declarative collection of scenarios used to evaluate agents."""

    id: str
    name: str | None = None
    description: str | None = None
    scenarios: list[BenchmarkScenario] = Field(default_factory=list)


class BenchmarkAgentResult(BaseModel):
    """Evaluation results for one agent across all scenarios in a suite."""

    agent_name: str
    per_scenario: dict[str, EvaluationReport] = Field(default_factory=dict)
    aggregate: dict[str, float] = Field(default_factory=dict)


class Scorecard(BaseModel):
    """Aggregated results of a benchmark suite run across one or more agents."""

    suite: BenchmarkSuite
    generated_at: datetime = Field(default_factory=_now_utc)
    results: list[BenchmarkAgentResult] = Field(default_factory=list)
    ranking: list[str] = Field(default_factory=list)
