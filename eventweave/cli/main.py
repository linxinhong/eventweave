"""EventWeave CLI."""

from __future__ import annotations

import typer

from eventweave.cli.commands import (
    benchmark,
    encode,
    eval,
    export,
    inspect,
    pack,
    quality,
    run,
    semantic,
    validate,
)
from eventweave.cli.commands import (
    compile as compile_cmd,
)

app = typer.Typer(
    name="eventweave",
    help="AI-assisted synthetic event stream generator.",
    no_args_is_help=True,
)

# Top-level commands
validate.register_commands(app)
compile_cmd.register_commands(app)
encode.register_commands(app)
export.register_commands(app)
inspect.register_commands(app)
run.register_commands(app)

# Sub-command groups
app.add_typer(pack.get_app())
app.add_typer(semantic.get_app())
app.add_typer(eval.get_app())
app.add_typer(benchmark.get_app())
app.add_typer(quality.get_app())

if __name__ == "__main__":
    app()
