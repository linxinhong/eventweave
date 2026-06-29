"""Inspect command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from eventweave.cli.helpers import console


def register_commands(app: typer.Typer) -> None:
    """Register the inspect command."""

    @app.command()
    def inspect(
        plan_path: Annotated[Path, typer.Argument(help="Path to runtime_plan.json.")],
    ) -> None:
        """Inspect a compiled runtime plan."""
        if not plan_path.exists():
            console.print(f"[red]Runtime plan not found: {plan_path}[/red]")
            raise typer.Exit(code=1)

        import json

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
