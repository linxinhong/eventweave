"""Semantic subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from eventweave.ai.cache import SemanticCache
from eventweave.ai.provider import ProviderConfig
from eventweave.ai.resolver import SemanticResolver
from eventweave.ai.sidecar import SemanticSidecar
from eventweave.cli.helpers import (
    console,
    load_events,
    load_scenario,
    load_semantic_tasks,
)
from eventweave.core.semantic import SemanticPool


def get_app() -> typer.Typer:
    """Build the semantic subcommand app."""
    app = typer.Typer(name="semantic", help="Generate and inspect semantic assets.")

    @app.command("generate")
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
            str | None, typer.Option("--model", help="AI model name (or EVENTWEAVE_AI_MODEL).")
        ] = None,
        api_key_env: Annotated[
            str,
            typer.Option("--api-key-env", help="Environment variable holding the AI API key."),
        ] = "EVENTWEAVE_AI_API_KEY",
        timeout: Annotated[
            float | None,
            typer.Option("--timeout", help="HTTP timeout in seconds for AI requests."),
        ] = None,
        max_retries: Annotated[
            int | None,
            typer.Option("--max-retries", help="Maximum retries for transient AI failures."),
        ] = None,
        max_tokens: Annotated[
            int | None,
            typer.Option("--max-tokens", help="Maximum tokens per AI response."),
        ] = None,
        temperature: Annotated[
            float | None,
            typer.Option("--temperature", help="Sampling temperature for AI requests."),
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

        scenario = load_scenario(scenario_path)
        tasks = load_semantic_tasks(tasks_path)
        events = load_events(events_path) if events_path.exists() else []

        provider_config = ProviderConfig(
            provider,
            base_url=base_url,
            model=model,
            api_key_env=api_key_env,
            timeout=timeout,
            max_retries=max_retries,
            max_tokens=max_tokens,
            temperature=temperature,
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

    @app.command("inspect")
    def semantic_inspect(
        pool_path: Annotated[Path, typer.Argument(help="Path to semantic_pool.json.")],
    ) -> None:
        """Inspect a generated semantic asset pool."""
        if not pool_path.exists():
            console.print(f"[red]Semantic pool not found: {pool_path}[/red]")
            raise typer.Exit(code=1)

        import json

        with pool_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        pool = load_semantic_pool(data)

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

    return app


def load_semantic_pool(data: object) -> SemanticPool:
    """Load a SemanticPool from parsed JSON (kept here to avoid circular imports)."""
    return SemanticPool.model_validate(data)
