"""Tests for the runtime plan writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventweave.compiler.writer import PlanWriter
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario


def test_writer_creates_plan_files(tmp_path: Path) -> None:
    scenario = Scenario(id="test", domain="security")
    plan = RuntimePlan(scenario=scenario)
    output_dir = tmp_path / "out"

    writer = PlanWriter(output_dir)
    written = writer.write(plan)

    assert written["scenario"].exists()
    assert written["runtime_plan"].exists()
    assert (output_dir / "event_plan.jsonl").exists()


def test_writer_refuses_path_outside_allowed_root(tmp_path: Path) -> None:
    scenario = Scenario(id="test", domain="security")
    plan = RuntimePlan(scenario=scenario)
    output_dir = tmp_path / ".." / "escaped"

    writer = PlanWriter(output_dir, allowed_root=tmp_path)
    with pytest.raises(ValueError, match="outside allowed root"):
        writer.write(plan)


def test_writer_refuses_non_empty_directory_without_force(tmp_path: Path) -> None:
    scenario = Scenario(id="test", domain="security")
    plan = RuntimePlan(scenario=scenario)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "existing.txt").write_text("data", encoding="utf-8")

    writer = PlanWriter(output_dir)
    with pytest.raises(ValueError, match="not empty"):
        writer.write(plan)


def test_writer_overwrites_non_empty_directory_with_force(tmp_path: Path) -> None:
    scenario = Scenario(id="test", domain="security")
    plan = RuntimePlan(scenario=scenario)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "existing.txt").write_text("data", encoding="utf-8")

    writer = PlanWriter(output_dir, force=True)
    written = writer.write(plan)
    assert written["scenario"].exists()
