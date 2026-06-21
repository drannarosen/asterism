"""Command-line interface for Asterism."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from asterism.evidence import EvidencePack
from asterism.packer import PackOptions, pack_directory
from asterism.retrieve import RetrievalKeyError, RetrievalStore

app = typer.Typer(
    name="asterism",
    help="Build provenance-preserving scientific EvidencePacks.",
    no_args_is_help=True,
)
console = Console()


@app.command("pack")
def pack_command(
    path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Local directory to pack.",
        ),
    ],
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Markdown output path."),
    ] = Path("evidence-pack.md"),
    json_path: Annotated[
        Path | None,
        typer.Option("--json", help="Optional JSON output path."),
    ] = None,
    store: Annotated[
        Path | None,
        typer.Option("--store", help="Retrieval store path."),
    ] = None,
    task: Annotated[
        str | None,
        typer.Option("--task", help="Task intent to record in the EvidencePack."),
    ] = None,
) -> None:
    """Build an EvidencePack from a local path."""
    options = PackOptions(store_path=store, task_intent=task)
    pack = pack_directory(path, options=options)
    pack.write_markdown(out)
    if json_path:
        pack.write_json(json_path)
    console.print(f"Wrote EvidencePack [bold]{pack.id}[/bold] with {len(pack.items)} items.")


@app.command("inspect")
def inspect_command(
    pack_json: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="EvidencePack JSON file.",
        ),
    ],
) -> None:
    """Inspect an EvidencePack JSON file."""
    pack = EvidencePack.model_validate_json(pack_json.read_text(encoding="utf-8"))
    table = Table(title=f"EvidencePack {pack.id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Source scope", pack.source_scope)
    table.add_row("Items", _count_label(len(pack.items), "item"))
    table.add_row("Retrieval keys", _count_label(len(pack.retrieval_keys), "retrieval key"))
    table.add_row("Omitted material", _count_label(len(pack.omitted_material), "record"))
    table.add_row("Audit status", pack.audit_status)
    console.print(table)


@app.command("retrieve")
def retrieve_command(
    key: Annotated[str, typer.Argument(help="Retrieval key, such as sha256:<digest>.")],
    store: Annotated[
        Path,
        typer.Option("--store", help="Retrieval store path."),
    ] = Path(".asterism/store"),
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Optional path for retrieved text."),
    ] = None,
) -> None:
    """Retrieve exact stored content by key."""
    try:
        content = RetrievalStore(store).retrieve_text(key)
    except RetrievalKeyError as exc:
        raise typer.BadParameter(str(exc), param_hint="key") from exc

    if out:
        out.write_text(content, encoding="utf-8")
    else:
        typer.echo(content, nl=False)


def _count_label(count: int, singular: str) -> str:
    suffix = singular if count == 1 else f"{singular}s"
    return f"{count} {suffix}"


if __name__ == "__main__":
    app()
