"""EventWeave CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from eventweave.ai.cache import SemanticCache
from eventweave.ai.provider import ProviderConfig
from eventweave.ai.resolver import SemanticResolver
from eventweave.ai.sidecar import SemanticSidecar
from eventweave.compiler import compile_scenario_file, compile_scenario_file_strict
from eventweave.compiler.loader import ScenarioLoadError
from eventweave.compiler.pack_loader import PackLoadError, PackRegistry
from eventweave.compiler.writer import PlanWriter
from eventweave.core.event import Event
from eventweave.core.ground_truth import GroundTruth
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticPool, SemanticTask
from eventweave.evaluation.agent_output import AgentOutput
from eventweave.evaluation.benchmark import Scorecard
from eventweave.evaluation.evaluator import Evaluator
from eventweave.evaluation.runner import BenchmarkRunError, load_suite, run_benchmark
from eventweave.evaluation.validator import RealismGate, SuiteValidator
from eventweave.pack.scaffold import ScaffoldError, scaffold_pack
from eventweave.quality.realism import RealismAnalyzer
from eventweave.runtime.local import LocalRuntime
from eventweave.runtime.sink import Sink
from eventweave.runtime.sinks.file import FileSink
from eventweave.runtime.sinks.http import HTTPSink
from eventweave.runtime.sinks.null import NullSink
from eventweave.runtime.sinks.stdout import StdoutSink

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

pack_app = typer.Typer(
    name="pack",
    help="List, inspect, and validate domain packs.",
)
app.add_typer(pack_app)

eval_app = typer.Typer(
    name="eval",
    help="Agent evaluation harness.",
)
app.add_typer(eval_app)

benchmark_app = typer.Typer(
    name="benchmark",
    help="Multi-scenario benchmark suites and scorecards.",
)
app.add_typer(benchmark_app)

quality_app = typer.Typer(
    name="quality",
    help="Dataset quality and realism tools.",
)
app.add_typer(quality_app)


def _get_registry(packs_dir: Path | None) -> PackRegistry:
    return PackRegistry(packs_dir=packs_dir or _find_packs_dir())


@pack_app.command("list")
def pack_list(
    packs_dir: Annotated[
        Path | None, typer.Option("--packs-dir", help="Path to packs directory.")
    ] = None,
) -> None:
    """List available domain packs."""
    registry = _get_registry(packs_dir)
    packs = registry.list_packs()

    if not packs:
        console.print("[yellow]No packs found.[/yellow]")
        return

    table = Table(title="EventWeave Packs")
    table.add_column("ID", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Name", style="green")
    table.add_column("Description", style="dim")

    for pack in packs:
        table.add_row(
            pack.id,
            pack.version,
            pack.name or "",
            pack.description or "",
        )
    console.print(table)


@pack_app.command("inspect")
def pack_inspect(
    pack_id: Annotated[str, typer.Argument(help="Pack identifier.")],
    packs_dir: Annotated[
        Path | None, typer.Option("--packs-dir", help="Path to packs directory.")
    ] = None,
) -> None:
    """Inspect a domain pack."""
    registry = _get_registry(packs_dir)
    try:
        pack = registry.load(pack_id)
    except PackLoadError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Pack: {pack.id}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("ID", pack.id)
    table.add_row("Name", pack.name or "")
    table.add_row("Version", pack.version)
    table.add_row("Description", pack.description or "")
    table.add_row("Dependencies", ", ".join(pack.depends_on) or "none")
    table.add_row("Entities", str(len(pack.entities)))
    table.add_row("Events", str(len(pack.events)))
    table.add_row("Rules", str(len(pack.rules)))

    examples_count = 0
    if pack.examples_path:
        examples_dir = registry.packs_dir / pack_id / pack.examples_path
        if examples_dir.exists():
            examples_count = len(list(examples_dir.glob("*.yaml")))
    table.add_row("Examples", str(examples_count))

    console.print(table)


@pack_app.command("validate")
def pack_validate(
    target: Annotated[
        str,
        typer.Argument(help="Pack id or path to pack directory."),
    ],
    packs_dir: Annotated[
        Path | None, typer.Option("--packs-dir", help="Path to packs directory.")
    ] = None,
) -> None:
    """Validate a domain pack."""
    maybe_path = Path(target)
    if maybe_path.exists() and maybe_path.is_dir():
        pack_path = maybe_path.resolve()
        registry = PackRegistry(packs_dir=pack_path.parent)
        domain = pack_path.name
    else:
        registry = _get_registry(packs_dir)
        domain = target

    try:
        issues = registry.validate_pack(domain)
    except PackLoadError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    warnings = [issue for issue in issues if issue.startswith("WARNING:")]

    for issue in issues:
        if issue.startswith("ERROR:"):
            console.print(f"[red]{issue}[/red]")
        elif issue.startswith("WARNING:"):
            console.print(f"[yellow]{issue}[/yellow]")
        else:
            console.print(issue)

    if errors:
        console.print(f"[red]Validation failed with {len(errors)} error(s).[/red]")
        raise typer.Exit(code=1)

    if warnings:
        console.print(
            f"[green]Validation passed[/green] with {len(warnings)} warning(s)."
        )
    else:
        console.print("[green]Validation passed.[/green]")


@pack_app.command("scaffold")
def pack_scaffold(
    pack_id: Annotated[str, typer.Argument(help="Pack identifier.")],
    packs_dir: Annotated[
        Path | None, typer.Option("--packs-dir", help="Path to packs directory.")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite existing pack directory.")
    ] = False,
) -> None:
    """Scaffold a new domain pack."""
    target_dir = packs_dir or _find_packs_dir()
    try:
        pack_path = scaffold_pack(pack_id, target_dir, force=force)
    except ScaffoldError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print("Use --force to overwrite.")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Created pack at {pack_path}[/green]")
    console.print("Next steps:")
    console.print(f"  1. Edit {pack_path / 'pack.yaml'}")
    console.print(f"  2. Define entities in {pack_path / 'entities'}")
    console.print(f"  3. Define events in {pack_path / 'events'}")
    console.print(f"  4. Update {pack_path / 'rules.yaml'}")
    console.print(f"  5. Edit the example in {pack_path / 'examples' / 'basic.yaml'}")
    console.print(f"  6. Run: eventweave pack validate {pack_id}")


@semantic_app.command("generate")
def semantic_generate(
    plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
    provider: Annotated[
        str, typer.Option("--provider", "-p", help="Provider type (mock/template/ai).")
    ] = "mock",
    force: Annotated[bool, typer.Option("--force", help="Regenerate cached assets.")] = False,
    cache_dir: Annotated[
        Path | None,
        typer.Option("--cache-dir", help="Directory for the semantic asset cache."),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="AI API base URL (or EVENTWEAVE_AI_BASE_URL)."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model name (or EVENTWEAVE_AI_MODEL)."),
    ] = None,
    api_key_env: Annotated[
        str,
        typer.Option("--api-key-env", help="Environment variable holding the AI API key."),
    ] = "EVENTWEAVE_AI_API_KEY",
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

    provider_config = ProviderConfig(
        provider,
        base_url=base_url,
        model=model,
        api_key_env=api_key_env,
    )
    cache = SemanticCache(cache_dir or (plan_dir / ".semantic_cache"))
    sidecar = SemanticSidecar(
        scenario,
        provider=provider_config,
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


@app.command()
def run(
    plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
    sink: Annotated[
        str, typer.Option("--sink", help="Output sink: stdout, file, or null.")
    ] = "stdout",
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output path for file sink.")
    ] = Path("out/events.jsonl"),
    speed: Annotated[
        float, typer.Option("--speed", help="Time acceleration factor.")
    ] = 1.0,
    no_wait: Annotated[
        bool, typer.Option("--no-wait", help="Emit all events immediately.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Use null sink and print stats only.")
    ] = False,
    url: Annotated[
        str | None,
        typer.Option("--url", help="Target URL for http sink."),
    ] = None,
    timeout: Annotated[
        float, typer.Option("--timeout", help="HTTP request timeout in seconds.")
    ] = 5.0,
    retries: Annotated[
        int, typer.Option("--retries", help="HTTP retry attempts for transient failures.")
    ] = 0,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Maximum number of events to emit.")
    ] = None,
) -> None:
    """Run a compiled event plan through a local runtime."""
    effective_sink: Sink
    if dry_run:
        effective_sink = NullSink()
    elif sink == "file":
        effective_sink = FileSink(output)
    elif sink == "http":
        if not url:
            console.print("[red]--url is required for http sink[/red]")
            raise typer.Exit(code=1)
        effective_sink = HTTPSink(url, timeout=timeout, retries=retries)
    elif sink == "null":
        effective_sink = NullSink()
    elif sink == "stdout":
        effective_sink = StdoutSink()
    else:
        console.print(f"[red]Unsupported sink: {sink}[/red]")
        raise typer.Exit(code=1)

    runtime = LocalRuntime(
        plan_dir,
        sink=effective_sink,
        speed=speed,
        no_wait=no_wait,
        limit=limit,
    )
    stats = runtime.run()

    if stats.unresolved_refs:
        console.print(
            f"[yellow]Warning: {stats.unresolved_refs} events have unresolved refs[/yellow]"
        )

    console.print("[green]Runtime finished[/green]")
    console.print(f"Events emitted: {stats.emitted}")
    if stats.failed:
        console.print(f"[red]Events failed: {stats.failed}[/red]")
    console.print(f"Duration: {stats.duration:.3f}s")


@eval_app.command("task")
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


@eval_app.command("run")
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


@eval_app.command("validate-output")
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


@benchmark_app.command("validate")
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
    report = SuiteValidator(
        min_score=min_score,
        realism_gates=realism_gates,
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
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]Report written to {output}[/green]")

    if not report.passed:
        raise typer.Exit(code=1)


@benchmark_app.command("list")
def benchmark_list(
    suites_dir: Annotated[
        Path, typer.Option("--suites-dir", help="Directory containing benchmark suite YAML files.")
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


@benchmark_app.command("run")
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
    try:
        scorecard = run_benchmark(benchmark_suite, agent_outputs)
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


@benchmark_app.command("leaderboard")
def benchmark_leaderboard(
    scorecard_path: Annotated[Path, typer.Argument(help="Path to scorecard JSON.")],
) -> None:
    """Print a leaderboard from a scorecard JSON file."""
    if not scorecard_path.exists():
        console.print(f"[red]Scorecard not found: {scorecard_path}[/red]")
        raise typer.Exit(code=1)

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


@quality_app.command("realism")
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

    with runtime_plan_path.open("r", encoding="utf-8") as f:
        plan = RuntimePlan.model_validate(json.load(f))
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


if __name__ == "__main__":
    app()
