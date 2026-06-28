"""Build semantic tasks from a scenario definition."""

from __future__ import annotations

from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticTask


def build_semantic_tasks(scenario: Scenario) -> list[SemanticTask]:
    """Extract semantic tasks from scenario-level list and timeline items."""
    tasks: list[SemanticTask] = []
    seen: set[str] = set()

    # Scenario-level semantic tasks.
    for task in scenario.semantic_tasks:
        if task.id not in seen:
            tasks.append(task)
            seen.add(task.id)

    # Inline semantic specs on timeline items.
    for idx, item in enumerate(scenario.timeline):
        if item.semantic is None:
            continue
        task_id = f"{item.id or item.event}_{idx}"
        if task_id in seen:
            continue
        task = SemanticTask(
            id=task_id,
            type=item.semantic.type,
            prompt=item.semantic.prompt,
            variables=item.semantic.variables,
            valid_for=[item.event],
            review_status=item.semantic.review_status,
        )
        tasks.append(task)
        seen.add(task_id)

    return tasks
