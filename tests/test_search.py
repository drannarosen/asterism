import pytest

from asterism.evidence import EvidenceItem, EvidencePack, InvariantMarker
from asterism.provenance import FileProvenance
from asterism.search import search_pack

FIRST_DIGEST = "b4d49e9328d6dc551ae29d8199491c3f332f3317770ccc1b6d7536b7a63a351c"
SECOND_DIGEST = "11ea3cdb16d79234259a0d8a7b6684bfd1ba8a47d95cf6cb42af413072c49bac"


def test_search_pack_finds_and_ranks_metadata_hits() -> None:
    pack = EvidencePack(
        id="pack-demo",
        source_scope=".",
        items=[
            EvidenceItem(
                kind="file",
                title="notes.md",
                provenance=FileProvenance(
                    path="notes.md",
                    sha256=FIRST_DIGEST,
                    retrieval_key=f"sha256:{FIRST_DIGEST}",
                ),
                summary="Stored exact text file.",
                invariants=[InvariantMarker(kind="units", text="units: cgs", line_start=1)],
            ),
            EvidenceItem(
                kind="file",
                title="model.py",
                provenance=FileProvenance(
                    path="src/model.py",
                    sha256=SECOND_DIGEST,
                    retrieval_key=f"sha256:{SECOND_DIGEST}",
                ),
                summary="Likelihood implementation.",
                invariants=[
                    InvariantMarker(kind="likelihood", text="likelihood: gaussian", line_start=4)
                ],
            ),
        ],
    )

    hits = search_pack(pack, "likelihood")

    assert len(hits) == 1
    assert hits[0].item.provenance.path == "src/model.py"
    assert hits[0].matched_fields == ("summary", "invariant_kind", "invariant_text")


def test_search_pack_rejects_empty_query() -> None:
    with pytest.raises(ValueError):
        search_pack(EvidencePack(id="pack-demo", source_scope="."), " ")
