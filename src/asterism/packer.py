"""Local directory packing for Asterism."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pathspec.gitignore import GitIgnoreSpec

from asterism.evidence import EvidenceItem, EvidencePack, InvariantMarker, OmittedMaterial
from asterism.provenance import FileProvenance
from asterism.retrieve import RetrievalStore, sha256_digest

DEFAULT_IGNORE_PATTERNS = (
    ".git",
    ".git/",
    ".asterism/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    "*.py[cod]",
    "*.egg-info/",
    "dist/",
    "build/",
)

_EQUATION_RE = re.compile(r"(^|\b)(equation|formula)\b|[A-Za-z0-9_{}\])]\s*=\s*[^=]")
_DOI_RE = re.compile(r"\b(doi:|10\.\d{4,9}/|arxiv:)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PackOptions:
    """Options for local directory packing."""

    profile: str = "repo"
    task_intent: str | None = None
    store_path: Path | str | None = None
    include_git: bool = True
    max_file_bytes: int = 1_000_000
    extra_ignore_patterns: tuple[str, ...] = field(default_factory=tuple)


def pack_directory(root: Path | str, *, options: PackOptions | None = None) -> EvidencePack:
    """Build an EvidencePack from a local directory."""
    source_root = Path(root).resolve()
    if not source_root.exists():
        raise FileNotFoundError(source_root)
    if not source_root.is_dir():
        raise NotADirectoryError(source_root)

    options = options or PackOptions()
    store_path = (
        Path(options.store_path) if options.store_path else source_root / ".asterism" / "store"
    )
    store = RetrievalStore(store_path)
    ignore_spec = _build_ignore_spec(source_root, options)
    git_commit = _git_commit(source_root) if options.include_git else None

    items: list[EvidenceItem] = []
    omitted: list[OmittedMaterial] = []
    for path in _iter_candidate_files(source_root, ignore_spec):
        relative_path = path.relative_to(source_root).as_posix()
        try:
            content_bytes = path.read_bytes()
        except OSError as exc:
            omitted.append(
                OmittedMaterial(
                    reason=f"Could not read file: {exc}",
                    source_path=relative_path,
                )
            )
            continue

        if len(content_bytes) > options.max_file_bytes:
            omitted.append(
                OmittedMaterial(reason="File exceeds max_file_bytes", source_path=relative_path)
            )
            continue

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            omitted.append(
                OmittedMaterial(reason="Binary or non-UTF-8 file", source_path=relative_path)
            )
            continue

        digest = sha256_digest(content_bytes)
        retrieval_key = store.put_bytes(content_bytes, source_path=relative_path)
        line_count = _line_count(content)
        invariants = detect_invariants(content)
        items.append(
            EvidenceItem(
                kind="file",
                title=relative_path,
                provenance=FileProvenance(
                    path=relative_path,
                    sha256=digest,
                    retrieval_key=retrieval_key,
                    line_start=1,
                    line_end=line_count,
                    byte_length=len(content_bytes),
                    char_length=len(content),
                    git_commit=git_commit,
                ),
                summary=_file_summary(line_count, invariants),
                invariants=invariants,
            )
        )

    pack_id = _pack_id(source_root, items)
    return EvidencePack(
        id=pack_id,
        source_scope=str(source_root),
        task_intent=options.task_intent,
        items=items,
        omitted_material=omitted,
    )


def detect_invariants(content: str) -> list[InvariantMarker]:
    """Return deterministic markers for likely scientific correctness invariants."""
    markers: list[InvariantMarker] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        for kind in _invariant_kinds(stripped, lowered):
            markers.append(InvariantMarker(kind=kind, text=stripped, line_start=line_number))
    return markers


def _invariant_kinds(line: str, lowered: str) -> list[str]:
    kinds: list[str] = []
    if _EQUATION_RE.search(line):
        kinds.append("equation")
    if "unit" in lowered or "cgs" in lowered or "si " in lowered:
        kinds.append("units")
    if "prior" in lowered:
        kinds.append("prior")
    if "likelihood" in lowered:
        kinds.append("likelihood")
    if "tolerance" in lowered or "tol=" in lowered or "rtol" in lowered or "atol" in lowered:
        kinds.append("tolerance")
    if "api" in lowered or "schema" in lowered or "contract" in lowered:
        kinds.append("api_contract")
    if "traceback" in lowered or "failed" in lowered or "error:" in lowered:
        kinds.append("failing_test")
    if "citation" in lowered or _DOI_RE.search(line):
        kinds.append("citation")
    return kinds


def _build_ignore_spec(root: Path, options: PackOptions) -> GitIgnoreSpec:
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    gitignore = root / ".gitignore"
    if gitignore.exists():
        patterns.extend(gitignore.read_text(encoding="utf-8").splitlines())
    patterns.extend(options.extra_ignore_patterns)
    return GitIgnoreSpec.from_lines(patterns)


def _iter_candidate_files(root: Path, ignore_spec: GitIgnoreSpec) -> list[Path]:
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)
        dir_names[:] = [
            name
            for name in sorted(dir_names)
            if not _is_ignored(current_path / name, root, ignore_spec, is_dir=True)
        ]
        for file_name in sorted(file_names):
            path = current_path / file_name
            if not _is_ignored(path, root, ignore_spec, is_dir=False):
                files.append(path)
    return files


def _is_ignored(path: Path, root: Path, ignore_spec: GitIgnoreSpec, *, is_dir: bool) -> bool:
    relative_path = path.relative_to(root).as_posix()
    if ignore_spec.match_file(relative_path):
        return True
    return is_dir and ignore_spec.match_file(f"{relative_path}/")


def _git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _line_count(content: str) -> int | None:
    if not content:
        return None
    return len(content.splitlines()) or 1


def _file_summary(line_count: int | None, invariants: list[InvariantMarker]) -> str:
    line_label = "0 lines" if line_count is None else f"{line_count} lines"
    marker_label = f"{len(invariants)} invariant markers"
    return f"Stored exact text file with {line_label} and {marker_label}."


def _pack_id(root: Path, items: list[EvidenceItem]) -> str:
    fingerprint_input = "\n".join(
        f"{item.provenance.path}:{item.provenance.sha256}" for item in items
    ).encode("utf-8")
    fingerprint = sha256_digest(fingerprint_input)[:12]
    name = root.name or "root"
    return f"{name}-{fingerprint}"
