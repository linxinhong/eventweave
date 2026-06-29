"""Quality subcommands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from eventweave.cli.helpers import console, load_runtime_plan
from eventweave.core.ground_truth import GroundTruth
from eventweave.quality.realism import RealismAnalyzer


def get_app() -> typer.Typer:
    """Build the quality subcommand app."""
    app = typer.Typer(name="quality", help="Dataset quality and realism tools.")

    @app.command("realism")
    def quality_realism(
        plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
        output: Annotated[
            Path | None, typer.Option("--output", "-o", help="Optional JSON path for the report.")
        ] = None,
    ) -> None:
        """Generate a synthetic realism report for a compiled runtime plan."""
        runtime_plan_path = plan_dir / "runtime_plan.json"
        ground_truth_path = plan_dir / "ground_truth.json"

        if not runtime_plan_path.exists():
            console.print(f"[red]Runtime plan not found: {runtime_plan_path}[/red]")
            raise typer.Exit(code=1)

        plan = load_runtime_plan(runtime_plan_path)
        ground_truth = None
        if ground_truth_path.exists():
            with ground_truth_path.open("r", encoding="utf-8") as f:
                ground_truth = GroundTruth.model_validate(json.load(f))

        report = RealismAnalyzer(plan, ground_truth).analyze()
        console.print(report.to_text())

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
            console.print(f"[green]Report written to {output}[/green]")

    return app
