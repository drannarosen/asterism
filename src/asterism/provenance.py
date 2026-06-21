"""Provenance records for EvidencePacks."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RETRIEVAL_KEY_PATTERN = re.compile(r"^sha256:([0-9a-f]{64})$")


def validate_relative_posix_path(value: str, *, field_name: str = "path") -> str:
    """Validate a relative POSIX path used in EvidencePack provenance."""
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if "\\" in value:
        raise ValueError(f"{field_name} must use POSIX separators")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise ValueError(f"{field_name} must be relative to the packed source root")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field_name} must not contain empty, current, or parent segments")
    return value


class FileProvenance(BaseModel):
    """Provenance for a stored local file or file chunk."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Path relative to the packed source root.")
    granularity: Literal["file", "line_chunk"] = Field(
        default="file",
        description="Whether this record represents a whole file or a deterministic line chunk.",
    )
    sha256: str = Field(description="SHA-256 digest for the exact stored content.")
    retrieval_key: str = Field(description="Content-addressed key for exact retrieval.")
    chunk_index: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=1, ge=1)
    line_start: int = Field(default=1, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    byte_start: int = Field(default=0, ge=0)
    byte_end: int | None = Field(default=None, ge=0)
    byte_length: int = Field(default=0, ge=0)
    char_length: int = Field(default=0, ge=0)
    git_commit: str | None = Field(
        default=None,
        description="Git commit for the source tree when available.",
    )

    @field_validator("path")
    @classmethod
    def _validate_relative_posix_path(cls, value: str) -> str:
        return validate_relative_posix_path(value)

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must be a lowercase 64-character hex digest")
        return value

    @field_validator("retrieval_key")
    @classmethod
    def _validate_retrieval_key(cls, value: str) -> str:
        if not RETRIEVAL_KEY_PATTERN.fullmatch(value):
            raise ValueError("retrieval_key must have form sha256:<64 lowercase hex characters>")
        return value

    @field_validator("git_commit")
    @classmethod
    def _validate_git_commit(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError("git_commit must be a lowercase 40-character hex commit SHA")
        return value

    @model_validator(mode="after")
    def _validate_cross_field_contracts(self) -> FileProvenance:
        retrieval_match = RETRIEVAL_KEY_PATTERN.fullmatch(self.retrieval_key)
        if retrieval_match and retrieval_match.group(1) != self.sha256:
            raise ValueError("retrieval_key digest must match sha256")
        if self.line_end is not None and self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        if self.byte_end is not None and self.byte_end < self.byte_start:
            raise ValueError("byte_end must be greater than or equal to byte_start")
        if self.chunk_index >= self.chunk_count:
            raise ValueError("chunk_index must be less than chunk_count")
        if self.granularity == "file" and (self.chunk_index != 0 or self.chunk_count != 1):
            raise ValueError("file granularity must use chunk_index=0 and chunk_count=1")
        return self
