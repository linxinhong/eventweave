"""Encode command: convert canonical events to vendor/log formats."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eventweave.cli.helpers import console
from eventweave.core.event import Event
from eventweave.encoders.registry import get_encoder, list_encoders
from eventweave.runtime.sinks.file import _resolve_within_output_dir


def register_commands(app: typer.Typer) -> None:
    """Register the encode command."""

    @app.command()
    def encode(
        plan_dir: Annotated[
            Path | None, typer.Argument(help="Path to compiled runtime plan directory.")
        ] = None,
        encoder: Annotated[
            str | None,
            typer.Option(
                "--encoder", "-e", help="Encoder name (e.g. syslog-rfc3164, nginx-access)."
            ),
        ] = None,
        output: Annotated[
            Path, typer.Option("--output", "-o", help="Output file path.")
        ] = Path("out/encoded.log"),
        output_dir: Annotated[
            Path, typer.Option("--output-dir", help="Allowed output directory for file paths.")
        ] = Path("."),
        list_encoders_flag: Annotated[
            bool, typer.Option("--list", help="List available encoders and exit.")
        ] = False,
        skip_failed: Annotated[
            bool, typer.Option("--skip-failed", help="Skip events that fail to encode.")
        ] = False,
    ) -> None:
        """Encode events from a compiled runtime plan to a vendor/log format."""
        if list_encoders_flag:
            for name in list_encoders():
                console.print(name)
            return

        if plan_dir is None:
            console.print("[red]Missing argument 'PLAN_DIR'[/red]")
            raise typer.Exit(code=1)

        if encoder is None:
            console.print("[red]--encoder is required (use --list to see options)[/red]")
            raise typer.Exit(code=1)

        try:
            enc = get_encoder(encoder)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

        event_plan_path = plan_dir / "event_plan.jsonl"
        if not event_plan_path.exists():
            console.print(f"[red]Event plan not found: {event_plan_path}[/red]")
            raise typer.Exit(code=1)

        safe_output = _resolve_within_output_dir(output, output_dir)
        safe_output.parent.mkdir(parents=True, exist_ok=True)

        encoded = 0
        failed = 0
        with event_plan_path.open("r", encoding="utf-8") as src, safe_output.open(
            "w", encoding="utf-8"
        ) as dst:
            for line in src:
                line = line.strip()
                if not line:
                    continue
                event = Event.model_validate_json(line)
                result = enc.encode(event)
                if not result.success:
                    failed += 1
                    if not skip_failed:
                        console.print(
                            f"[red]Encode failed for {event.event_id}: {result.error_reason}[/red]"
                        )
                        raise typer.Exit(code=1)
                    console.print(
                        f"[yellow]Skipped {event.event_id}: {result.error_reason}[/yellow]"
                    )
                    continue
                dst.write(result.output + "\n")
                encoded += 1

        console.print(
            f"[green]Encoded {encoded} events -> {safe_output} ({failed} failed)[/green]"
        )
