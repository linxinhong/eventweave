"""Encode command group: run, inspect, preflight."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from eventweave.cli.helpers import console
from eventweave.core.event import Event
from eventweave.encoders import GO_ENCODER_NAMES
from eventweave.encoders.registry import get_encoder, list_encoders
from eventweave.runtime.sinks.file import _resolve_within_output_dir


def get_app() -> typer.Typer:
    """Build the encode subcommand app."""
    app = typer.Typer(name="encode", help="Encode events to vendor/log formats.")

    @app.command("run")
    def encode_run(
        plan_dir: Annotated[
            Path, typer.Argument(help="Path to compiled runtime plan directory.")
        ],
        encoder: Annotated[
            str,
            typer.Option(
                "--encoder", "-e", help="Encoder name (e.g. syslog-rfc3164, nginx-access)."
            ),
        ],
        output: Annotated[
            Path, typer.Option("--output", "-o", help="Output file path.")
        ] = Path("out/encoded.log"),
        output_dir: Annotated[
            Path, typer.Option("--output-dir", help="Allowed output directory for file paths.")
        ] = Path("."),
        skip_failed: Annotated[
            bool, typer.Option("--skip-failed", help="Skip events that fail to encode.")
        ] = False,
    ) -> None:
        """Encode events from a compiled runtime plan to a vendor/log format."""
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

    @app.command("inspect")
    def encode_inspect(
        encoder_name: Annotated[str, typer.Argument(help="Encoder name.")],
    ) -> None:
        """Show encoder metadata and required fields."""
        try:
            enc = get_encoder(encoder_name)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

        info = enc.get_info()
        available_in = ["python"]
        if info["name"] in GO_ENCODER_NAMES:
            available_in.append("go")

        table = Table(title=f"Encoder: {info['name']}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Name", info["name"])
        table.add_row("Content-Type", info["content_type"])
        table.add_row("Description", info["description"] or "-")
        table.add_row("Required fields", ", ".join(info["required_fields"]) or "none")
        table.add_row("Optional fields", ", ".join(info["optional_fields"]) or "none")
        table.add_row(
            "Supported event types", ", ".join(info["supported_event_types"]) or "any"
        )
        table.add_row("Available in", ", ".join(available_in))

        console.print(table)

    @app.command("preflight")
    def encode_preflight(
        plan_dir: Annotated[
            Path, typer.Argument(help="Path to compiled runtime plan directory.")
        ],
        encoder: Annotated[
            str,
            typer.Option(
                "--encoder", "-e", help="Encoder name (e.g. syslog-rfc3164, nginx-access)."
            ),
        ],
    ) -> None:
        """Check how many events in a plan can be encoded by the given encoder."""
        try:
            enc = get_encoder(encoder)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

        event_plan_path = plan_dir / "event_plan.jsonl"
        if not event_plan_path.exists():
            console.print(f"[red]Event plan not found: {event_plan_path}[/red]")
            raise typer.Exit(code=1)

        total = 0
        success = 0
        failures_by_type: Counter[str] = Counter()
        missing_fields: Counter[str] = Counter()
        sample_reasons: dict[str, str] = {}

        with event_plan_path.open("r", encoding="utf-8") as src:
            for line in src:
                line = line.strip()
                if not line:
                    continue
                event = Event.model_validate_json(line)
                total += 1
                result = enc.encode(event)
                if result.success:
                    success += 1
                    continue

                failures_by_type[event.event_type] += 1
                if event.event_type not in sample_reasons:
                    sample_reasons[event.event_type] = result.error_reason or "unknown"
                if (
                    result.error_reason
                    and result.error_reason.startswith("missing required fields:")
                ):
                    fields_part = result.error_reason.split(":", 1)[1]
                    for field in fields_part.split(","):
                        missing_fields[field.strip()] += 1

        failed = total - success
        percentage = (success / total * 100) if total else 0.0

        summary = Table(title=f"Preflight: {encoder}")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="magenta")
        summary.add_row("Total events", str(total))
        summary.add_row("Encodable", str(success))
        summary.add_row("Failed", str(failed))
        summary.add_row("Encodable %", f"{percentage:.1f}%")
        console.print(summary)

        if failures_by_type:
            by_type_table = Table(title="Failures by event type")
            by_type_table.add_column("Event type", style="cyan")
            by_type_table.add_column("Count", style="magenta")
            by_type_table.add_column("Sample reason", style="dim")
            for event_type, count in failures_by_type.most_common():
                by_type_table.add_row(event_type, str(count), sample_reasons.get(event_type, ""))
            console.print(by_type_table)

        if missing_fields:
            missing_table = Table(title="Missing required fields")
            missing_table.add_column("Field", style="cyan")
            missing_table.add_column("Count", style="magenta")
            for field, count in missing_fields.most_common():
                missing_table.add_row(field, str(count))
            console.print(missing_table)

        if failed:
            raise typer.Exit(code=1)

    @app.command("list")
    def encode_list() -> None:
        """List available encoders."""
        for name in list_encoders():
            console.print(name)

    return app


def register_commands(app: typer.Typer) -> None:
    """Register the encode command group (kept for compatibility with main.py)."""
    app.add_typer(get_app())
