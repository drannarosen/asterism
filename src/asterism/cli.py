"""Command-line interface for Asterism."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="asterism",
    help="Build provenance-preserving scientific EvidencePacks.",
    no_args_is_help=True,
)


@app.command()
def pack() -> None:
    """Build an EvidencePack from a local path."""
    typer.echo("Packing is not implemented yet.")
