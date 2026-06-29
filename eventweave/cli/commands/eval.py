"""Eval subcommands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.table import Table

from eventweave.cli.helpers import console, find_packs_dir
from eventweave.compiler import compile_scenario_file
from eventweave.compiler.loader import ScenarioLoadError
from eventweave.compiler.writer import PlanWriter
from eventweave.core.ground_truth import GroundTruth
from eventweave.evaluation.agent_output import AgentOutput
from eventweave.evaluation.evaluator import Evaluator


def get_app() -> typer.Typer:
    """Build the eval subcommand app."""
    app = typer.Typer(name="eval", help="Agent evaluation harness.")

    @app.command("prepare")
    def eval_prepare(
        scenario: Annotated[Path, typer.Argument(help="Path to scenario YAML/JSON file.")],
        output: Annotated[
            Path, typer.Option("-o", "--output", help="Output directory for compiled plan.")
        ] = Path("dist"),
        packs: Annotated[
            Path | None, typer.Option(help="Path to packs directory.")
        ] = None,
        seed: Annotated[
            int | None, typer.Option(help="Random seed for deterministic output.")
        ] = None,
        force: Annotated[
            bool, typer.Option(help="Overwrite a non-empty output directory.")
        ] = False,
    ) -> None:
        """Compile a scenario so that eval/benchmark can use the artifacts."""
        packs_dir = packs or find_packs_dir()
        try:
            result = compile_scenario_file(scenario, packs_dir=packs_dir, seed=seed)
        except ScenarioLoadError as exc:
            console.print(f"[red]Load error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        if result.errors:
            console.print(f"[red]Scenario {result.plan.scenario.id!r} has errors.[/red]")
            for error in result.errors:
                console.print(f"  - {error}")
            raise typer.Exit(code=1)

        output_dir = output / result.plan.scenario.id
        allowed_root = output.resolve().parent if output.is_absolute() else Path.cwd()
        writer = PlanWriter(output_dir, force=force, allowed_root=allowed_root)
        writer.write(result.plan, semantic_tasks=result.semantic_tasks)

        console.print(
            f"[green]Prepared evaluation artifacts for {result.plan.scenario.id!r}[/green]"
        )
        console.print(f"Ground truth: {output_dir / 'ground_truth.json'}")

    @app.command("task")
    def eval_task(
        plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
        output: Annotated[
            Path | None,
            typer.Option("-o", "--output", help="Output path for the evaluation task file."),
        ] = None,
    ) -> None:
        """Generate an agent evaluation task from a compiled runtime plan."""
        scenario_path = plan_dir / "scenario.json"
        ground_truth_path = plan_dir / "ground_truth.json"
        event_plan_path = plan_dir / "event_plan.jsonl"

        if not scenario_path.exists():
            console.print(f"[red]Scenario not found: {scenario_path}[/red]")
            raise typer.Exit(code=1)
        if not ground_truth_path.exists():
            console.print(
                f"[red]Ground truth not found: {ground_truth_path}. "
                "Declare ground_truth in the scenario and recompile.[/red]"
            )
            raise typer.Exit(code=1)
        if not event_plan_path.exists():
            console.print(f"[red]Event plan not found: {event_plan_path}[/red]")
            raise typer.Exit(code=1)

        with scenario_path.open("r", encoding="utf-8") as f:
            scenario_data = json.load(f)

        scenario_id = scenario_data.get("id", "unknown")
        scenario_name = scenario_data.get("name", scenario_id)
        scenario_summary = scenario_data.get("description", "")

        task_output = output or (plan_dir / "eval" / "task.json")
        task_output.parent.mkdir(parents=True, exist_ok=True)

        task = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "scenario_summary": scenario_summary,
            "instructions": (
                "Analyze the provided event stream and produce a structured report. "
                "Identify key security findings, the entities involved, the attack or "
                "business-flow stage each finding belongs to, and the event IDs that "
                "support each finding. Return your output in the AgentOutput JSON schema."
            ),
            "event_plan": str(event_plan_path),
            "ground_truth_path": str(ground_truth_path),
            "output_schema": {
                "format": "agent_output",
                "description": "EventWeave AgentOutput schema",
                "required_fields": [
                    "scenario_id",
                    "findings",
                    "key_event_ids",
                    "timeline_stages",
                    "summary",
                ],
                "finding_fields": [
                    "type",
                    "entities",
                    "stage",
                    "evidence_event_ids",
                    "confidence",
                    "attributes",
                ],
            },
        }

        task_output.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Evaluation task written to {task_output}[/green]")

    @app.command("run")
    def eval_run(
        ground_truth: Annotated[
            Path, typer.Option("--ground-truth", help="Path to ground_truth.json.")
        ],
        agent_output: Annotated[
            Path, typer.Option("--agent-output", help="Path to agent output JSON.")
        ],
        output: Annotated[
            Path, typer.Option("--output", "-o", help="Output path for the evaluation report.")
        ] = Path("eval_report.json"),
    ) -> None:
        """Evaluate an agent output against ground truth."""
        if not ground_truth.exists():
            console.print(f"[red]Ground truth not found: {ground_truth}[/red]")
            raise typer.Exit(code=1)
        if not agent_output.exists():
            console.print(f"[red]Agent output not found: {agent_output}[/red]")
            raise typer.Exit(code=1)

        with ground_truth.open("r", encoding="utf-8") as f:
            gt = GroundTruth.model_validate(json.load(f))
        with agent_output.open("r", encoding="utf-8") as f:
            ao = AgentOutput.model_validate(json.load(f))

        if ao.scenario_id != gt.scenario_id:
            console.print(
                f"[yellow]Warning: scenario_id mismatch "
                f"(agent={ao.scenario_id}, ground_truth={gt.scenario_id})[/yellow]"
            )

        report = Evaluator(gt, ao).evaluate()

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        table = Table(title=f"Evaluation Report: {report.scenario_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        for name, value in report.metrics.items():
            table.add_row(name, f"{value:.2f}")
        console.print(table)
        console.print(f"[green]Report written to {output}[/green]")

    @app.command("validate-output")
    def eval_validate_output(
        path: Annotated[Path, typer.Argument(help="Path to agent output JSON.")],
    ) -> None:
        """Validate an agent output JSON file against the AgentOutput schema."""
        if not path.exists():
            console.print(f"[red]Agent output not found: {path}[/red]")
            raise typer.Exit(code=1)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            AgentOutput.model_validate(data)
        except ValidationError as exc:
            console.print(f"[red]Invalid agent output:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[green]Valid agent output: {path}[/green]")

    return app
