"""Shared helpers for the EventWeave CLI."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from eventweave.compiler.pack_loader import PackRegistry
from eventweave.core.event import Event
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticPool, SemanticTask

console = Console()


def find_packs_dir() -> Path:
    """Locate packs directory relative to the current working directory."""
    return Path.cwd() / "packs"


def load_scenario(path: Path) -> Scenario:
    """Load a scenario JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Scenario.model_validate(data)


def load_events(path: Path) -> list[Event]:
    """Load a JSONL event plan."""
    events: list[Event] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(Event.model_validate(json.loads(line)))
    return events


def load_semantic_tasks(path: Path) -> list[SemanticTask]:
    """Load semantic tasks from a JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [SemanticTask.model_validate(item) for item in data]


def get_registry(packs_dir: Path | None) -> PackRegistry:
    """Build a pack registry for the given or default packs directory."""
    return PackRegistry(packs_dir=packs_dir or find_packs_dir())


def load_runtime_plan(path: Path) -> RuntimePlan:
    """Load a runtime plan JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return RuntimePlan.model_validate(json.load(f))


def load_semantic_pool(path: Path) -> SemanticPool:
    """Load a semantic pool JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return SemanticPool.model_validate(data)
