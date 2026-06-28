"""Tests for the eval validate-output CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eventweave.cli.main import app

runner = CliRunner()


def test_eval_validate_output_success(tmp_path: Path) -> None:
    path = tmp_path / "agent_output.json"
    path.write_text(
        json.dumps(
            {
                "scenario_id": "s",
                "findings": [{"type": "f"}],
                "key_event_ids": [],
                "timeline_stages": [],
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["eval", "validate-output", str(path)])
    assert result.exit_code == 0, result.output
    assert "Valid agent output" in result.output


def test_eval_validate_output_failure(tmp_path: Path) -> None:
    path = tmp_path / "agent_output.json"
    path.write_text(json.dumps({"scenario_id": 123}), encoding="utf-8")
    result = runner.invoke(app, ["eval", "validate-output", str(path)])
    assert result.exit_code == 1, result.output
    assert "Invalid agent output" in result.output
