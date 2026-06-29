"""Pack subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from eventweave.cli.helpers import console, find_packs_dir, get_registry
from eventweave.compiler.pack_loader import PackLoadError
from eventweave.pack.scaffold import ScaffoldError, scaffold_pack


def get_app() -> typer.Typer:
    """Build the pack subcommand app."""
    app = typer.Typer(name="pack", help="List, inspect, and validate domain packs.")

    @app.command("list")
    def pack_list(
        packs_dir: Annotated[
            Path | None, typer.Option("--packs-dir", help="Path to packs directory.")
        ] = None,
    ) -> None:
        """List available domain packs."""
        registry = get_registry(packs_dir)
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

    @app.command("inspect")
    def pack_inspect(
        pack_id: Annotated[str, typer.Argument(help="Pack identifier.")],
        packs_dir: Annotated[
            Path | None, typer.Option("--packs-dir", help="Path to packs directory.")
        ] = None,
    ) -> None:
        """Inspect a domain pack."""
        registry = get_registry(packs_dir)
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
        table.add_row("Realism profiles", str(len(pack.realism_profiles)))

        examples_count = 0
        if pack.examples_path:
            examples_dir = registry.packs_dir / pack_id / pack.examples_path
            if examples_dir.exists():
                examples_count = len(list(examples_dir.glob("*.yaml")))
        table.add_row("Examples", str(examples_count))

        console.print(table)

    @app.command("validate")
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
            registry = get_registry(pack_path.parent)
            domain = pack_path.name
        else:
            registry = get_registry(packs_dir)
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

    @app.command("scaffold")
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
        target_dir = packs_dir or find_packs_dir()
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

    return app
