"""Benchmark suite validation and dataset quality gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eventweave.compiler import compile_scenario_file
from eventweave.core.ground_truth import ExpectedFinding
from eventweave.evaluation.benchmark import BenchmarkSuite
from eventweave.evaluation.evaluator import Evaluator
from eventweave.evaluation.runner import (
    _discover_agent_output,
    _load_agent_output,
    load_suite,
)
from eventweave.quality.realism import RealismAnalyzer


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    message: str = ""


@dataclass
class RealismGate:
    """Optional thresholds a scenario must satisfy to be considered realistic."""

    min_noise_ratio: float | None = None
    min_event_types: int | None = None
    min_sources: int | None = None
    max_burstiness: float | None = None
    require_jitter: bool = False


@dataclass
class ValidationReport:
    """Report produced by validating a benchmark suite."""

    suite_id: str
    passed: bool = False
    checks: list[CheckResult] = field(default_factory=list)
    realism: dict[str, Any] = field(default_factory=dict)

    def add(self, name: str, passed: bool, message: str = "") -> None:
        self.checks.append(CheckResult(name=name, passed=passed, message=message))
        self.passed = all(c.passed for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "passed": self.passed,
            "checks": [
                {"name": c.name, "passed": c.passed, "message": c.message}
                for c in self.checks
            ],
            "realism": self.realism,
        }


class SuiteValidator:
    """Validates a benchmark suite and its sample data."""

    def __init__(
        self,
        min_score: float = 1.0,
        agent_dir: str | Path | None = None,
        realism_gates: RealismGate | None = None,
    ) -> None:
        self.min_score = min_score
        self.agent_dir = Path(agent_dir) if agent_dir is not None else Path("examples/evaluation")
        self.realism_gates = realism_gates or RealismGate()

    def validate(self, suite_path: str | Path) -> ValidationReport:
        """Run all validation checks against a suite file."""
        path = Path(suite_path)
        report = ValidationReport(suite_id="")

        suite = self._load_suite(path, report)
        if suite is None:
            return report

        report.suite_id = suite.id
        self._check_unique_scenario_ids(suite, report)

        for scenario in suite.scenarios:
            self._validate_scenario(scenario, report)

        return report

    def _load_suite(
        self, path: Path, report: ValidationReport
    ) -> BenchmarkSuite | None:
        if not path.exists():
            report.add("suite_exists", False, f"Suite file not found: {path}")
            return None

        try:
            suite = load_suite(path)
        except Exception as exc:  # noqa: BLE001
            report.add("suite_load", False, f"Failed to load suite: {exc}")
            return None

        report.add("suite_load", True, f"Loaded suite {suite.id}")
        return suite

    def _check_unique_scenario_ids(
        self, suite: BenchmarkSuite, report: ValidationReport
    ) -> None:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for scenario in suite.scenarios:
            if scenario.id in seen:
                duplicates.add(scenario.id)
            seen.add(scenario.id)

        if duplicates:
            report.add(
                "unique_scenario_ids",
                False,
                f"Duplicate scenario ids: {', '.join(sorted(duplicates))}",
            )
        else:
            report.add("unique_scenario_ids", True, "All scenario ids are unique")

    def _validate_scenario(
        self, scenario: Any, report: ValidationReport
    ) -> None:
        scenario_id = scenario.id
        scenario_path = scenario.scenario_path

        if not scenario_path.exists():
            report.add(
                f"{scenario_id}_exists",
                False,
                f"Scenario file not found: {scenario_path}",
            )
            return
        report.add(f"{scenario_id}_exists", True, "Scenario file exists")

        result = compile_scenario_file(scenario_path)
        if result.errors or result.plan is None:
            report.add(
                f"{scenario_id}_compile",
                False,
                "Cannot validate scenario: compilation failed",
            )
            return

        plan = result.plan
        report.add(
            f"{scenario_id}_compile",
            True,
            "Scenario compiled successfully",
        )

        if plan.scenario.ground_truth is None:
            report.add(
                f"{scenario_id}_ground_truth",
                False,
                "Scenario has no ground_truth",
            )
            return

        ground_truth = plan.scenario.ground_truth
        report.add(
            f"{scenario_id}_ground_truth",
            True,
            f"Ground truth has {len(ground_truth.expected_findings)} expected findings",
        )

        self._check_scenario_id_match(scenario_id, ground_truth, plan, report)
        self._check_evidence_event_ids(ground_truth, plan, report)
        self._check_duplicate_findings(scenario_id, ground_truth.expected_findings, report)
        self._check_sample_output(ground_truth, report)
        self._check_realism(scenario_id, plan, ground_truth, report)

    def _check_scenario_id_match(
        self,
        scenario_id: str,
        ground_truth: Any,
        plan: Any,
        report: ValidationReport,
    ) -> None:
        if ground_truth.scenario_id != plan.scenario.id:
            report.add(
                f"{scenario_id}_scenario_id_match",
                False,
                f"Ground truth scenario_id {ground_truth.scenario_id!r} "
                f"does not match scenario file id {plan.scenario.id!r}",
            )
        else:
            report.add(
                f"{scenario_id}_scenario_id_match",
                True,
                "Ground truth scenario_id matches scenario file id",
            )

    def _check_evidence_event_ids(
        self,
        ground_truth: Any,
        plan: Any,
        report: ValidationReport,
    ) -> None:
        scenario_id = ground_truth.scenario_id
        event_ids = {ev.event_id for ev in plan.events}
        invalid: set[str] = set()
        for finding in ground_truth.expected_findings:
            for event_id in finding.evidence_event_ids or []:
                if event_id not in event_ids:
                    invalid.add(event_id)

        if invalid:
            report.add(
                f"{scenario_id}_evidence_events",
                False,
                f"Invalid evidence_event_ids: {', '.join(sorted(invalid))}",
            )
        else:
            report.add(
                f"{scenario_id}_evidence_events",
                True,
                "All evidence_event_ids reference existing events",
            )

    def _check_duplicate_findings(
        self,
        scenario_id: str,
        findings: list[ExpectedFinding],
        report: ValidationReport,
    ) -> None:
        seen: set[tuple[str, str]] = set()
        duplicates: set[tuple[str, str]] = set()
        for finding in findings:
            key = (finding.type, finding.stage or "")
            if key in seen:
                duplicates.add(key)
            seen.add(key)

        if duplicates:
            report.add(
                f"{scenario_id}_unique_findings",
                False,
                f"Duplicate expected findings by (type, stage): {sorted(duplicates)}",
            )
        else:
            report.add(
                f"{scenario_id}_unique_findings",
                True,
                "All expected findings are unique by (type, stage)",
            )

    def _check_sample_output(
        self,
        ground_truth: Any,
        report: ValidationReport,
    ) -> None:
        scenario_id = ground_truth.scenario_id
        output_path = _discover_agent_output(self.agent_dir, scenario_id)
        if output_path is None:
            report.add(
                f"{scenario_id}_sample_output",
                False,
                f"Sample agent output not found in {self.agent_dir}",
            )
            return

        try:
            agent_output = _load_agent_output(output_path)
        except Exception as exc:  # noqa: BLE001
            report.add(
                f"{scenario_id}_sample_output",
                False,
                f"Sample agent output is invalid: {exc}",
            )
            return

        report.add(
            f"{scenario_id}_sample_output",
            True,
            "Sample agent output is valid",
        )

        eval_report = Evaluator(ground_truth, agent_output).evaluate()
        score = eval_report.metrics.get("overall_score", 0.0)
        if score >= self.min_score:
            report.add(
                f"{scenario_id}_sample_score",
                True,
                f"Sample overall_score = {score:.2f}",
            )
        else:
            report.add(
                f"{scenario_id}_sample_score",
                False,
                f"Sample overall_score = {score:.2f}, required >= {self.min_score:.2f}",
            )

    def _check_realism(
        self,
        scenario_id: str,
        plan: Any,
        ground_truth: Any,
        report: ValidationReport,
    ) -> None:
        """Run optional realism gate checks for a compiled scenario."""
        gate = self.realism_gates
        if (
            gate.min_noise_ratio is None
            and gate.min_event_types is None
            and gate.min_sources is None
            and gate.max_burstiness is None
            and not gate.require_jitter
        ):
            return

        analysis = RealismAnalyzer(plan, ground_truth).analyze()
        metrics: dict[str, Any] = analysis.to_dict()
        key_events = metrics.get("ground_truth_events", 0)
        noise_events = metrics.get("noise_events", 0)
        metrics["noise_multiplier"] = (
            noise_events / key_events if key_events else 0.0
        )
        report.realism[scenario_id] = metrics

        if gate.min_noise_ratio is not None:
            multiplier = metrics["noise_multiplier"]
            passed = multiplier >= gate.min_noise_ratio
            report.add(
                f"{scenario_id}_realism_noise",
                passed,
                f"noise_multiplier={multiplier:.2f}, required >= {gate.min_noise_ratio:.2f}",
            )

        if gate.min_event_types is not None:
            event_types = len(metrics.get("event_type_distribution", {}))
            passed = event_types >= gate.min_event_types
            report.add(
                f"{scenario_id}_realism_event_types",
                passed,
                f"event_types={event_types}, required >= {gate.min_event_types}",
            )

        if gate.min_sources is not None:
            sources = metrics.get("unique_sources", 0)
            passed = sources >= gate.min_sources
            report.add(
                f"{scenario_id}_realism_sources",
                passed,
                f"sources={sources}, required >= {gate.min_sources}",
            )

        if gate.max_burstiness is not None:
            burstiness = metrics.get("burstiness_score", 0.0)
            passed = burstiness <= gate.max_burstiness
            report.add(
                f"{scenario_id}_realism_burstiness",
                passed,
                f"burstiness={burstiness:.3f}, required <= {gate.max_burstiness:.3f}",
            )

        if gate.require_jitter:
            jitter = plan.scenario.jitter
            passed = jitter is not None and jitter.enabled
            report.add(
                f"{scenario_id}_realism_jitter",
                passed,
                "jitter is enabled" if passed else "jitter is not enabled",
            )
