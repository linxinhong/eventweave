"""High-level compiler engine."""

from __future__ import annotations

from pathlib import Path

from eventweave.compiler.loader import load_scenario
from eventweave.compiler.pack_loader import PackRegistry
from eventweave.compiler.planner import ScenarioPlanner
from eventweave.compiler.rules import RuleRegistry
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario


class CompileResult:
    """Result of compiling a scenario."""

    def __init__(self, plan: RuntimePlan, warnings: list[str]) -> None:
        self.plan = plan
        self.warnings = warnings


def compile_scenario(
    scenario: Scenario,
    packs_dir: str | Path | None = None,
    seed: int | None = None,
) -> CompileResult:
    """Compile a scenario into a runtime plan with rule validation."""
    planner = ScenarioPlanner(packs_dir=packs_dir)
    plan = planner.compile(scenario, seed=seed)

    registry = RuleRegistry()
    # Load rules from packs used by the scenario.
    pack_registry = PackRegistry(packs_dir=packs_dir)
    packs = pack_registry.load_with_dependencies(scenario.domain)
    for pack in packs.values():
        registry.load_from_pack(pack.rules)

    # Load explicit scenario rules.
    registry.load_from_scenario(scenario)

    warnings = registry.validate(scenario, plan)
    return CompileResult(plan=plan, warnings=warnings)


def compile_scenario_file(
    path: str | Path,
    packs_dir: str | Path | None = None,
    seed: int | None = None,
) -> CompileResult:
    """Load and compile a scenario file."""
    scenario = load_scenario(path)
    return compile_scenario(scenario, packs_dir=packs_dir, seed=seed)
