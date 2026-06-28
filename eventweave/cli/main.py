"""EventWeave CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from eventweave.compiler import compile_scenario_file, compile_scenario_file_strict
from eventweave.compiler.loader import ScenarioLoadError
from eventweave.compiler.writer import PlanWriter

app = typer.Typer(
    name="eventweave",
    help="AI-assisted synthetic event stream generator.",
    no_args_is_help=True,
)
console = Console()


def _find_packs_dir() -> Path:
    """Locate packs directory relative to the current working directory."""
    return Path.cwd() / "packs"


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
    written = writer.write(result.plan)

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


if __name__ == "__main__":
    app()
