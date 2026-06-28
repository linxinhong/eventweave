"""Benchmark runner for multi-scenario agent evaluation."""

from __future__ import annotations

from pathlib import Path

import yaml

from eventweave.compiler import compile_scenario_file
from eventweave.core.ground_truth import GroundTruth
from eventweave.evaluation.agent_output import AgentOutput
from eventweave.evaluation.benchmark import (
    BenchmarkAgentResult,
    BenchmarkSuite,
    Scorecard,
)
from eventweave.evaluation.evaluator import Evaluator
from eventweave.evaluation.report import EvaluationReport


def load_suite(path: str | Path) -> BenchmarkSuite:
    """Load a benchmark suite from a YAML file."""
    suite_path = Path(path)
    with suite_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return BenchmarkSuite.model_validate(data)


def _discover_agent_output(agent_dir: Path, scenario_id: str) -> Path | None:
    """Find the agent output file for a scenario id inside an agent directory.

    Tries `{scenario_id}.json` first, then `{scenario_id}_agent_output.json`.
    """
    candidates = [
        agent_dir / f"{scenario_id}.json",
        agent_dir / f"{scenario_id}_agent_output.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_ground_truth(scenario_path: str | Path) -> GroundTruth:
    """Compile a scenario file and return its ground truth."""
    result = compile_scenario_file(scenario_path)
    if result.errors:
        errors = "; ".join(result.errors)
        raise BenchmarkRunError(f"Failed to compile {scenario_path}: {errors}")
    if result.plan.scenario.ground_truth is None:
        raise BenchmarkRunError(f"Scenario {scenario_path} has no ground_truth")
    return result.plan.scenario.ground_truth


def _load_agent_output(path: Path) -> AgentOutput:
    """Load an agent output JSON file."""
    import json

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return AgentOutput.model_validate(data)


def _aggregate_metrics(reports: dict[str, EvaluationReport]) -> dict[str, float]:
    """Average each metric across scenarios."""
    if not reports:
        return {}

    metric_names = list(next(iter(reports.values())).metrics.keys())
    aggregates: dict[str, float] = {}
    for name in metric_names:
        values = [report.metrics[name] for report in reports.values() if name in report.metrics]
        aggregates[name] = sum(values) / len(values) if values else 0.0
    return aggregates


def _rank_agents(results: list[BenchmarkAgentResult]) -> list[str]:
    """Rank agents by balanced_score, then overall_score, descending."""

    def _key(result: BenchmarkAgentResult) -> tuple[float, float]:
        return (
            result.aggregate.get("balanced_score", 0.0),
            result.aggregate.get("overall_score", 0.0),
        )

    return [result.agent_name for result in sorted(results, key=_key, reverse=True)]


class BenchmarkRunError(Exception):
    """Raised when a benchmark run cannot complete."""


def run_benchmark(
    suite: BenchmarkSuite,
    agent_dirs: list[Path],
) -> Scorecard:
    """Run a benchmark suite against one or more agent output directories."""
    agent_results: list[BenchmarkAgentResult] = []

    for agent_dir in agent_dirs:
        agent_name = agent_dir.name
        per_scenario: dict[str, EvaluationReport] = {}

        for scenario in suite.scenarios:
            ground_truth = _load_ground_truth(scenario.scenario_path)
            output_path = _discover_agent_output(agent_dir, ground_truth.scenario_id)
            if output_path is None:
                expected = agent_dir / f"{ground_truth.scenario_id}.json"
                raise BenchmarkRunError(
                    f"Agent {agent_name!r} missing output for scenario "
                    f"{ground_truth.scenario_id!r} (looked for {expected})"
                )

            agent_output = _load_agent_output(output_path)
            report = Evaluator(ground_truth, agent_output).evaluate()
            per_scenario[scenario.id] = report

        aggregate = _aggregate_metrics(per_scenario)
        agent_results.append(
            BenchmarkAgentResult(
                agent_name=agent_name,
                per_scenario=per_scenario,
                aggregate=aggregate,
            )
        )

    ranking = _rank_agents(agent_results)
    return Scorecard(suite=suite, results=agent_results, ranking=ranking)
