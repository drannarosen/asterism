"""Command-line interface for Asterism."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from asterism.audit import AuditReport, audit_pack
from asterism.evidence import EvidencePack
from asterism.packer import PackOptions, available_pack_profiles, pack_directory
from asterism.retrieve import RetrievalKeyError, RetrievalStore
from asterism.search import SearchHit, search_pack

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
    profile: Annotated[
        str,
        typer.Option(
            "--profile",
            help="Deterministic pack profile: repo, debug, review, or handoff.",
        ),
    ] = "repo",
) -> None:
    """Build an EvidencePack from a local path."""
    try:
        options = PackOptions(profile=profile, store_path=store, task_intent=task)  # type: ignore[arg-type]
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="profile") from exc
    pack = pack_directory(path, options=options)
    pack.write_markdown(out)
    if json_path:
        pack.write_json(json_path)
    message = f"Wrote EvidencePack [bold]{pack.id}[/bold] with {len(pack.items)} items."
    if pack.audit_summary:
        message += (
            f" Audit {pack.audit_summary.status}: "
            f"{pack.audit_summary.errors} errors, {pack.audit_summary.warnings} warnings."
        )
    console.print(message)


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
    table.add_row("Profile", pack.profile)
    table.add_row("Items", _count_label(len(pack.items), "item"))
    table.add_row("Retrieval keys", _count_label(len(pack.retrieval_keys), "retrieval key"))
    table.add_row("Omitted material", _count_label(len(pack.omitted_material), "record"))
    table.add_row("Audit status", pack.audit_status)
    if pack.audit_summary:
        table.add_row("Audit checked items", str(pack.audit_summary.checked_items))
        table.add_row(
            "Audit checked retrieval keys",
            str(pack.audit_summary.checked_retrieval_keys),
        )
        table.add_row("Audit errors", str(pack.audit_summary.errors))
        table.add_row("Audit warnings", str(pack.audit_summary.warnings))
    console.print(table)


@app.command("audit")
def audit_command(
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
    store: Annotated[
        Path,
        typer.Option("--store", help="Retrieval store path."),
    ] = Path(".asterism/store"),
) -> None:
    """Audit EvidencePack retrieval integrity and metadata consistency."""
    pack = EvidencePack.model_validate_json(pack_json.read_text(encoding="utf-8"))
    report = audit_pack(pack, store=RetrievalStore(store))
    _render_audit_report(report)
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("search")
def search_command(
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
    query: Annotated[str, typer.Argument(help="Metadata query to search for.")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum hits to print.")] = 20,
) -> None:
    """Search EvidencePack metadata for paths, invariants, hashes, or retrieval keys."""
    pack = EvidencePack.model_validate_json(pack_json.read_text(encoding="utf-8"))
    try:
        hits = search_pack(pack, query, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="query") from exc
    _render_search_hits(hits, query=query)


@app.command("get")
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


def _render_search_hits(hits: list[SearchHit], *, query: str) -> None:
    if not hits:
        console.print(f"No EvidencePack metadata hits for [bold]{query}[/bold].")
        return

    table = Table(title=f"EvidencePack search: {query}")
    table.add_column("Score", justify="right", no_wrap=True)
    table.add_column("Path")
    table.add_column("Lines", no_wrap=True)
    table.add_column("Matched")
    table.add_column("Key")
    for hit in hits:
        provenance = hit.item.provenance
        table.add_row(
            str(hit.score),
            provenance.path,
            _line_span(provenance.line_start, provenance.line_end),
            ", ".join(hit.matched_fields),
            _short_key(provenance.retrieval_key),
        )
    console.print(table)
    typer.echo("Retrieval commands:")
    for hit in hits:
        provenance = hit.item.provenance
        typer.echo(
            f"- {provenance.path}: "
            f"asterism retrieve {provenance.retrieval_key} --store .asterism/store"
        )


def _count_label(count: int, singular: str) -> str:
    suffix = singular if count == 1 else f"{singular}s"
    return f"{count} {suffix}"


def _line_span(line_start: int, line_end: int | None) -> str:
    if line_end is None:
        return f"{line_start}-unknown"
    if line_start == line_end:
        return str(line_start)
    return f"{line_start}-{line_end}"


def _short_key(key: str) -> str:
    if len(key) <= 24:
        return key
    return f"{key[:21]}..."


def _render_audit_report(report: AuditReport) -> None:
    status = "passed" if report.passed else "failed"
    console.print(
        f"Audit [bold]{status}[/bold]: "
        f"{report.checked_items} items, "
        f"{report.checked_retrieval_keys} retrieval keys, "
        f"{report.error_count} errors, "
        f"{report.warning_count} warnings."
    )
    if not report.findings:
        return
    table = Table(title="Audit Findings")
    table.add_column("Severity", no_wrap=True)
    table.add_column("Code", no_wrap=True)
    table.add_column("Path")
    table.add_column("Retrieval key", overflow="fold")
    table.add_column("Message")
    for finding in report.findings:
        table.add_row(
            finding.severity.value,
            finding.code,
            finding.path or "",
            finding.retrieval_key or "",
            finding.message,
        )
    console.print(table)


@app.command("profiles")
def profiles_command() -> None:
    """List deterministic pack profiles."""
    table = Table(title="Asterism Pack Profiles")
    table.add_column("Name")
    table.add_column("Chunk lines", justify="right")
    table.add_column("Max bytes", justify="right")
    table.add_column("Emphasized invariants")
    table.add_column("Description")
    for profile in available_pack_profiles():
        table.add_row(
            profile.name,
            str(profile.chunk_line_count),
            str(profile.max_file_bytes),
            ", ".join(profile.emphasized_invariants),
            profile.description,
        )
    console.print(table)


if __name__ == "__main__":
    app()
