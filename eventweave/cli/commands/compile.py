"""Compile command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eventweave.cli.helpers import console, find_packs_dir
from eventweave.compiler import compile_scenario_file, compile_scenario_file_strict
from eventweave.compiler.loader import ScenarioLoadError
from eventweave.compiler.writer import PlanWriter


def register_commands(app: typer.Typer) -> None:
    """Register the compile command."""

    @app.command()
    def compile(
        scenario: Annotated[Path, typer.Argument(help="Path to scenario YAML/JSON file.")],
        output: Annotated[
            Path, typer.Option("-o", "--output", help="Output directory for runtime plan.")
        ] = Path("dist"),
        packs: Annotated[Path | None, typer.Option(help="Path to packs directory.")] = None,
        seed: Annotated[
            int | None, typer.Option(help="Random seed for deterministic output.")
        ] = None,
        strict: Annotated[bool, typer.Option(help="Treat rule violations as errors.")] = False,
        strict_schema: Annotated[
            bool, typer.Option("--strict-schema", help="Treat schema violations as errors.")
        ] = False,
        force: Annotated[
            bool, typer.Option(help="Overwrite a non-empty output directory.")
        ] = False,
    ) -> None:
        """Compile a scenario into a runtime plan."""
        packs_dir = packs or find_packs_dir()
        try:
            if strict:
                result = compile_scenario_file_strict(
                    scenario, packs_dir=packs_dir, seed=seed, strict_schema=strict_schema
                )
            else:
                result = compile_scenario_file(
                    scenario, packs_dir=packs_dir, seed=seed, strict_schema=strict_schema
                )
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
        allowed_root = output.resolve().parent if output.is_absolute() else Path.cwd()
        writer = PlanWriter(output_dir, force=force, allowed_root=allowed_root)
        written = writer.write(result.plan, semantic_tasks=result.semantic_tasks)

        console.print(f"[green]Compiled {result.plan.scenario.id!r}[/green]")
        console.print(f"Output: {output_dir}")
        for name, path in written.items():
            console.print(f"  {name}: {path}")

        if result.warnings:
            console.print("[yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  - {warning}")
