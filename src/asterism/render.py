"""Markdown rendering for EvidencePacks."""

from __future__ import annotations

from asterism.evidence import EvidencePack


def render_markdown(pack: EvidencePack) -> str:
    """Render an EvidencePack as compact Markdown."""
    lines: list[str] = [
        f"# EvidencePack: {pack.id}",
        "",
        f"- Schema: `{pack.schema_version}`",
        f"- Source scope: `{pack.source_scope}`",
        f"- Audit status: `{pack.audit_status}`",
        f"- Items: {len(pack.items)}",
        f"- Retrieval keys: {len(pack.retrieval_keys)}",
    ]
    if pack.task_intent:
        lines.append(f"- Task intent: {pack.task_intent}")

    lines.extend(["", "## Evidence Items"])
    if not pack.items:
        lines.append("")
        lines.append("_No evidence items recorded._")
    for item in pack.items:
        provenance = item.provenance
        line_span = _line_span(provenance.line_start, provenance.line_end)
        lines.extend(
            [
                "",
                f"### {item.title}",
                "",
                f"- Kind: `{item.kind}`",
                f"- Granularity: `{provenance.granularity}`",
                f"- Path: `{provenance.path}`",
                f"- Lines: {line_span}",
                f"- Bytes: {_byte_span(provenance.byte_start, provenance.byte_end)}",
                f"- Chunk: {provenance.chunk_index + 1}/{provenance.chunk_count}",
                f"- SHA-256: `{provenance.sha256}`",
                f"- Retrieval key: `{provenance.retrieval_key}`",
                f"- Stored bytes: {provenance.byte_length}",
                f"- Characters: {provenance.char_length}",
                f"- Summary: {item.summary}",
            ]
        )
        if provenance.git_commit:
            lines.append(f"- Git commit: `{provenance.git_commit}`")
        if item.invariants:
            lines.append("")
            lines.append("Preserved invariant markers:")
            for marker in item.invariants:
                marker_line = f"line {marker.line_start}" if marker.line_start else "line unknown"
                lines.append(f"- `{marker.kind}` at {marker_line}: {marker.text}")

    lines.extend(["", "## Omitted Material"])
    if not pack.omitted_material:
        lines.append("")
        lines.append("_No omitted material recorded._")
    for material in pack.omitted_material:
        source = f" `{material.source_path}`" if material.source_path else ""
        retrieval = f" Retrieval key: `{material.retrieval_key}`." if material.retrieval_key else ""
        lines.append(f"-{source} {material.reason}.{retrieval}".rstrip())

    return "\n".join(lines) + "\n"


def _line_span(line_start: int, line_end: int | None) -> str:
    if line_end is None:
        return f"{line_start}-unknown"
    if line_start == line_end:
        return str(line_start)
    return f"{line_start}-{line_end}"


def _byte_span(byte_start: int, byte_end: int | None) -> str:
    if byte_end is None:
        return f"{byte_start}-unknown"
    return f"{byte_start}-{byte_end} (exclusive)"
