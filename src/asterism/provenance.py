"""Provenance records for EvidencePacks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FileProvenance(BaseModel):
    """Provenance for a stored local file or file chunk."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Path relative to the packed source root.")
    sha256: str = Field(description="SHA-256 digest for the exact stored content.")
    retrieval_key: str = Field(description="Content-addressed key for exact retrieval.")
    line_start: int = Field(default=1, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    byte_length: int = Field(default=0, ge=0)
    char_length: int = Field(default=0, ge=0)
    git_commit: str | None = Field(
        default=None,
        description="Git commit for the source tree when available.",
    )
