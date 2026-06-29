"""Tests for the benchmark suite validator."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eventweave.cli.main import app
from eventweave.evaluation.validator import SuiteValidator

runner = CliRunner()


def test_validator_passes_real_security_suite() -> None:
    report = SuiteValidator().validate("benchmarks/security.yaml")
    assert report.passed
    assert report.suite_id == "security_baseline"


def test_validator_passes_real_ecommerce_suite() -> None:
    report = SuiteValidator().validate("benchmarks/ecommerce.yaml")
    assert report.passed
    assert report.suite_id == "ecommerce_baseline"


def test_validator_missing_suite() -> None:
    report = SuiteValidator().validate("benchmarks/missing.yaml")
    assert not report.passed
    assert any(c.name == "suite_exists" and not c.passed for c in report.checks)


def test_validator_duplicate_scenario_ids(tmp_path: Path) -> None:
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        """
id: duplicate_suite
scenarios:
  - id: same
    scenario_path: examples/security/lateral_movement.yaml
  - id: same
    scenario_path: examples/ecommerce/refund.yaml
""",
        encoding="utf-8",
    )
    report = SuiteValidator().validate(suite_path)
    assert not report.passed
    check = next(c for c in report.checks if c.name == "unique_scenario_ids")
    assert not check.passed
    assert "same" in check.message


def test_validator_invalid_evidence_event_id(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        """
id: bad_evidence
domain: security
for_each: user
duration: 5m
seed: 1
entities:
  user:
    count: 1
    type: user
timeline:
  - id: login
    at: "00:00:00"
    event: user.login.failed
    entity_refs:
      user: "$flow"
ground_truth:
  scenario_id: bad_evidence
  expected_findings:
    - type: bad_login
      stage: initial_access
      evidence_event_ids:
        - nonexistent_event
""",
        encoding="utf-8",
    )
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        f"""
id: bad_evidence_suite
scenarios:
  - id: bad_evidence
    scenario_path: {scenario_path}
""",
        encoding="utf-8",
    )
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    agent_dir.joinpath("bad_evidence.json").write_text(
        json.dumps(
            {
                "scenario_id": "bad_evidence",
                "findings": [
                    {
                        "type": "bad_login",
                        "stage": "initial_access",
                        "entities": [],
                        "evidence_event_ids": [],
                        "confidence": 0.9,
                    }
                ],
                "key_event_ids": [],
                "timeline_stages": [],
                "summary": "bad",
            }
        ),
        encoding="utf-8",
    )

    report = SuiteValidator(agent_dir=agent_dir).validate(suite_path)
    assert not report.passed
    check = next(c for c in report.checks if "evidence_events" in c.name)
    assert not check.passed
    assert "nonexistent_event" in check.message


def test_validator_low_sample_score(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        """
id: low_score
domain: security
for_each: user
duration: 5m
seed: 1
entities:
  user:
    count: 1
    type: user
timeline:
  - id: login
    at: "00:00:00"
    event: user.login.failed
    entity_refs:
      user: "$flow"
ground_truth:
  scenario_id: low_score
  expected_findings:
    - type: missing_finding
      stage: initial_access
""",
        encoding="utf-8",
    )
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        f"""
id: low_score_suite
scenarios:
  - id: low_score
    scenario_path: {scenario_path}
""",
        encoding="utf-8",
    )
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    agent_dir.joinpath("low_score.json").write_text(
        json.dumps(
            {
                "scenario_id": "low_score",
                "findings": [],
                "key_event_ids": [],
                "timeline_stages": [],
                "summary": "nothing",
            }
        ),
        encoding="utf-8",
    )

    report = SuiteValidator(min_score=1.0, agent_dir=agent_dir).validate(suite_path)
    assert not report.passed
    check = next(c for c in report.checks if "sample_score" in c.name)
    assert not check.passed


def test_cli_benchmark_validate_passes() -> None:
    result = runner.invoke(app, ["benchmark", "validate", "--suite", "benchmarks/security.yaml"])
    assert result.exit_code == 0, result.output
    assert "security_baseline" in result.output
    assert "passed" in result.output


def test_cli_benchmark_validate_writes_report(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "benchmark",
            "validate",
            "--suite",
            "benchmarks/ecommerce.yaml",
            "--output",
            str(report_path),
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["suite_id"] == "ecommerce_baseline"
    assert data["passed"] is True


def test_cli_benchmark_validate_fails_on_bad_suite(tmp_path: Path) -> None:
    suite_path = tmp_path / "bad.yaml"
    suite_path.write_text(
        f"""
id: bad_suite
scenarios:
  - id: missing
    scenario_path: {tmp_path}/no_such_scenario.yaml
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["benchmark", "validate", "--suite", str(suite_path)])
    assert result.exit_code == 1
    assert "failed" in result.output
