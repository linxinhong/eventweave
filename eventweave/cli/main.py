"""EventWeave CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from eventweave.ai.cache import SemanticCache
from eventweave.ai.provider import ProviderConfig
from eventweave.ai.resolver import SemanticResolver
from eventweave.ai.sidecar import SemanticSidecar
from eventweave.compiler import compile_scenario_file, compile_scenario_file_strict
from eventweave.compiler.loader import ScenarioLoadError
from eventweave.compiler.writer import PlanWriter
from eventweave.core.event import Event
from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticPool, SemanticTask

app = typer.Typer(
    name="eventweave",
    help="AI-assisted synthetic event stream generator.",
    no_args_is_help=True,
)
console = Console()


def _find_packs_dir() -> Path:
    """Locate packs directory relative to the current working directory."""
    return Path.cwd() / "packs"


def _load_scenario(path: Path) -> Scenario:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Scenario.model_validate(data)


def _load_events(path: Path) -> list[Event]:
    events: list[Event] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(Event.model_validate(json.loads(line)))
    return events


def _load_semantic_tasks(path: Path) -> list[SemanticTask]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [SemanticTask.model_validate(item) for item in data]


@app.command()
def validate(
    scenario: Annotated[Path, typer.Argument(help="Path to scenario YAML/JSON file.")],
    packs: Annotated[Path | None, typer.Option(help="Path to packs directory.")] = None,
    strict: Annotated[bool, typer.Option(help="Treat rule violations as errors.")] = False,
) -> None:
    """Validate a scenario file."""
    packs_dir = packs or _find_packs_dir()
    try:
        if strict:
            result = compile_scenario_file_strict(scenario, packs_dir=packs_dir)
        else:
            result = compile_scenario_file(scenario, packs_dir=packs_dir)
    except ScenarioLoadError as exc:
        console.print(f"[red]Load error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if result.errors:
        console.print(f"[red]Scenario {result.plan.scenario.id!r} has errors.[/red]")
        for error in result.errors:
            console.print(f"  - {error}")
        raise typer.Exit(code=1)

    console.print(f"[green]Scenario {result.plan.scenario.id!r} is valid.[/green]")
    console.print(f"Entities: {len(result.plan.entities)}")
    console.print(f"Events: {len(result.plan.events)}")
    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  - {warning}")


@app.command()
def compile(
    scenario: Annotated[Path, typer.Argument(help="Path to scenario YAML/JSON file.")],
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Output directory for runtime plan.")
    ] = Path("dist"),
    packs: Annotated[Path | None, typer.Option(help="Path to packs directory.")] = None,
    seed: Annotated[int | None, typer.Option(help="Random seed for deterministic output.")] = None,
    strict: Annotated[bool, typer.Option(help="Treat rule violations as errors.")] = False,
) -> None:
    """Compile a scenario into a runtime plan."""
    packs_dir = packs or _find_packs_dir()
    try:
        if strict:
            result = compile_scenario_file_strict(scenario, packs_dir=packs_dir, seed=seed)
        else:
            result = compile_scenario_file(scenario, packs_dir=packs_dir, seed=seed)
    except ScenarioLoadError as exc:
        console.print(f"[red]Load error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if result.errors:
        console.print(f"[red]Scenario {result.plan.scenario.id!r} has errors.[/red]")
        for error in result.errors:
            console.print(f"  - {error}")
        raise typer.Exit(code=1)

    # Use scenario id as output subdirectory.
    output_dir = output / result.plan.scenario.id
    writer = PlanWriter(output_dir)
    written = writer.write(result.plan, semantic_tasks=result.semantic_tasks)

    console.print(f"[green]Compiled {result.plan.scenario.id!r}[/green]")
    console.print(f"Output: {output_dir}")
    for name, path in written.items():
        console.print(f"  {name}: {path}")

    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  - {warning}")


@app.command()
def export(
    plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
    format: Annotated[str, typer.Option("--format", help="Export format.")] = "jsonl",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output file path.")] = Path(
        "out/events.jsonl"
    ),
) -> None:
    """Export events from a compiled runtime plan."""
    event_plan_path = plan_dir / "event_plan.jsonl"
    if not event_plan_path.exists():
        console.print(f"[red]Event plan not found: {event_plan_path}[/red]")
        raise typer.Exit(code=1)

    if format != "jsonl":
        console.print(f"[red]Unsupported export format: {format}[/red]")
        raise typer.Exit(code=1)

    # Copy canonical events to output path.
    output.parent.mkdir(parents=True, exist_ok=True)
    with event_plan_path.open("r", encoding="utf-8") as src:
        content = src.read()
    with output.open("w", encoding="utf-8") as dst:
        dst.write(content)

    console.print(f"[green]Exported {event_plan_path} -> {output}[/green]")


@app.command()
def inspect(
    plan_path: Annotated[Path, typer.Argument(help="Path to runtime_plan.json.")],
) -> None:
    """Inspect a compiled runtime plan."""
    if not plan_path.exists():
        console.print(f"[red]Runtime plan not found: {plan_path}[/red]")
        raise typer.Exit(code=1)

    with plan_path.open("r", encoding="utf-8") as f:
        plan_data = json.load(f)

    scenario = plan_data.get("scenario", {})
    table = Table(title=f"Runtime Plan: {scenario.get('id', 'unknown')}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Scenario", scenario.get("id", "unknown"))
    table.add_row("Domain", scenario.get("domain", "unknown"))
    table.add_row("Entities", str(len(plan_data.get("entities", []))))
    table.add_row("Relations", str(len(plan_data.get("relations", []))))
    table.add_row("Events", str(len(plan_data.get("events", []))))
    table.add_row("Sources", str(len(plan_data.get("sources", []))))

    console.print(table)


semantic_app = typer.Typer(
    name="semantic",
    help="Generate and inspect semantic assets.",
)
app.add_typer(semantic_app)


@semantic_app.command("generate")
def semantic_generate(
    plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
    provider: Annotated[
        str, typer.Option("--provider", "-p", help="Provider type (mock/template).")
    ] = "mock",
    force: Annotated[bool, typer.Option("--force", help="Regenerate cached assets.")] = False,
    cache_dir: Annotated[
        Path | None,
        typer.Option("--cache-dir", help="Directory for the semantic asset cache."),
    ] = None,
) -> None:
    """Generate semantic assets for a compiled runtime plan."""
    scenario_path = plan_dir / "scenario.json"
    tasks_path = plan_dir / "semantic_tasks.json"
    events_path = plan_dir / "event_plan.jsonl"

    if not scenario_path.exists():
        console.print(f"[red]Scenario not found: {scenario_path}[/red]")
        raise typer.Exit(code=1)
    if not tasks_path.exists():
        console.print(f"[red]Semantic tasks not found: {tasks_path}[/red]")
        raise typer.Exit(code=1)

    scenario = _load_scenario(scenario_path)
    tasks = _load_semantic_tasks(tasks_path)
    events = _load_events(events_path) if events_path.exists() else []

    cache = SemanticCache(cache_dir or (plan_dir / ".semantic_cache"))
    sidecar = SemanticSidecar(
        scenario,
        provider=ProviderConfig(provider),
        cache=cache,
    )
    pool = sidecar.generate_all(tasks, events=events, force=force)

    # Resolve semantic_refs placeholders to concrete asset ids and rewrite event plan.
    resolver = SemanticResolver(pool)
    resolved_events = resolver.resolve_events(events)
    stats = resolver.stats(resolved_events)

    events_path.write_text(
        "\n".join(event.model_dump_json() for event in resolved_events) + "\n",
        encoding="utf-8",
    )

    pool_path = plan_dir / "semantic_pool.json"
    pool_path.write_text(pool.model_dump_json(indent=2), encoding="utf-8")

    console.print(f"[green]Generated {len(pool.assets)} semantic assets[/green]")
    console.print(f"Resolved semantic_refs for {stats['resolved']} events")
    if stats["unresolved"]:
        console.print(
            f"[yellow]{stats['unresolved']} events still have task-level refs[/yellow]"
        )
    console.print(f"Output: {pool_path}")


@semantic_app.command("inspect")
def semantic_inspect(
    pool_path: Annotated[Path, typer.Argument(help="Path to semantic_pool.json.")],
) -> None:
    """Inspect a generated semantic asset pool."""
    if not pool_path.exists():
        console.print(f"[red]Semantic pool not found: {pool_path}[/red]")
        raise typer.Exit(code=1)

    with pool_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    pool = SemanticPool.model_validate(data)

    table = Table(title=f"Semantic Pool: {pool.scenario_id}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Scenario", pool.scenario_id)
    table.add_row("Total Assets", str(len(pool.assets)))

    by_type: dict[str, int] = {}
    for asset in pool.assets:
        by_type[asset.type] = by_type.get(asset.type, 0) + 1
    table.add_row("Types", ", ".join(f"{k}: {v}" for k, v in by_type.items()))

    console.print(table)

    for asset in pool.assets:
        console.print(f"\n[bold]{asset.id}[/bold] ({asset.type})")
        console.print(asset.text[:200] + "..." if len(asset.text) > 200 else asset.text)


if __name__ == "__main__":
    app()
