"""Encode command group: run, inspect, preflight."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from eventweave.cli.helpers import console
from eventweave.core.event import Event
from eventweave.encoders import GO_ENCODER_NAMES
from eventweave.encoders.base import Encoder
from eventweave.encoders.enrichment import (
    EnrichmentProfile,
    enrich_event,
    get_enrichment_profile,
)
from eventweave.encoders.registry import get_encoder, list_encoders
from eventweave.runtime.sinks.file import _resolve_within_output_dir


@dataclass
class PreflightResult:
    """Aggregated preflight statistics."""

    total: int = 0
    success: int = 0
    failures_by_type: Counter[str] = field(default_factory=Counter)
    missing_fields: Counter[str] = field(default_factory=Counter)
    sample_reasons: dict[str, str] = field(default_factory=dict)

    @property
    def failed(self) -> int:
        return self.total - self.success

    @property
    def percentage(self) -> float:
        return (self.success / self.total * 100) if self.total else 0.0


def _run_preflight(
    event_plan_path: Path, encoder: Encoder, profile: EnrichmentProfile | None
) -> PreflightResult:
    """Run preflight against the event plan."""
    result = PreflightResult()
    with event_plan_path.open("r", encoding="utf-8") as src:
        for line in src:
            line = line.strip()
            if not line:
                continue
            event = Event.model_validate_json(line)
            result.total += 1
            if profile is not None:
                event = enrich_event(event, profile)
            encoded = encoder.encode(event)
            if encoded.success:
                result.success += 1
                continue

            result.failures_by_type[event.event_type] += 1
            if event.event_type not in result.sample_reasons:
                reason = encoded.error_reason or "unknown"
                result.sample_reasons[event.event_type] = reason
            if (
                encoded.error_reason
                and encoded.error_reason.startswith("missing required fields:")
            ):
                fields_part = encoded.error_reason.split(":", 1)[1]
                for fld in fields_part.split(","):
                    result.missing_fields[fld.strip()] += 1
    return result


def _print_preflight(result: PreflightResult, encoder: str, title_suffix: str = "") -> None:
    title = f"Preflight: {encoder}"
    if title_suffix:
        title = f"{title} ({title_suffix})"
    summary = Table(title=title)
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value", style="magenta")
    summary.add_row("Total events", str(result.total))
    summary.add_row("Encodable", str(result.success))
    summary.add_row("Failed", str(result.failed))
    summary.add_row("Encodable %", f"{result.percentage:.1f}%")
    console.print(summary)

    if result.failures_by_type:
        by_type_table = Table(title="Failures by event type")
        by_type_table.add_column("Event type", style="cyan")
        by_type_table.add_column("Count", style="magenta")
        by_type_table.add_column("Sample reason", style="dim")
        for event_type, count in result.failures_by_type.most_common():
            by_type_table.add_row(
                event_type, str(count), result.sample_reasons.get(event_type, "")
            )
        console.print(by_type_table)

    if result.missing_fields:
        missing_table = Table(title="Missing required fields")
        missing_table.add_column("Field", style="cyan")
        missing_table.add_column("Count", style="magenta")
        for fld, count in result.missing_fields.most_common():
            missing_table.add_row(fld, str(count))
        console.print(missing_table)


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
        enrich: Annotated[
            bool,
            typer.Option("--enrich", help="Apply encoder enrichment profile before encoding."),
        ] = False,
    ) -> None:
        """Encode events from a compiled runtime plan to a vendor/log format."""
        try:
            enc = get_encoder(encoder)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

        profile: EnrichmentProfile | None = None
        if enrich:
            profile = get_enrichment_profile(encoder)
            if profile is None:
                console.print(
                    f"[yellow]No enrichment profile found for {encoder}; "
                    "continuing without enrichment.[/yellow]"
                )

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
                if profile is not None:
                    event = enrich_event(event, profile)
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
        enrich: Annotated[
            bool,
            typer.Option("--enrich", help="Apply encoder enrichment profile before encoding."),
        ] = False,
        compare_enrichment: Annotated[
            bool,
            typer.Option(
                "--compare-enrichment",
                help="Show before/after comparison when --enrich is used.",
            ),
        ] = False,
    ) -> None:
        """Check how many events in a plan can be encoded by the given encoder."""
        try:
            enc = get_encoder(encoder)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

        profile: EnrichmentProfile | None = None
        if enrich:
            profile = get_enrichment_profile(encoder)
            if profile is None:
                console.print(
                    f"[yellow]No enrichment profile found for {encoder}; "
                    "continuing without enrichment.[/yellow]"
                )

        event_plan_path = plan_dir / "event_plan.jsonl"
        if not event_plan_path.exists():
            console.print(f"[red]Event plan not found: {event_plan_path}[/red]")
            raise typer.Exit(code=1)

        baseline = _run_preflight(event_plan_path, enc, profile=None)
        enriched = _run_preflight(event_plan_path, enc, profile)

        show_baseline = compare_enrichment or (enrich and baseline.failed > enriched.failed)

        if show_baseline:
            _print_preflight(baseline, encoder, "without enrichment")
        _print_preflight(enriched, encoder, "with enrichment" if show_baseline else "")

        if compare_enrichment and baseline.failed != enriched.failed:
            delta_table = Table(title="Enrichment impact")
            delta_table.add_column("Metric", style="cyan")
            delta_table.add_column("Value", style="magenta")
            delta_table.add_row(
                "Encodable improvement",
                (
                    f"{enriched.success - baseline.success} "
                    f"({baseline.percentage:.1f}% -> {enriched.percentage:.1f}%)"
                ),
            )
            delta_table.add_row(
                "Failed reduction",
                str(baseline.failed - enriched.failed),
            )
            console.print(delta_table)

        if enriched.failed:
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
