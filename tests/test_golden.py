"""Golden tests for stable compiler output."""

from __future__ import annotations

import json
from pathlib import Path

from eventweave.compiler.engine import compile_scenario_file


class TestGoldenCompilation:
    def _event_signature(self, event: dict) -> dict:
        """Return a deterministic subset of an event for comparison."""
        return {
            "event_id": event["event_id"],
            "scenario_id": event["scenario_id"],
            "flow_id": event["flow_id"],
            "source_id": event["source_id"],
            "event_type": event["event_type"],
            "entity_refs": event["entity_refs"],
            "attributes": event["attributes"],
            "labels": event["labels"],
            "ground_truth": event["ground_truth"],
        }

    def _load_event_signatures(self, path: Path) -> list[dict]:
        events: list[dict] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                event = json.loads(line)
                events.append(self._event_signature(event))
        return events

    def test_ecommerce_refund_golden(self, project_root: Path, packs_dir: Path) -> None:
        scenario_path = project_root / "examples" / "ecommerce" / "refund.yaml"
        result = compile_scenario_file(scenario_path, packs_dir=packs_dir, seed=20260628)

        golden_path = (
            project_root / "tests" / "golden" / "ecommerce_refund_flow" / "event_plan.jsonl"
        )
        expected = self._load_event_signatures(golden_path)
        actual = [self._event_signature(e.model_dump()) for e in result.plan.events]

        assert len(actual) == len(expected)
        assert actual == expected

    def test_security_lateral_movement_golden(self, project_root: Path, packs_dir: Path) -> None:
        scenario_path = project_root / "examples" / "security" / "lateral_movement.yaml"
        result = compile_scenario_file(scenario_path, packs_dir=packs_dir, seed=20260628)

        golden_path = (
            project_root / "tests" / "golden" / "security_lateral_movement" / "event_plan.jsonl"
        )
        expected = self._load_event_signatures(golden_path)
        actual = [self._event_signature(e.model_dump()) for e in result.plan.events]

        assert len(actual) == len(expected)
        assert actual == expected
