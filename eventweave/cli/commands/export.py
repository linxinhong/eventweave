"""Export command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eventweave.cli.helpers import console
from eventweave.runtime.sinks.file import _resolve_within_output_dir


def register_commands(app: typer.Typer) -> None:
    """Register the export command."""

    @app.command()
    def export(
        plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
        format: Annotated[str, typer.Option("--format", help="Export format.")] = "jsonl",
        output: Annotated[Path, typer.Option("--output", "-o", help="Output file path.")] = Path(
            "out/events.jsonl"
        ),
        output_dir: Annotated[
            Path, typer.Option("--output-dir", help="Allowed output directory for file paths.")
        ] = Path("."),
    ) -> None:
        """Export events from a compiled runtime plan."""
        event_plan_path = plan_dir / "event_plan.jsonl"
        if not event_plan_path.exists():
            console.print(f"[red]Event plan not found: {event_plan_path}[/red]")
            raise typer.Exit(code=1)

        if format != "jsonl":
            console.print(f"[red]Unsupported export format: {format}[/red]")
            raise typer.Exit(code=1)

        # Resolve output within the allowed directory to prevent path traversal.
        safe_output = _resolve_within_output_dir(output, output_dir)

        # Copy canonical events to output path.
        safe_output.parent.mkdir(parents=True, exist_ok=True)
        with event_plan_path.open("r", encoding="utf-8") as src:
            content = src.read()
        with safe_output.open("w", encoding="utf-8") as dst:
            dst.write(content)

        console.print(f"[green]Exported {event_plan_path} -> {safe_output}[/green]")
