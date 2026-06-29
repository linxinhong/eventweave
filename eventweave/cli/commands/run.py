"""Run command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eventweave.cli.helpers import console
from eventweave.runtime.local import LocalRuntime
from eventweave.runtime.sink import Sink
from eventweave.runtime.sinks.file import FileSink
from eventweave.runtime.sinks.http import HTTPSink
from eventweave.runtime.sinks.null import NullSink
from eventweave.runtime.sinks.stdout import StdoutSink


def register_commands(app: typer.Typer) -> None:
    """Register the run command."""

    @app.command()
    def run(
        plan_dir: Annotated[Path, typer.Argument(help="Path to compiled runtime plan directory.")],
        sink: Annotated[
            str, typer.Option("--sink", help="Output sink: stdout, file, or null.")
        ] = "stdout",
        output: Annotated[
            Path, typer.Option("--output", "-o", help="Output path for file sink.")
        ] = Path("out/events.jsonl"),
        output_dir: Annotated[
            Path, typer.Option("--output-dir", help="Allowed output directory for file sink.")
        ] = Path("."),
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
        allow_internal_url: Annotated[
            bool,
            typer.Option(
                "--allow-internal-url", help="Allow http sink to send to internal/private URLs."
            ),
        ] = False,
        timeout: Annotated[
            float, typer.Option("--timeout", help="HTTP request timeout in seconds.")
        ] = 5.0,
        retries: Annotated[
            int, typer.Option("--retries", help="HTTP retry attempts for transient failures.")
        ] = 0,
        max_retry_duration: Annotated[
            float,
            typer.Option("--max-retry-duration", help="Maximum total retry duration in seconds."),
        ] = 30.0,
        backoff_factor: Annotated[
            float, typer.Option("--backoff-factor", help="Base multiplier for exponential backoff.")
        ] = 1.0,
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
            effective_sink = FileSink(output, output_dir=output_dir)
        elif sink == "http":
            if not url:
                console.print("[red]--url is required for http sink[/red]")
                raise typer.Exit(code=1)
            try:
                effective_sink = HTTPSink(
                    url,
                    timeout=timeout,
                    retries=retries,
                    max_retry_duration=max_retry_duration,
                    backoff_factor=backoff_factor,
                    allow_internal=allow_internal_url,
                )
            except ValueError as exc:
                console.print(f"[red]Invalid http sink URL: {exc}[/red]")
                raise typer.Exit(code=1) from exc
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
