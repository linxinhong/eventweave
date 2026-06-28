"""Tests for scenario compiler."""

from __future__ import annotations

from pathlib import Path

from eventweave.compiler.engine import (
    compile_scenario_file,
    compile_scenario_file_strict,
)


class TestCompileScenario:
    def test_compile_ecommerce_refund(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        plan = result.plan
        assert plan.scenario.id == "ecommerce_refund_flow"
        assert plan.scenario.for_each == "order"
        assert len(plan.entities) > 0
        assert len(plan.events) > 0
        assert all(e.event_type for e in plan.events)
        assert all(e.event_time for e in plan.events)

    def test_compile_security_lateral_movement(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "security" / "lateral_movement.yaml"
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        plan = result.plan
        assert plan.scenario.id == "security_lateral_movement"
        assert plan.scenario.for_each == "user"
        assert len(plan.entities) > 0
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

    def test_event_id_format(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        for event in result.plan.events:
            assert event.event_id.startswith("evt-ecommerce-refund-flow-")
            parts = event.event_id.split("-")
            assert len(parts) == 6  # evt, scenario, flow, idx, step, idx

    def test_events_sorted_by_time(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        times_and_ids = [(e.event_time, e.event_id) for e in result.plan.events]
        assert times_and_ids == sorted(times_and_ids)

    def test_step_id_refs(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)

        # Find a pay_order event and check that its order ref matches the create_order event
        # in the same flow.
        for event in result.plan.events:
            if event.event_type != "order.paid":
                continue
            order_id = event.entity_refs.get("order")
            assert order_id
            assert order_id == event.flow_id

    def test_strict_mode_returns_errors(self, project_root: Path, packs_dir: Path) -> None:
        path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result = compile_scenario_file_strict(path, packs_dir=packs_dir, seed=20260628)

        # Warnings become errors in strict mode. The example may or may not produce
        # warnings; the important invariant is that warnings list is empty when there
        # are errors, and ok reflects the state.
        assert len(result.warnings) == 0
        assert result.ok == (len(result.errors) == 0)
