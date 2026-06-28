"""Tests for scenario compiler."""

from __future__ import annotations

from pathlib import Path

from eventweave.compiler.engine import compile_scenario_file


class TestCompileScenario:
    def test_compile_ecommerce_refund(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        plan = result.plan
        assert plan.scenario.id == "ecommerce_refund_flow"
        assert len(plan.entities) == 35  # 10 customers + 5 products + 20 orders
        assert len(plan.events) > 0
        assert all(e.event_type for e in plan.events)
        assert all(e.event_time for e in plan.events)

    def test_compile_security_lateral_movement(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "security" / "lateral_movement.yaml"
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        plan = result.plan
        assert plan.scenario.id == "security_lateral_movement"
        assert len(plan.entities) == 33  # 5 users + 10 hosts + 15 ips + 3 alerts
        assert len(plan.events) > 0

    def test_deterministic_with_same_seed(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result1 = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)
        result2 = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        event_ids_1 = [e.event_id for e in result1.plan.events]
        event_ids_2 = [e.event_id for e in result2.plan.events]
        assert event_ids_1 == event_ids_2

        event_types_1 = [e.event_type for e in result1.plan.events]
        event_types_2 = [e.event_type for e in result2.plan.events]
        assert event_types_1 == event_types_2
