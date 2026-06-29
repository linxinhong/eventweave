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
    BenchmarkRunError,
    _discover_agent_output,
    _load_agent_output,
    _load_ground_truth,
    load_suite,
)


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    message: str = ""


@dataclass
class ValidationReport:
    """Report produced by validating a benchmark suite."""

    suite_id: str
    passed: bool = False
    checks: list[CheckResult] = field(default_factory=list)

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
        }


class SuiteValidator:
    """Validates a benchmark suite and its sample data."""

    def __init__(
        self,
        min_score: float = 1.0,
        agent_dir: str | Path | None = None,
    ) -> None:
        self.min_score = min_score
        self.agent_dir = Path(agent_dir) if agent_dir is not None else Path("examples/evaluation")

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

        try:
            ground_truth = _load_ground_truth(scenario_path)
        except BenchmarkRunError as exc:
            report.add(
                f"{scenario_id}_ground_truth",
                False,
                f"Failed to load ground truth: {exc}",
            )
            return
        except Exception as exc:  # noqa: BLE001
            report.add(
                f"{scenario_id}_compile",
                False,
                f"Failed to compile scenario: {exc}",
            )
            return

        report.add(
            f"{scenario_id}_compile",
            True,
            "Scenario compiled successfully",
        )
        report.add(
            f"{scenario_id}_ground_truth",
            True,
            f"Ground truth has {len(ground_truth.expected_findings)} expected findings",
        )

        self._check_scenario_id_match(scenario_path, scenario_id, ground_truth, report)
        self._check_evidence_event_ids(scenario_path, ground_truth, report)
        self._check_duplicate_findings(scenario_id, ground_truth.expected_findings, report)
        self._check_sample_output(ground_truth, report)

    def _compile_or_report(
        self, scenario_path: Path, scenario_id: str, report: ValidationReport
    ) -> Any | None:
        result = compile_scenario_file(scenario_path)
        if result.errors or result.plan is None:
            report.add(
                f"{scenario_id}_compile",
                False,
                "Cannot validate scenario: compilation failed",
            )
            return None
        return result.plan

    def _check_scenario_id_match(
        self,
        scenario_path: Path,
        scenario_id: str,
        ground_truth: Any,
        report: ValidationReport,
    ) -> None:
        plan = self._compile_or_report(scenario_path, scenario_id, report)
        if plan is None:
            return
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
        scenario_path: Path,
        ground_truth: Any,
        report: ValidationReport,
    ) -> None:
        scenario_id = ground_truth.scenario_id
        plan = self._compile_or_report(scenario_path, scenario_id, report)
        if plan is None:
            report.add(
                f"{scenario_id}_evidence_events",
                False,
                "Cannot validate evidence events: compilation failed",
            )
            return

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
