"""Tests for the synthetic realism report."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eventweave.cli.main import app
from eventweave.compiler import compile_scenario
from eventweave.core.scenario import Scenario
from eventweave.quality.realism import RealismAnalyzer

runner = CliRunner()


def _noisy_scenario() -> Scenario:
    return Scenario.model_validate(
        {
            "id": "realism_test",
            "domain": "security",
            "for_each": "host",
            "duration": "10m",
            "seed": 42,
            "entities": {"host": {"count": 2, "type": "host"}},
            "sources": [{"id": "edr", "type": "service", "role": "edr"}],
            "timeline": [
                {
                    "id": "login",
                    "at": "00:00:00",
                    "event": "user.login.failed",
                    "source": "edr",
                    "entity_refs": {"host": "$flow"},
                }
            ],
            "noise": {
                "enabled": True,
                "ratio": 4.0,
                "events": [
                    {"event": "user.login.success", "weight": 1},
                    {"event": "dns.query", "weight": 1},
                ],
            },
            "ground_truth": {
                "scenario_id": "realism_test",
                "expected_findings": [
                    {
                        "type": "suspicious_login",
                        "stage": "initial_access",
                        "evidence_event_ids": ["evt-realism-test-001-001"],
                    }
                ],
            },
        }
    )


def test_realism_report_counts_noise_events() -> None:
    scenario = _noisy_scenario()
    result = compile_scenario(scenario)
    report = RealismAnalyzer(result.plan, result.plan.scenario.ground_truth).analyze()

    assert report.total_events > 0
    assert report.noise_events > 0
    assert report.ground_truth_events > 0
    assert report.noise_ratio > 0
    assert report.ground_truth_coverage == 1.0
    assert report.scenario_id == "realism_test"


def test_realism_report_json_written(tmp_path: Path) -> None:
    scenario = _noisy_scenario()
    result = compile_scenario(scenario)
    output = tmp_path / "realism.json"

    report_path = tmp_path / "plan"
    from eventweave.compiler.writer import PlanWriter

    PlanWriter(report_path, force=True).write(result.plan)

    result_cli = runner.invoke(
        app,
        [
            "quality",
            "realism",
            str(report_path),
            "--output",
            str(output),
        ],
    )
    assert result_cli.exit_code == 0, result_cli.output
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["scenario_id"] == "realism_test"
    assert data["noise_events"] > 0


def test_quality_realism_cli() -> None:
    scenario = _noisy_scenario()
    result = compile_scenario(scenario)
    report_path = Path("dist/realism_test_plan")
    from eventweave.compiler.writer import PlanWriter

    PlanWriter(report_path, force=True).write(result.plan)

    result_cli = runner.invoke(app, ["quality", "realism", str(report_path)])
    assert result_cli.exit_code == 0, result_cli.output
    assert "Realism Report" in result_cli.output
    assert "realism_test" in result_cli.output
