"""Benchmark subcommands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from eventweave.cli.helpers import console
from eventweave.evaluation.benchmark import Scorecard
from eventweave.evaluation.runner import (
    BenchmarkRunError,
    load_suite,
    run_benchmark,
)
from eventweave.evaluation.validator import RealismGate, SuiteValidator


def get_app() -> typer.Typer:
    """Build the benchmark subcommand app."""
    app = typer.Typer(name="benchmark", help="Multi-scenario benchmark suites and scorecards.")

    @app.command("validate")
    def benchmark_validate(
        suite: Annotated[
            Path, typer.Option("--suite", help="Path to benchmark suite YAML file.")
        ],
        min_score: Annotated[
            float,
            typer.Option("--min-score", help="Minimum required sample overall_score."),
        ] = 1.0,
        min_noise_ratio: Annotated[
            float | None,
            typer.Option("--min-noise-ratio", help="Minimum noise events per key event."),
        ] = None,
        min_event_types: Annotated[
            int | None,
            typer.Option("--min-event-types", help="Minimum distinct event types."),
        ] = None,
        min_sources: Annotated[
            int | None,
            typer.Option("--min-sources", help="Minimum distinct source ids."),
        ] = None,
        max_burstiness: Annotated[
            float | None,
            typer.Option("--max-burstiness", help="Maximum allowed burstiness score."),
        ] = None,
        require_jitter: Annotated[
            bool,
            typer.Option("--require-jitter", help="Require scenario-level jitter to be enabled."),
        ] = False,
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Optional JSON path for validation report."),
        ] = None,
    ) -> None:
        """Validate a benchmark suite and its sample data."""
        if not suite.exists():
            console.print(f"[red]Suite not found: {suite}[/red]")
            raise typer.Exit(code=1)

        realism_gates = RealismGate(
            min_noise_ratio=min_noise_ratio,
            min_event_types=min_event_types,
            min_sources=min_sources,
            max_burstiness=max_burstiness,
            require_jitter=require_jitter,
        )
        plan_dir_root = Path(os.environ.get("EVENTWEAVE_PLAN_DIR", "dist"))
        report = SuiteValidator(
            min_score=min_score,
            realism_gates=realism_gates,
            plan_dir_root=plan_dir_root,
        ).validate(suite)

        status = "[green]passed[/green]" if report.passed else "[red]failed[/red]"
        console.print(f"Validation for [cyan]{report.suite_id}[/cyan]: {status}")

        table = Table(title=f"Validation Checks: {report.suite_id}")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Message", style="dim")
        for check in report.checks:
            status_text = "[green]PASS[/green]" if check.passed else "[red]FAIL[/red]"
            table.add_row(check.name, status_text, check.message)
        console.print(table)

        if output:
            import json

            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
            console.print(f"[green]Report written to {output}[/green]")

        if not report.passed:
            raise typer.Exit(code=1)

    @app.command("list")
    def benchmark_list(
        suites_dir: Annotated[
            Path,
            typer.Option("--suites-dir", help="Directory containing benchmark suite YAML files."),
        ] = Path("benchmarks"),
    ) -> None:
        """List available benchmark suites."""
        if not suites_dir.exists():
            console.print(f"[red]Benchmark suites directory not found: {suites_dir}[/red]")
            raise typer.Exit(code=1)

        suites: list[tuple[str, str, Path]] = []
        for path in sorted(suites_dir.glob("*.yaml")):
            try:
                suite = load_suite(path)
                suites.append((suite.id, suite.name or "", path))
            except Exception as exc:  # noqa: BLE001
                console.print(f"[yellow]Skipping {path}: {exc}[/yellow]")

        if not suites:
            console.print("[yellow]No benchmark suites found.[/yellow]")
            return

        table = Table(title="Benchmark Suites")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Path", style="dim")
        for suite_id, name, path in suites:
            table.add_row(suite_id, name, str(path))
        console.print(table)

    @app.command("run")
    def benchmark_run(
        suite: Annotated[
            Path, typer.Option("--suite", help="Path to benchmark suite YAML file.")
        ],
        agent_outputs: Annotated[
            list[Path],
            typer.Option("--agent-outputs", help="One or more agent output directories."),
        ],
        output: Annotated[
            Path, typer.Option("--output", "-o", help="Output path for the scorecard JSON.")
        ] = Path("scorecard.json"),
    ) -> None:
        """Run a benchmark suite against one or more agent output directories."""
        if not suite.exists():
            console.print(f"[red]Suite not found: {suite}[/red]")
            raise typer.Exit(code=1)

        missing_dirs = [d for d in agent_outputs if not d.exists()]
        if missing_dirs:
            dirs = ", ".join(str(d) for d in missing_dirs)
            console.print(f"[red]Agent output directories not found: {dirs}[/red]")
            raise typer.Exit(code=1)

        benchmark_suite = load_suite(suite)
        plan_dir_root = Path(os.environ.get("EVENTWEAVE_PLAN_DIR", "dist"))
        try:
            scorecard = run_benchmark(benchmark_suite, agent_outputs, plan_dir_root=plan_dir_root)
        except BenchmarkRunError as exc:
            console.print(f"[red]Benchmark run failed:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(scorecard.model_dump_json(indent=2), encoding="utf-8")

        table = Table(title=f"Benchmark Scorecard: {scorecard.suite.id}")
        table.add_column("Agent", style="cyan")
        table.add_column("Overall", style="magenta")
        table.add_column("Balanced", style="magenta")
        for result in scorecard.results:
            table.add_row(
                result.agent_name,
                f"{result.aggregate.get('overall_score', 0.0):.2f}",
                f"{result.aggregate.get('balanced_score', 0.0):.2f}",
            )
        console.print(table)
        console.print(f"Ranking: {', '.join(scorecard.ranking)}")
        console.print(f"[green]Scorecard written to {output}[/green]")

    @app.command("leaderboard")
    def benchmark_leaderboard(
        scorecard_path: Annotated[Path, typer.Argument(help="Path to scorecard JSON.")],
    ) -> None:
        """Print a leaderboard from a scorecard JSON file."""
        if not scorecard_path.exists():
            console.print(f"[red]Scorecard not found: {scorecard_path}[/red]")
            raise typer.Exit(code=1)

        import json

        with scorecard_path.open("r", encoding="utf-8") as f:
            scorecard = Scorecard.model_validate(json.load(f))

        table = Table(title=f"Leaderboard: {scorecard.suite.id}")
        table.add_column("Rank", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Overall", style="magenta")
        table.add_column("Balanced", style="magenta")

        results_by_name = {r.agent_name: r for r in scorecard.results}
        for rank, agent_name in enumerate(scorecard.ranking, start=1):
            result = results_by_name[agent_name]
            table.add_row(
                str(rank),
                agent_name,
                f"{result.aggregate.get('overall_score', 0.0):.2f}",
                f"{result.aggregate.get('balanced_score', 0.0):.2f}",
            )
        console.print(table)

    return app
