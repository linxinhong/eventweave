"""Export command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eventweave.cli.helpers import console
from eventweave.core.event import Event
from eventweave.encoders.registry import get_encoder
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
        encoder: Annotated[
            str | None,
            typer.Option("--encoder", "-e", help="Encode events with this encoder."),
        ] = None,
    ) -> None:
        """Export events from a compiled runtime plan."""
        event_plan_path = plan_dir / "event_plan.jsonl"
        if not event_plan_path.exists():
            console.print(f"[red]Event plan not found: {event_plan_path}[/red]")
            raise typer.Exit(code=1)

        if format != "jsonl":
            console.print(f"[red]Unsupported export format: {format}[/red]")
            raise typer.Exit(code=1)

        safe_output = _resolve_within_output_dir(output, output_dir)
        safe_output.parent.mkdir(parents=True, exist_ok=True)

        enc = None
        if encoder is not None:
            try:
                enc = get_encoder(encoder)
            except KeyError as exc:
                console.print(f"[red]{exc}[/red]")
                raise typer.Exit(code=1) from exc

        with event_plan_path.open("r", encoding="utf-8") as src, safe_output.open(
            "w", encoding="utf-8"
        ) as dst:
            for line in src:
                line = line.strip()
                if not line:
                    continue
                if enc is None:
                    dst.write(line + "\n")
                    continue
                event = Event.model_validate_json(line)
                result = enc.encode(event)
                if not result.success:
                    console.print(
                        f"[red]Encode failed for {event.event_id}: {result.error_reason}[/red]"
                    )
                    raise typer.Exit(code=1)
                dst.write(result.output + "\n")

        console.print(f"[green]Exported {event_plan_path} -> {safe_output}[/green]")
