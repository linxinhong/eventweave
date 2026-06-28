"""High-level compiler engine."""

from __future__ import annotations

from pathlib import Path

from eventweave.compiler.loader import load_scenario
from eventweave.compiler.pack_loader import PackRegistry
from eventweave.compiler.planner import ScenarioPlanner
from eventweave.compiler.rules import RuleRegistry
from eventweave.compiler.semantic_task_builder import build_semantic_tasks
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticTask


class CompileResult:
    """Result of compiling a scenario."""

    def __init__(
        self,
        plan: RuntimePlan,
        semantic_tasks: list[SemanticTask],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        self.plan = plan
        self.semantic_tasks = semantic_tasks
        self.warnings = warnings
        self.errors = errors

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def compile_scenario(
    scenario: Scenario,
    packs_dir: str | Path | None = None,
    seed: int | None = None,
) -> CompileResult:
    """Compile a scenario into a runtime plan with rule validation."""
    effective_seed = seed if seed is not None else scenario.seed
    planner = ScenarioPlanner(packs_dir=packs_dir)
    plan, planner_warnings = planner.compile(scenario, seed=effective_seed)

    semantic_tasks = build_semantic_tasks(scenario)
    _attach_semantic_refs_placeholder(plan, semantic_tasks)

    registry = RuleRegistry()
    # Load rules from packs used by the scenario.
    pack_registry = PackRegistry(packs_dir=packs_dir)
    packs = pack_registry.load_with_dependencies(scenario.domain)
    for pack in packs.values():
        registry.load_from_pack(pack.rules)

    # Load explicit scenario rules.
    registry.load_from_scenario(scenario)

    rule_warnings = registry.validate(scenario, plan)
    all_warnings = planner_warnings + rule_warnings
    return CompileResult(
        plan=plan,
        semantic_tasks=semantic_tasks,
        warnings=all_warnings,
        errors=[],
    )


def compile_scenario_file(
    path: str | Path,
    packs_dir: str | Path | None = None,
    seed: int | None = None,
) -> CompileResult:
    """Load and compile a scenario file."""
    scenario = load_scenario(path)
    return compile_scenario(scenario, packs_dir=packs_dir, seed=seed)


def compile_scenario_strict(
    scenario: Scenario,
    packs_dir: str | Path | None = None,
    seed: int | None = None,
) -> CompileResult:
    """Compile a scenario in strict mode: rule violations become errors."""
    result = compile_scenario(scenario, packs_dir=packs_dir, seed=seed)
    if result.warnings:
        result.errors.extend(result.warnings)
        result.warnings = []
    return result


def compile_scenario_file_strict(
    path: str | Path,
    packs_dir: str | Path | None = None,
    seed: int | None = None,
) -> CompileResult:
    """Load and compile a scenario file in strict mode."""
    scenario = load_scenario(path)
    return compile_scenario_strict(scenario, packs_dir=packs_dir, seed=seed)


def _attach_semantic_refs_placeholder(
    plan: RuntimePlan,
    semantic_tasks: list[SemanticTask],
) -> None:
    """Attach placeholder semantic_refs to events based on matching tasks.

    This is a compile-time placeholder. Actual asset ids are injected after
    the semantic sidecar generates the asset pool.
    """
    tasks_by_event_type: dict[str, list[SemanticTask]] = {}
    for task in semantic_tasks:
        if task.valid_for:
            for event_type in task.valid_for:
                tasks_by_event_type.setdefault(event_type, []).append(task)
        else:
            # Tasks valid for all events.
            tasks_by_event_type.setdefault("*", []).append(task)

    for event in plan.events:
        refs: set[str] = set(event.semantic_refs)
        for task in tasks_by_event_type.get(event.event_type, []):
            refs.add(f"semantic://{task.id}")
        for task in tasks_by_event_type.get("*", []):
            refs.add(f"semantic://{task.id}")
        event.semantic_refs = sorted(refs)
