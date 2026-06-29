"""Validate command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eventweave.cli.helpers import console, find_packs_dir
from eventweave.compiler import compile_scenario_file, compile_scenario_file_strict
from eventweave.compiler.loader import ScenarioLoadError


def register_commands(app: typer.Typer) -> None:
    """Register the validate command."""

    @app.command()
    def validate(
        scenario: Annotated[Path, typer.Argument(help="Path to scenario YAML/JSON file.")],
        packs: Annotated[Path | None, typer.Option(help="Path to packs directory.")] = None,
        strict: Annotated[bool, typer.Option(help="Treat rule violations as errors.")] = False,
    ) -> None:
        """Validate a scenario file."""
        packs_dir = packs or find_packs_dir()
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
