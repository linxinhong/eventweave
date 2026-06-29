"""Tests for the benchmark harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from eventweave.cli.main import app
from eventweave.evaluation.benchmark import BenchmarkSuite
from eventweave.evaluation.runner import BenchmarkRunError, load_suite, run_benchmark

runner = CliRunner()


def test_load_benchmark_suite(tmp_path: Path) -> None:
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        """
id: test_suite
name: Test suite
description: A test suite.
scenarios:
  - id: s1
    scenario_path: scenarios/s1.yaml
""",
        encoding="utf-8",
    )
    suite = load_suite(suite_path)
    assert suite.id == "test_suite"
    assert suite.name == "Test suite"
    assert len(suite.scenarios) == 1
    assert suite.scenarios[0].id == "s1"
    assert str(suite.scenarios[0].scenario_path) == "scenarios/s1.yaml"


def test_benchmark_suite_model_validation() -> None:
    suite = BenchmarkSuite.model_validate(
        {
            "id": "suite",
            "scenarios": [
                {"id": "s1", "scenario_path": "examples/security/lateral_movement.yaml"}
            ],
        }
    )
    assert suite.id == "suite"
    assert isinstance(suite.scenarios[0].scenario_path, Path)


def test_run_benchmark_missing_agent_output(tmp_path: Path) -> None:
    suite = BenchmarkSuite(
        id="test_suite",
        scenarios=[
            {"id": "lateral_movement", "scenario_path": "examples/security/lateral_movement.yaml"}
        ],
    )
    agent_dir = tmp_path / "empty_agent"
    agent_dir.mkdir()

    with pytest.raises(BenchmarkRunError, match="missing output"):
        run_benchmark(suite, [agent_dir])


def test_run_benchmark_perfect_sample_outputs(tmp_path: Path) -> None:
    suite = BenchmarkSuite(
        id="sample_suite",
        scenarios=[
            {"id": "lateral_movement", "scenario_path": "examples/security/lateral_movement.yaml"},
            {"id": "refund_flow", "scenario_path": "examples/ecommerce/refund.yaml"},
        ],
    )
    agent_dir = tmp_path / "perfect_agent"
    agent_dir.mkdir()

    security_output = Path(
        "examples/evaluation/security_lateral_movement_agent_output.json"
    ).read_text(encoding="utf-8")
    ecommerce_output = Path(
        "examples/evaluation/ecommerce_refund_flow_agent_output.json"
    ).read_text(encoding="utf-8")
    (agent_dir / "security_lateral_movement.json").write_text(security_output, encoding="utf-8")
    (agent_dir / "ecommerce_refund_flow.json").write_text(ecommerce_output, encoding="utf-8")

    scorecard = run_benchmark(suite, [agent_dir])

    assert scorecard.suite.id == "sample_suite"
    assert len(scorecard.results) == 1
    result = scorecard.results[0]
    assert result.agent_name == "perfect_agent"
    assert result.aggregate["overall_score"] == 1.0
    assert result.aggregate["balanced_score"] == 1.0
    assert scorecard.ranking == ["perfect_agent"]


def test_run_benchmark_leaderboard_order(tmp_path: Path) -> None:
    suite = BenchmarkSuite(
        id="leaderboard_suite",
        scenarios=[
            {"id": "refund_flow", "scenario_path": "examples/ecommerce/refund.yaml"},
        ],
    )

    good_agent_dir = tmp_path / "good_agent"
    good_agent_dir.mkdir()
    good_output = json.loads(
        Path("examples/evaluation/ecommerce_refund_flow_agent_output.json").read_text(encoding="utf-8")
    )
    (good_agent_dir / "ecommerce_refund_flow.json").write_text(
        json.dumps(good_output), encoding="utf-8"
    )

    bad_agent_dir = tmp_path / "bad_agent"
    bad_agent_dir.mkdir()
    bad_output = dict(good_output)
    bad_output["findings"] = []
    (bad_agent_dir / "ecommerce_refund_flow.json").write_text(
        json.dumps(bad_output), encoding="utf-8"
    )

    scorecard = run_benchmark(suite, [bad_agent_dir, good_agent_dir])
    assert scorecard.ranking == ["good_agent", "bad_agent"]


def test_cli_benchmark_list(tmp_path: Path) -> None:
    suite_path = tmp_path / "test_suite.yaml"
    suite_path.write_text("id: test_suite\nscenarios: []\n", encoding="utf-8")

    result = runner.invoke(app, ["benchmark", "list", "--suites-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "test_suite" in result.output


def test_cli_benchmark_run(tmp_path: Path) -> None:
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        """
id: cli_suite
scenarios:
  - id: refund_flow
    scenario_path: examples/ecommerce/refund.yaml
""",
        encoding="utf-8",
    )

    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    good_output = Path("examples/evaluation/ecommerce_refund_flow_agent_output.json").read_text(
        encoding="utf-8"
    )
    (agent_dir / "ecommerce_refund_flow.json").write_text(good_output, encoding="utf-8")

    scorecard_path = tmp_path / "scorecard.json"
    result = runner.invoke(
        app,
        [
            "benchmark",
            "run",
            "--suite",
            str(suite_path),
            "--agent-outputs",
            str(agent_dir),
            "--output",
            str(scorecard_path),
        ],
    )
    assert result.exit_code == 0, result.output
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert scorecard["suite"]["id"] == "cli_suite"
    assert scorecard["results"][0]["aggregate"]["overall_score"] == 1.0
    assert "Benchmark Scorecard" in result.output


def test_cli_benchmark_leaderboard(tmp_path: Path) -> None:
    scorecard = {
        "suite": {"id": "leaderboard_suite", "scenarios": []},
        "generated_at": "2026-06-28T12:00:00+00:00",
        "results": [
            {
                "agent_name": "agent_a",
                "per_scenario": {},
                "aggregate": {"overall_score": 0.9, "balanced_score": 0.85},
            },
            {
                "agent_name": "agent_b",
                "per_scenario": {},
                "aggregate": {"overall_score": 0.8, "balanced_score": 0.9},
            },
        ],
        "ranking": ["agent_b", "agent_a"],
    }
    scorecard_path = tmp_path / "scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

    result = runner.invoke(app, ["benchmark", "leaderboard", str(scorecard_path)])
    assert result.exit_code == 0, result.output
    assert "agent_b" in result.output
    assert "agent_a" in result.output
    assert "Leaderboard" in result.output
