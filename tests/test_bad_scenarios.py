"""Tests for invalid scenario inputs."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventweave.compiler import compile_scenario_file_strict
from eventweave.compiler.loader import ScenarioLoadError
from eventweave.compiler.planner import CompileError
from eventweave.compiler.rules import RuleViolationError


class TestBadScenarios:
    def test_invalid_duration(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "tests" / "bad_scenarios" / "invalid_duration.yaml"
        with pytest.raises(CompileError):
            compile_scenario_file_strict(path, packs_dir=packs_dir, seed=20260628)

    def test_missing_scenario_id(self, project_root: Path) -> None:
        path = project_root / "tests" / "bad_scenarios" / "missing_scenario_id.yaml"
        with pytest.raises(ScenarioLoadError):
            compile_scenario_file_strict(path)

    def test_unknown_rule_type(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "tests" / "bad_scenarios" / "unknown_rule_type.yaml"
        with pytest.raises(RuleViolationError):
            compile_scenario_file_strict(path, packs_dir=packs_dir, seed=20260628)

    def test_rule_violation_strict_fails(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "tests" / "bad_scenarios" / "rule_violation.yaml"
        result = compile_scenario_file_strict(path, packs_dir=packs_dir, seed=20260628)
        assert not result.ok
        assert len(result.errors) > 0
        assert any("order.paid" in e for e in result.errors)
