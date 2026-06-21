"""Markdown rendering for EvidencePacks."""

from __future__ import annotations

from collections import Counter

from asterism.evidence import EvidencePack


def render_markdown(pack: EvidencePack) -> str:
    """Render an EvidencePack as an agent-oriented handoff document."""
    lines: list[str] = [
        f"# EvidencePack: {pack.id}",
        "",
        "## Agent Handoff",
        "",
        "- Treat the JSON EvidencePack as canonical; this Markdown is a readable handoff view.",
        (
            "- Use retrieval keys to recover exact source bytes before quoting or editing "
            "source content."
        ),
        (
            "- Preserve source paths, line spans, byte spans, SHA-256 digests, and git "
            "commits when citing evidence."
        ),
        "- Treat omitted material as unavailable unless a retrieval key is present.",
        "",
        "## Pack Summary",
        "",
        f"- Schema: `{pack.schema_version}`",
        f"- Profile: `{pack.profile}`",
        f"- Source scope: `{pack.source_scope}`",
        f"- Audit status: `{pack.audit_status}`",
        f"- Items: {len(pack.items)}",
        f"- Retrieval keys: {len(pack.retrieval_keys)}",
        f"- Omitted material: {len(pack.omitted_material)}",
    ]
    if pack.task_intent:
        lines.append(f"- Task intent: {pack.task_intent}")

    invariant_counts = _invariant_counts(pack)
    lines.extend(["", "## Invariant Index"])
    if not invariant_counts:
        lines.append("")
        lines.append("_No invariant markers recorded._")
    else:
        lines.append("")
        for kind, count in sorted(invariant_counts.items()):
            lines.append(f"- `{kind}`: {count}")

    lines.extend(["", "## Retrieval Commands"])
    if not pack.items:
        lines.append("")
        lines.append("_No retrieval keys recorded._")
    else:
        lines.append("")
        lines.append("Use the retrieval store produced with this pack.")
        lines.append("Each evidence item below includes its exact retrieval command.")
        lines.append("With the default store path:")
        lines.append("")
        lines.append("```bash")
        lines.append("asterism retrieve <retrieval-key> --store .asterism/store")
        lines.append("```")

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
                (
                    f"- Retrieve: `asterism retrieve {provenance.retrieval_key} "
                    "--store .asterism/store`"
                ),
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
    else:
        omission_counts = _omission_counts(pack)
        lines.append("")
        lines.append("Omission summary:")
        for reason, count in sorted(omission_counts.items()):
            lines.append(f"- {reason}: {count}")
        lines.append("")
        lines.append("Omission records:")
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


def _invariant_counts(pack: EvidencePack) -> Counter[str]:
    return Counter(marker.kind for item in pack.items for marker in item.invariants)


def _omission_counts(pack: EvidencePack) -> Counter[str]:
    return Counter(material.reason for material in pack.omitted_material)
