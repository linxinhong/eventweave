"""Tests for streaming runtime plan loaders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eventweave.core.event import Event
from eventweave.runtime.loader import iter_event_plan


def test_iter_event_plan_yields_events(tmp_path: Path) -> None:
    path = tmp_path / "event_plan.jsonl"
    path.write_text(
        json.dumps(
            {
                "event_id": "e1",
                "scenario_id": "sc1",
                "source_id": "src1",
                "event_type": "login",
                "event_time": "2024-01-01T00:00:00Z",
                "entity_refs": {},
                "attributes": {},
                "semantic_refs": [],
                "labels": [],
                "ground_truth": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    events = list(iter_event_plan(path))
    assert len(events) == 1
    assert isinstance(events[0], Event)
    assert events[0].event_id == "e1"


def test_iter_event_plan_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "event_plan.jsonl"
    path.write_text(
        "\n"
        + json.dumps(
            {
                "event_id": "e1",
                "scenario_id": "sc1",
                "source_id": "src1",
                "event_type": "login",
                "event_time": "2024-01-01T00:00:00Z",
                "entity_refs": {},
                "attributes": {},
                "semantic_refs": [],
                "labels": [],
                "ground_truth": {},
            }
        )
        + "\n\n",
        encoding="utf-8",
    )

    events = list(iter_event_plan(path))
    assert len(events) == 1


def test_iter_event_plan_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list(iter_event_plan(tmp_path / "missing.jsonl"))
