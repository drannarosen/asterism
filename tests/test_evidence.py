from asterism.evidence import EvidenceItem, EvidencePack, InvariantMarker
from asterism.provenance import FileProvenance


def test_evidence_pack_round_trips_json() -> None:
    item = EvidenceItem(
        kind="file",
        title="notes.txt",
        provenance=FileProvenance(path="notes.txt", sha256="abc", retrieval_key="sha256:abc"),
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

    assert EvidencePack.model_validate_json(output_path.read_text(encoding="utf-8")).id == "pack-demo"
