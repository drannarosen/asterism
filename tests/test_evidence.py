import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from asterism.evidence import EvidenceItem, EvidencePack, InvariantMarker, OmittedMaterial
from asterism.provenance import FileProvenance

EXAMPLE_DIGEST = "b4d49e9328d6dc551ae29d8199491c3f332f3317770ccc1b6d7536b7a63a351c"


def test_evidence_pack_round_trips_json() -> None:
    item = EvidenceItem(
        kind="file",
        title="notes.txt",
        provenance=FileProvenance(
            path="notes.txt",
            sha256=EXAMPLE_DIGEST,
            retrieval_key=f"sha256:{EXAMPLE_DIGEST}",
        ),
        summary="Stored exactly.",
        invariants=[InvariantMarker(kind="equation", text="E = mc^2", line_start=1)],
    )
    pack = EvidencePack(id="pack-demo", source_scope=".", items=[item])

    restored = EvidencePack.model_validate_json(pack.model_dump_json())

    assert restored.items[0].provenance.path == "notes.txt"
    assert restored.items[0].invariants[0].kind == "equation"


def test_evidence_pack_writes_json(tmp_path) -> None:
    output_path = tmp_path / "pack.json"
    pack = EvidencePack(id="pack-demo", source_scope=".")

    pack.write_json(output_path)

    restored = EvidencePack.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert restored.id == "pack-demo"


def test_evidence_pack_rejects_invalid_hashes() -> None:
    with pytest.raises(ValidationError):
        FileProvenance(path="notes.txt", sha256="abc", retrieval_key="sha256:abc")


def test_evidence_pack_rejects_mismatched_retrieval_key() -> None:
    other_digest = "0" * 64
    with pytest.raises(ValidationError):
        FileProvenance(
            path="notes.txt",
            sha256=EXAMPLE_DIGEST,
            retrieval_key=f"sha256:{other_digest}",
        )


def test_evidence_pack_rejects_absolute_provenance_paths() -> None:
    with pytest.raises(ValidationError):
        FileProvenance(
            path="/private/notes.txt",
            sha256=EXAMPLE_DIGEST,
            retrieval_key=f"sha256:{EXAMPLE_DIGEST}",
        )


def test_evidence_pack_rejects_invalid_line_spans() -> None:
    with pytest.raises(ValidationError):
        FileProvenance(
            path="notes.txt",
            sha256=EXAMPLE_DIGEST,
            retrieval_key=f"sha256:{EXAMPLE_DIGEST}",
            line_start=3,
            line_end=2,
        )


def test_omitted_material_rejects_invalid_retrieval_key() -> None:
    with pytest.raises(ValidationError):
        OmittedMaterial(reason="Skipped", retrieval_key="sha1:abc", source_path="notes.txt")


def test_omitted_material_rejects_absolute_source_path() -> None:
    with pytest.raises(ValidationError):
        OmittedMaterial(reason="Skipped", source_path="/private/notes.txt")


def test_v1alpha1_fixture_validates_and_serializes_canonically() -> None:
    fixture = Path("tests/fixtures/evidencepack-v1alpha1.json")
    pack = EvidencePack.model_validate_json(fixture.read_text(encoding="utf-8"))

    assert pack.schema_version == "asterism.evidencepack.v1alpha1"
    assert pack.items[0].provenance.sha256 == EXAMPLE_DIGEST
    assert json.loads(pack.to_canonical_json()) == json.loads(fixture.read_text(encoding="utf-8"))
