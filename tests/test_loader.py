"""Tests for scenario loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventweave.compiler.loader import ScenarioLoadError, load_scenario


class TestLoadScenario:
    def test_load_ecommerce_refund(self, project_root: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        scenario = load_scenario(path)
        assert scenario.id == "ecommerce_refund_flow"
        assert scenario.domain == "ecommerce"
        assert len(scenario.timeline) > 0

    def test_load_security_lateral_movement(self, project_root: Path) -> None:
        path = project_root / "examples" / "security" / "lateral_movement.yaml"
        scenario = load_scenario(path)
        assert scenario.id == "security_lateral_movement"
        assert scenario.domain == "security"

    def test_missing_file(self) -> None:
        with pytest.raises(ScenarioLoadError):
            load_scenario("nonexistent.yaml")

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        bad = tmp_path / "scenario.txt"
        bad.write_text("id: test")
        with pytest.raises(ScenarioLoadError):
            load_scenario(bad)
