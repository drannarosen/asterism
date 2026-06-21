"""EvidencePack audit checks."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from asterism.evidence import EvidencePack
from asterism.packer import PACK_PROFILES
from asterism.retrieve import RetrievalKeyError, RetrievalStore, sha256_digest


class AuditSeverity(StrEnum):
    """Severity level for an audit finding."""

    ERROR = "error"
    WARNING = "warning"


class AuditFinding(BaseModel):
    """A single audit finding."""

    model_config = ConfigDict(extra="forbid")

    severity: AuditSeverity
    code: str
    message: str
    path: str | None = None
    retrieval_key: str | None = None


class AuditReport(BaseModel):
    """Audit result for an EvidencePack."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    checked_items: int = 0
    checked_retrieval_keys: int = 0
    findings: list[AuditFinding] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == AuditSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == AuditSeverity.WARNING)


def audit_pack(pack: EvidencePack, *, store: RetrievalStore) -> AuditReport:
    """Audit schema-valid pack metadata and exact retrieval integrity."""
    findings: list[AuditFinding] = []

    if pack.profile not in PACK_PROFILES:
        findings.append(
            AuditFinding(
                severity=AuditSeverity.ERROR,
                code="unknown_profile",
                message=f"Unknown pack profile: {pack.profile}",
            )
        )

    seen_keys: dict[str, str] = {}
    for item in pack.items:
        provenance = item.provenance
        key = provenance.retrieval_key
        previous_path = seen_keys.get(key)
        if previous_path is not None and previous_path != provenance.path:
            findings.append(
                AuditFinding(
                    severity=AuditSeverity.WARNING,
                    code="duplicate_retrieval_key",
                    message="Multiple source paths reference identical stored bytes.",
                    path=provenance.path,
                    retrieval_key=key,
                )
            )
        else:
            seen_keys[key] = provenance.path

        try:
            content = store.retrieve_bytes(key)
        except RetrievalKeyError:
            findings.append(
                AuditFinding(
                    severity=AuditSeverity.ERROR,
                    code="missing_retrieval_blob",
                    message="Retrieval key is missing from the store.",
                    path=provenance.path,
                    retrieval_key=key,
                )
            )
            continue

        digest = sha256_digest(content)
        if digest != provenance.sha256:
            findings.append(
                AuditFinding(
                    severity=AuditSeverity.ERROR,
                    code="retrieval_digest_mismatch",
                    message="Stored bytes do not match provenance SHA-256 digest.",
                    path=provenance.path,
                    retrieval_key=key,
                )
            )
        if len(content) != provenance.byte_length:
            findings.append(
                AuditFinding(
                    severity=AuditSeverity.ERROR,
                    code="byte_length_mismatch",
                    message="Stored bytes do not match provenance byte_length.",
                    path=provenance.path,
                    retrieval_key=key,
                )
            )

    for omitted in pack.omitted_material:
        if omitted.retrieval_key is not None:
            try:
                store.retrieve_bytes(omitted.retrieval_key)
            except RetrievalKeyError:
                findings.append(
                    AuditFinding(
                        severity=AuditSeverity.ERROR,
                        code="missing_omitted_retrieval_blob",
                        message="Omitted material references a missing retrieval key.",
                        path=omitted.source_path,
                        retrieval_key=omitted.retrieval_key,
                    )
                )

    error_count = sum(1 for finding in findings if finding.severity == AuditSeverity.ERROR)
    return AuditReport(
        passed=error_count == 0,
        checked_items=len(pack.items),
        checked_retrieval_keys=len(pack.retrieval_keys),
        findings=findings,
    )
