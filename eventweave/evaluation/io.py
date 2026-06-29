"""I/O helpers for evaluation artifacts.

Evaluation should consume compiled runtime plans rather than re-invoke the
compiler. This module provides helpers to load ground truth, agent output, and
event plans from a compiled plan directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from eventweave.core.event import Event
from eventweave.core.ground_truth import GroundTruth
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario
from eventweave.evaluation.agent_output import AgentOutput


class EvaluationIOError(Exception):
    """Raised when a required evaluation artifact cannot be loaded."""


def default_plan_dir_root() -> Path:
    """Return the default root for compiled plan directories.

    Defaults to ``dist`` under the current working directory, but can be
    overridden with the ``EVENTWEAVE_PLAN_DIR`` environment variable.
    """
    return Path(os.environ.get("EVENTWEAVE_PLAN_DIR", "dist"))


def load_ground_truth(path: str | Path) -> GroundTruth:
    """Load a ground truth JSON file."""
    p = Path(path)
    if not p.exists():
        raise EvaluationIOError(f"Ground truth not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return GroundTruth.model_validate(data)
    except Exception as exc:
        raise EvaluationIOError(f"Failed to load ground truth from {p}: {exc}") from exc


def load_agent_output(path: str | Path) -> AgentOutput:
    """Load an agent output JSON file."""
    p = Path(path)
    if not p.exists():
        raise EvaluationIOError(f"Agent output not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return AgentOutput.model_validate(data)
    except Exception as exc:
        raise EvaluationIOError(f"Failed to load agent output from {p}: {exc}") from exc


def load_event_plan(path: str | Path) -> list[Event]:
    """Load events from a JSONL event plan file."""
    p = Path(path)
    if not p.exists():
        raise EvaluationIOError(f"Event plan not found: {p}")
    events: list[Event] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(Event.model_validate(json.loads(line)))
    except Exception as exc:
        raise EvaluationIOError(f"Failed to load event plan from {p}: {exc}") from exc
    return events


def load_runtime_plan(plan_dir: str | Path) -> RuntimePlan:
    """Load a minimal runtime plan from a compiled plan directory.

    Only the scenario and events are required for evaluation. Entities,
    relations, and sources are left empty.
    """
    plan_dir = Path(plan_dir)
    scenario_path = plan_dir / "scenario.json"
    event_plan_path = plan_dir / "event_plan.jsonl"

    if not scenario_path.exists():
        raise EvaluationIOError(f"Scenario metadata not found: {scenario_path}")

    try:
        with scenario_path.open("r", encoding="utf-8") as f:
            scenario = Scenario.model_validate(json.load(f))
    except Exception as exc:
        raise EvaluationIOError(f"Failed to load scenario from {scenario_path}: {exc}") from exc

    events = load_event_plan(event_plan_path) if event_plan_path.exists() else []
    return RuntimePlan(scenario=scenario, events=events)


def read_scenario_id(scenario_path: str | Path) -> str:
    """Read the ``id`` field from a scenario YAML/JSON file."""
    p = Path(scenario_path)
    if not p.exists():
        raise EvaluationIOError(f"Scenario file not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        raise EvaluationIOError(f"Failed to read scenario id from {p}: {exc}") from exc

    if not isinstance(data, dict) or "id" not in data:
        raise EvaluationIOError(f"Scenario file missing id: {p}")
    return str(data["id"])


def resolve_plan_dir(
    scenario_path: str | Path,
    scenario_id: str | None = None,
    plan_dir_root: Path | None = None,
) -> Path:
    """Resolve the compiled plan directory for a scenario."""
    root = plan_dir_root or default_plan_dir_root()
    sid = scenario_id or read_scenario_id(scenario_path)
    return root / sid


def resolve_ground_truth_path(
    scenario_path: str | Path,
    scenario_id: str | None = None,
    ground_truth_path: Path | None = None,
    plan_dir_root: Path | None = None,
) -> Path:
    """Resolve the ground truth path for a scenario.

    If ``ground_truth_path`` is provided directly, it is returned. Otherwise the
    standard layout ``<plan_dir_root>/<scenario_id>/ground_truth.json`` is used.
    """
    if ground_truth_path is not None:
        return ground_truth_path

    plan_dir = resolve_plan_dir(scenario_path, scenario_id=scenario_id, plan_dir_root=plan_dir_root)
    gt_path = plan_dir / "ground_truth.json"
    if not gt_path.exists():
        raise EvaluationIOError(
            f"Compiled ground truth not found: {gt_path}. "
            f"Run 'eventweave eval prepare {scenario_path}' first."
        )
    return gt_path
