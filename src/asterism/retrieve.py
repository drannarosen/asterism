"""Exact content retrieval for Asterism packs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


class RetrievalKeyError(KeyError):
    """Raised when a retrieval key is invalid or unavailable."""


def sha256_digest(content: bytes) -> str:
    """Return the SHA-256 hex digest for *content*."""
    return sha256(content).hexdigest()


def retrieval_key_for_digest(digest: str) -> str:
    """Return the canonical retrieval key for a SHA-256 digest."""
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"Invalid SHA-256 digest: {digest!r}")
    return f"sha256:{digest}"


@dataclass(frozen=True)
class RetrievalStore:
    """Local content-addressed store for exact pack retrieval."""

    root: Path | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root))

    def put_text(self, content: str, *, source_path: str | None = None) -> str:
        """Store UTF-8 text and return its retrieval key."""
        return self.put_bytes(content.encode("utf-8"), source_path=source_path)

    def put_bytes(self, content: bytes, *, source_path: str | None = None) -> str:
        """Store bytes and return their canonical retrieval key."""
        del source_path
        digest = sha256_digest(content)
        key = retrieval_key_for_digest(digest)
        blob_path = self._blob_path(digest)
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        if not blob_path.exists():
            temporary_path = blob_path.with_name(f".{digest}.tmp")
            temporary_path.write_bytes(content)
            temporary_path.replace(blob_path)
        return key

    def retrieve_text(self, key: str, *, encoding: str = "utf-8") -> str:
        """Retrieve a UTF-8 text chunk by key."""
        return self.retrieve_bytes(key).decode(encoding)

    def retrieve_bytes(self, key: str) -> bytes:
        """Retrieve exact bytes by key."""
        digest = self._digest_from_key(key)
        blob_path = self._blob_path(digest)
        if not blob_path.exists():
            raise RetrievalKeyError(f"Retrieval key is not available: {key}")
        return blob_path.read_bytes()

    def _blob_path(self, digest: str) -> Path:
        return Path(self.root) / "blobs" / "sha256" / digest

    @staticmethod
    def _digest_from_key(key: str) -> str:
        prefix = "sha256:"
        if not key.startswith(prefix):
            raise RetrievalKeyError(f"Unsupported retrieval key: {key}")
        digest = key.removeprefix(prefix)
        try:
            retrieval_key_for_digest(digest)
        except ValueError as exc:
            raise RetrievalKeyError(str(exc)) from exc
        return digest
