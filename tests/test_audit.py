from pathlib import Path

from asterism.audit import AuditSeverity, audit_pack
from asterism.evidence import EvidencePack
from asterism.packer import PackOptions, pack_directory
from asterism.retrieve import RetrievalStore


def test_audit_pack_passes_for_fresh_pack(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("Equation: E = mc^2\n", encoding="utf-8")
    store_path = root / ".asterism" / "store"

    pack = pack_directory(root, options=PackOptions(store_path=store_path))
    report = audit_pack(pack, store=RetrievalStore(store_path))

    assert report.passed
    assert report.error_count == 0
    assert report.checked_items == 1
    assert report.checked_retrieval_keys == 1


def test_audit_pack_reports_missing_retrieval_blob(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("units: cgs\n", encoding="utf-8")
    store_path = root / ".asterism" / "store"

    pack = pack_directory(root, options=PackOptions(store_path=store_path))
    report = audit_pack(pack, store=RetrievalStore(tmp_path / "missing-store"))

    assert not report.passed
    assert report.error_count == 1
    assert report.findings[0].severity == AuditSeverity.ERROR
    assert report.findings[0].code == "missing_retrieval_blob"


def test_audit_pack_reports_tampered_retrieval_blob(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("likelihood: gaussian\n", encoding="utf-8")
    store_path = root / ".asterism" / "store"

    pack = pack_directory(root, options=PackOptions(store_path=store_path))
    key = pack.items[0].provenance.retrieval_key
    digest = key.removeprefix("sha256:")
    (store_path / "blobs" / "sha256" / digest).write_text("tampered\n", encoding="utf-8")

    report = audit_pack(pack, store=RetrievalStore(store_path))

    assert not report.passed
    assert report.findings[0].code == "retrieval_digest_mismatch"


def test_audit_pack_reports_duplicate_retrieval_keys(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.md").write_text("same\n", encoding="utf-8")
    (root / "b.md").write_text("same\n", encoding="utf-8")
    store_path = root / ".asterism" / "store"

    pack = pack_directory(root, options=PackOptions(store_path=store_path))
    report = audit_pack(pack, store=RetrievalStore(store_path))

    assert report.passed
    assert report.warning_count == 1
    assert any(
        finding.code == "duplicate_retrieval_key"
        and finding.severity == AuditSeverity.WARNING
        for finding in report.findings
    )


def test_audit_pack_reports_unknown_profile(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("api contract\n", encoding="utf-8")
    store_path = root / ".asterism" / "store"

    pack = pack_directory(root, options=PackOptions(store_path=store_path))
    tampered = EvidencePack.model_validate({**pack.model_dump(), "profile": "surprise"})
    report = audit_pack(tampered, store=RetrievalStore(store_path))

    assert not report.passed
    assert any(finding.code == "unknown_profile" for finding in report.findings)
