"""EvidencePack schema models."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from asterism.provenance import FileProvenance


SCHEMA_VERSION = "asterism.evidencepack.v1alpha1"


class InvariantMarker(BaseModel):
    """A deterministic marker for content that should be preserved carefully."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(description="Invariant family, such as equation, units, or citation.")
    text: str = Field(description="Matched source text.")
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)


class OmittedMaterial(BaseModel):
    """Description of material represented by retrieval instead of compact context."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    retrieval_key: str | None = None
    source_path: str | None = None


class EvidenceItem(BaseModel):
    """A provenance-bearing item in an EvidencePack."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    title: str
    provenance: FileProvenance
    summary: str = ""
    invariants: list[InvariantMarker] = Field(default_factory=list)


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

    @property
    def retrieval_keys(self) -> list[str]:
        """Return all exact retrieval keys referenced by pack items."""
        return [item.provenance.retrieval_key for item in self.items]

    def write_json(self, path: Path | str) -> None:
        """Write the pack as stable, indented JSON."""
        Path(path).write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def write_markdown(self, path: Path | str) -> None:
        """Write a Markdown rendering of the pack."""
        from asterism.render import render_markdown

        Path(path).write_text(render_markdown(self), encoding="utf-8")
