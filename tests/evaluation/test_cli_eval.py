"""Tests for the eval CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eventweave.cli.main import app
from eventweave.core.ground_truth import GroundTruth
from eventweave.evaluation.agent_output import AgentFinding, AgentOutput

runner = CliRunner()


def test_eval_task_missing_ground_truth(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    (plan_dir / "scenario.json").write_text(
        json.dumps({"id": "s", "domain": "security"}), encoding="utf-8"
    )
    (plan_dir / "event_plan.jsonl").write_text("", encoding="utf-8")
    result = runner.invoke(app, ["eval", "task", str(plan_dir)])
    assert result.exit_code == 1
    assert "Ground truth not found" in result.output


def test_eval_task_success(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    (plan_dir / "scenario.json").write_text(
        json.dumps({"id": "s", "domain": "security", "name": "Test"}),
        encoding="utf-8",
    )
    ground_truth = GroundTruth(scenario_id="s")
    (plan_dir / "ground_truth.json").write_text(
        ground_truth.model_dump_json(indent=2), encoding="utf-8"
    )
    (plan_dir / "event_plan.jsonl").write_text("", encoding="utf-8")

    output = plan_dir / "eval" / "task.json"
    result = runner.invoke(
        app, ["eval", "task", str(plan_dir), "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    task = json.loads(output.read_text(encoding="utf-8"))
    assert task["scenario_id"] == "s"
    assert "output_schema" in task
    assert task["ground_truth_path"].endswith("ground_truth.json")


def test_eval_run_produces_report(tmp_path: Path) -> None:
    ground_truth_path = tmp_path / "ground_truth.json"
    agent_output_path = tmp_path / "agent_output.json"
    report_path = tmp_path / "report.json"

    ground_truth = GroundTruth(
        scenario_id="s",
        expected_findings=[
            {"type": "suspicious_login", "stage": "initial_access"},
        ],
    )
    agent_output = AgentOutput(
        scenario_id="s",
        findings=[
            AgentFinding(type="suspicious_login", stage="initial_access"),
        ],
    )

    ground_truth_path.write_text(
        ground_truth.model_dump_json(indent=2), encoding="utf-8"
    )
    agent_output_path.write_text(
        agent_output.model_dump_json(indent=2), encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "eval",
            "run",
            "--ground-truth",
            str(ground_truth_path),
            "--agent-output",
            str(agent_output_path),
            "--output",
            str(report_path),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["scenario_id"] == "s"
    assert report["metrics"]["finding_type_recall"] == 1.0
    assert "Evaluation Report" in result.output
def test_eval_prepare_creates_ground_truth(tmp_path: Path) -> None:
    output_dir = tmp_path / "dist"
    result = runner.invoke(
        app,
        [
            "eval",
            "prepare",
            "examples/ecommerce/refund.yaml",
            "-o",
            str(output_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    gt_path = output_dir / "ecommerce_refund_flow" / "ground_truth.json"
    assert gt_path.exists(), f"Ground truth not written: {gt_path}"
    ground_truth = GroundTruth.model_validate_json(gt_path.read_text(encoding="utf-8"))
    assert ground_truth.scenario_id == "ecommerce_refund_flow"
