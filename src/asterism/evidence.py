"""EvidencePack schema models."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asterism.provenance import RETRIEVAL_KEY_PATTERN, FileProvenance, validate_relative_posix_path

SCHEMA_VERSION = "asterism.evidencepack.v1alpha1"


class InvariantMarker(BaseModel):
    """A deterministic marker for content that should be preserved carefully."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(description="Invariant family, such as equation, units, or citation.")
    text: str = Field(description="Matched source text.")
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)

    @field_validator("kind", "text")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class OmittedMaterial(BaseModel):
    """Description of material represented by retrieval instead of compact context."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    retrieval_key: str | None = None
    source_path: str | None = None

    @field_validator("reason")
    @classmethod
    def _validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must not be empty")
        return value

    @field_validator("retrieval_key")
    @classmethod
    def _validate_retrieval_key(cls, value: str | None) -> str | None:
        if value is not None and not RETRIEVAL_KEY_PATTERN.fullmatch(value):
            raise ValueError("retrieval_key must have form sha256:<64 lowercase hex characters>")
        return value

    @field_validator("source_path")
    @classmethod
    def _validate_source_path(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_relative_posix_path(value, field_name="source_path")
        return value


class EvidenceItem(BaseModel):
    """A provenance-bearing item in an EvidencePack."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    title: str
    provenance: FileProvenance
    summary: str = ""
    invariants: list[InvariantMarker] = Field(default_factory=list)

    @field_validator("kind", "title")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class EvidencePack(BaseModel):
    """A compact, provenance-preserving scientific context pack."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["asterism.evidencepack.v1alpha1"] = SCHEMA_VERSION
    id: str
    source_scope: str
    task_intent: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[EvidenceItem] = Field(default_factory=list)
    omitted_material: list[OmittedMaterial] = Field(default_factory=list)
    audit_status: str = "draft"

    @field_validator("id", "source_scope")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @property
    def retrieval_keys(self) -> list[str]:
        """Return all exact retrieval keys referenced by pack items."""
        return [item.provenance.retrieval_key for item in self.items]

    def write_json(self, path: Path | str) -> None:
        """Write the pack as stable, indented JSON."""
        Path(path).write_text(self.to_canonical_json() + "\n", encoding="utf-8")

    def to_canonical_json(self) -> str:
        """Return stable JSON for the v1alpha1 wire format."""
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True)

    def write_markdown(self, path: Path | str) -> None:
        """Write a Markdown rendering of the pack."""
        from asterism.render import render_markdown

        Path(path).write_text(render_markdown(self), encoding="utf-8")
