from asterism.evidence import (
    AuditSummary,
    EvidenceItem,
    EvidencePack,
    InvariantMarker,
    OmittedMaterial,
)
from asterism.provenance import FileProvenance
from asterism.render import render_markdown

EXAMPLE_DIGEST = "b4d49e9328d6dc551ae29d8199491c3f332f3317770ccc1b6d7536b7a63a351c"


def test_render_markdown_includes_agent_handoff_sections() -> None:
    pack = EvidencePack(
        id="pack-demo",
        source_scope=".",
        items=[
            EvidenceItem(
                kind="file",
                title="notes.md",
                provenance=FileProvenance(
                    path="notes.md",
                    sha256=EXAMPLE_DIGEST,
                    retrieval_key=f"sha256:{EXAMPLE_DIGEST}",
                    byte_length=12,
                    char_length=12,
                ),
                summary="Stored exact text file.",
                invariants=[
                    InvariantMarker(kind="equation", text="E = mc^2", line_start=1),
                    InvariantMarker(kind="units", text="units: cgs", line_start=2),
                ],
            )
        ],
        omitted_material=[
            OmittedMaterial(
                reason="Secret-looking content omitted (OpenAI API key at line 1)",
                source_path=".env",
            )
        ],
        audit_status="passed_with_warnings",
        audit_summary=AuditSummary(
            status="passed_with_warnings",
            checked_items=1,
            checked_retrieval_keys=1,
            errors=0,
            warnings=1,
        ),
    )

    markdown = render_markdown(pack)

    assert "## Agent Handoff" in markdown
    assert "## Pack Summary" in markdown
    assert "## Invariant Index" in markdown
    assert "- Audit warnings: 1" in markdown
    assert "- `equation`: 1" in markdown
    assert "- `units`: 1" in markdown
    assert "## Retrieval Commands" in markdown
    assert f"asterism retrieve sha256:{EXAMPLE_DIGEST} --store .asterism/store" in markdown
    assert "Omission summary:" in markdown
    assert "Secret-looking content omitted (OpenAI API key at line 1): 1" in markdown
    assert "Omission records:" in markdown
    assert "`notes.md`" in markdown
