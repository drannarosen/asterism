"""Local directory packing for Asterism."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NamedTuple

from pathspec.gitignore import GitIgnoreSpec

from asterism.evidence import (
    AuditSummary,
    EvidenceItem,
    EvidencePack,
    InvariantMarker,
    OmittedMaterial,
)
from asterism.extractors import extract_invariants
from asterism.provenance import FileProvenance
from asterism.retrieve import RetrievalStore, sha256_digest

PackProfile = Literal["repo", "debug", "review", "handoff"]

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

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private key",
        re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    ),
    (
        "OpenAI API key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "GitHub token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "AWS access key",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "Slack token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    ),
    (
        "secret assignment",
        re.compile(
            r"\b(?:api[_-]?key|secret|token|password|passwd|client_secret|private_key)"
            r"\b\s*[:=]\s*[\"']?[A-Za-z0-9_./+=@$%:~-]{12,}",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class ProfileDefinition:
    """Deterministic policy preset for pack construction."""

    name: PackProfile
    description: str
    chunk_line_count: int
    max_file_bytes: int
    extra_ignore_patterns: tuple[str, ...] = ()
    emphasized_invariants: tuple[str, ...] = ()


PACK_PROFILES: dict[PackProfile, ProfileDefinition] = {
    "repo": ProfileDefinition(
        name="repo",
        description="General repository context with balanced chunking.",
        chunk_line_count=200,
        max_file_bytes=1_000_000,
        emphasized_invariants=("api_contract", "citation", "equation", "units"),
    ),
    "debug": ProfileDefinition(
        name="debug",
        description="Finer chunks for failures, stack traces, tolerances, and local debugging.",
        chunk_line_count=80,
        max_file_bytes=2_000_000,
        emphasized_invariants=("failing_test", "tolerance", "api_contract", "likelihood"),
    ),
    "review": ProfileDefinition(
        name="review",
        description="Review-oriented context that skips common generated reports.",
        chunk_line_count=120,
        max_file_bytes=1_000_000,
        extra_ignore_patterns=(
            ".coverage",
            "coverage.xml",
            "htmlcov/",
            "junit.xml",
            "test-results/",
        ),
        emphasized_invariants=("api_contract", "citation", "equation", "units", "tolerance"),
    ),
    "handoff": ProfileDefinition(
        name="handoff",
        description="Coarser session handoff context with generated report noise suppressed.",
        chunk_line_count=160,
        max_file_bytes=750_000,
        extra_ignore_patterns=(
            ".coverage",
            "coverage.xml",
            "htmlcov/",
            "junit.xml",
            "test-results/",
        ),
        emphasized_invariants=("api_contract", "citation", "equation", "units", "failing_test"),
    ),
}


@dataclass(frozen=True)
class PackOptions:
    """Options for local directory packing."""

    profile: PackProfile = "repo"
    task_intent: str | None = None
    store_path: Path | str | None = None
    include_git: bool = True
    max_file_bytes: int | None = None
    chunk_line_count: int | None = None
    extra_ignore_patterns: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.profile not in PACK_PROFILES:
            raise ValueError(f"Unknown pack profile: {self.profile}")
        if self.max_file_bytes is not None and self.max_file_bytes < 1:
            raise ValueError("max_file_bytes must be at least 1")
        if self.chunk_line_count is not None and self.chunk_line_count < 1:
            raise ValueError("chunk_line_count must be at least 1")


@dataclass(frozen=True)
class _ResolvedPackOptions:
    profile: ProfileDefinition
    task_intent: str | None
    store_path: Path | str | None
    include_git: bool
    max_file_bytes: int
    chunk_line_count: int
    extra_ignore_patterns: tuple[str, ...]


def available_pack_profiles() -> tuple[ProfileDefinition, ...]:
    """Return supported deterministic pack profiles."""
    return tuple(PACK_PROFILES.values())


def pack_directory(root: Path | str, *, options: PackOptions | None = None) -> EvidencePack:
    """Build an EvidencePack from a local directory."""
    source_root = Path(root).resolve()
    if not source_root.exists():
        raise FileNotFoundError(source_root)
    if not source_root.is_dir():
        raise NotADirectoryError(source_root)

    resolved = _resolve_options(options or PackOptions())
    store_path = (
        Path(resolved.store_path) if resolved.store_path else source_root / ".asterism" / "store"
    )
    store = RetrievalStore(store_path)
    ignore_spec = _build_ignore_spec(source_root, resolved)
    git_commit = _git_commit(source_root) if resolved.include_git else None

    items: list[EvidenceItem] = []
    omitted: list[OmittedMaterial] = []
    candidate_files, path_omissions = _iter_candidate_files(source_root, ignore_spec)
    omitted.extend(path_omissions)
    for path in candidate_files:
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

        if len(content_bytes) > resolved.max_file_bytes:
            omitted.append(
                OmittedMaterial(reason="File exceeds max_file_bytes", source_path=relative_path)
            )
            continue

        if _is_binary_content(content_bytes):
            omitted.append(OmittedMaterial(reason="Binary file", source_path=relative_path))
            continue

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            omitted.append(
                OmittedMaterial(reason="Binary or non-UTF-8 file", source_path=relative_path)
            )
            continue

        secret_match = _detect_secret(content)
        if secret_match is not None:
            omitted.append(
                OmittedMaterial(
                    reason=f"Secret-looking content omitted ({secret_match})",
                    source_path=relative_path,
                )
            )
            continue

        chunks = _line_chunks(content, chunk_line_count=resolved.chunk_line_count)
        chunk_count = len(chunks)
        for chunk_index, chunk in enumerate(chunks):
            chunk_bytes = chunk.text.encode("utf-8")
            digest = sha256_digest(chunk_bytes)
            retrieval_key = store.put_bytes(chunk_bytes, source_path=relative_path)
            invariants = extract_invariants(chunk.text, line_offset=chunk.line_start - 1)
            granularity: Literal["file", "line_chunk"] = (
                "file" if chunk_count == 1 else "line_chunk"
            )
            items.append(
                EvidenceItem(
                    kind="file" if granularity == "file" else "file_chunk",
                    title=_item_title(relative_path, chunk.line_start, chunk.line_end, chunk_count),
                    provenance=FileProvenance(
                        path=relative_path,
                        granularity=granularity,
                        sha256=digest,
                        retrieval_key=retrieval_key,
                        chunk_index=chunk_index,
                        chunk_count=chunk_count,
                        line_start=chunk.line_start,
                        line_end=chunk.line_end,
                        byte_start=chunk.byte_start,
                        byte_end=chunk.byte_end,
                        byte_length=len(chunk_bytes),
                        char_length=len(chunk.text),
                        git_commit=git_commit,
                    ),
                    summary=_file_summary(
                        chunk.line_count,
                        invariants,
                        profile=resolved.profile,
                        chunk_index=chunk_index,
                        chunk_count=chunk_count,
                    ),
                    invariants=invariants,
                )
            )

    items = _rank_items(items, resolved.profile)
    pack_id = _pack_id(source_root, items, profile=resolved.profile.name)
    pack = EvidencePack(
        id=pack_id,
        profile=resolved.profile.name,
        source_scope=str(source_root),
        task_intent=resolved.task_intent,
        items=items,
        omitted_material=omitted,
    )
    return _attach_audit_summary(pack, store)


def detect_invariants(content: str, *, line_offset: int = 0) -> list[InvariantMarker]:
    """Return deterministic markers for likely scientific correctness invariants."""
    return extract_invariants(content, line_offset=line_offset)


def _resolve_options(options: PackOptions) -> _ResolvedPackOptions:
    profile = PACK_PROFILES[options.profile]
    return _ResolvedPackOptions(
        profile=profile,
        task_intent=options.task_intent,
        store_path=options.store_path,
        include_git=options.include_git,
        max_file_bytes=options.max_file_bytes or profile.max_file_bytes,
        chunk_line_count=options.chunk_line_count or profile.chunk_line_count,
        extra_ignore_patterns=profile.extra_ignore_patterns + options.extra_ignore_patterns,
    )


def _attach_audit_summary(pack: EvidencePack, store: RetrievalStore) -> EvidencePack:
    from asterism.audit import audit_pack

    report = audit_pack(pack, store=store)
    if not report.passed:
        status = "failed"
    elif report.warning_count:
        status = "passed_with_warnings"
    else:
        status = "passed"
    return pack.model_copy(
        update={
            "audit_status": status,
            "audit_summary": AuditSummary(
                status=status,
                checked_items=report.checked_items,
                checked_retrieval_keys=report.checked_retrieval_keys,
                errors=report.error_count,
                warnings=report.warning_count,
            ),
        }
    )


def _build_ignore_spec(root: Path, options: _ResolvedPackOptions) -> GitIgnoreSpec:
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    patterns.extend(_gitignore_patterns(root))
    patterns.extend(options.extra_ignore_patterns)
    return GitIgnoreSpec.from_lines(patterns)


def _gitignore_patterns(root: Path) -> list[str]:
    patterns: list[str] = []
    for gitignore in sorted(root.rglob(".gitignore")):
        base = gitignore.parent.relative_to(root).as_posix()
        for raw_line in gitignore.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                patterns.append(raw_line)
                continue
            if not base or base == ".":
                patterns.append(raw_line)
                continue
            patterns.extend(_prefix_gitignore_pattern(line, base))
    return patterns


def _prefix_gitignore_pattern(line: str, base: str) -> list[str]:
    negated = line.startswith("!")
    pattern = line[1:] if negated else line
    pattern = pattern.lstrip("/")
    if not pattern:
        return [line]

    prefix = "!" if negated else ""
    if "/" in pattern.rstrip("/"):
        return [f"{prefix}{base}/{pattern}"]
    return [f"{prefix}{base}/{pattern}", f"{prefix}{base}/**/{pattern}"]


def _iter_candidate_files(
    root: Path, ignore_spec: GitIgnoreSpec
) -> tuple[list[Path], list[OmittedMaterial]]:
    files: list[Path] = []
    omissions: list[OmittedMaterial] = []
    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)
        kept_dir_names: list[str] = []
        for name in sorted(dir_names):
            path = current_path / name
            if _is_ignored(path, root, ignore_spec, is_dir=True):
                continue
            if path.is_symlink():
                omissions.append(
                    OmittedMaterial(
                        reason="Symlink skipped",
                        source_path=path.relative_to(root).as_posix(),
                    )
                )
                continue
            kept_dir_names.append(name)
        dir_names[:] = kept_dir_names
        for file_name in sorted(file_names):
            path = current_path / file_name
            if _is_ignored(path, root, ignore_spec, is_dir=False):
                continue
            if path.is_symlink():
                omissions.append(
                    OmittedMaterial(
                        reason="Symlink skipped",
                        source_path=path.relative_to(root).as_posix(),
                    )
                )
                continue
            files.append(path)
    return files, omissions


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


def _is_binary_content(content: bytes) -> bool:
    return b"\0" in content[:8192]


def _detect_secret(content: str) -> str | None:
    for line_number, line in enumerate(content.splitlines(), start=1):
        for label, pattern in _SECRET_PATTERNS:
            match = pattern.search(line)
            if match is None:
                continue
            if _looks_like_placeholder(match.group(0)):
                continue
            return f"{label} at line {line_number}"
    return None


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    placeholders = (
        "<",
        ">",
        "example",
        "placeholder",
        "changeme",
        "replace",
        "your_",
        "your-",
        "xxxxx",
        "dummy",
    )
    return any(placeholder in lowered for placeholder in placeholders)


def _line_count(content: str) -> int | None:
    if not content:
        return None
    return len(content.splitlines()) or 1


class _LineChunk(NamedTuple):
    text: str
    line_start: int
    line_end: int | None
    byte_start: int
    byte_end: int

    @property
    def line_count(self) -> int | None:
        if self.line_end is None:
            return None
        return self.line_end - self.line_start + 1


def _line_chunks(content: str, *, chunk_line_count: int) -> list[_LineChunk]:
    if chunk_line_count < 1:
        raise ValueError("chunk_line_count must be at least 1")
    lines = content.splitlines(keepends=True)
    if not lines:
        return [_LineChunk(text="", line_start=1, line_end=None, byte_start=0, byte_end=0)]
    if len(lines) <= chunk_line_count:
        return [
            _LineChunk(
                text=content,
                line_start=1,
                line_end=len(lines),
                byte_start=0,
                byte_end=len(content.encode("utf-8")),
            )
        ]

    chunks: list[_LineChunk] = []
    byte_start = 0
    for start_index in range(0, len(lines), chunk_line_count):
        chunk_lines = lines[start_index : start_index + chunk_line_count]
        chunk_text = "".join(chunk_lines)
        chunk_bytes = chunk_text.encode("utf-8")
        byte_end = byte_start + len(chunk_bytes)
        chunks.append(
            _LineChunk(
                text=chunk_text,
                line_start=start_index + 1,
                line_end=start_index + len(chunk_lines),
                byte_start=byte_start,
                byte_end=byte_end,
            )
        )
        byte_start = byte_end
    return chunks


def _file_summary(
    line_count: int | None,
    invariants: list[InvariantMarker],
    *,
    profile: ProfileDefinition,
    chunk_index: int = 0,
    chunk_count: int = 1,
) -> str:
    line_label = "0 lines" if line_count is None else f"{line_count} lines"
    marker_label = f"{len(invariants)} invariant markers"
    if chunk_count == 1:
        summary = f"Stored exact text file with {line_label} and {marker_label}."
    else:
        summary = (
            f"Stored exact text chunk {chunk_index + 1}/{chunk_count} "
            f"with {line_label} and {marker_label}."
        )
    emphasis_label = _profile_emphasis_label(invariants, profile)
    if emphasis_label:
        summary += f" Profile {profile.name} emphasis: {emphasis_label}."
    return summary


def _rank_items(items: list[EvidenceItem], profile: ProfileDefinition) -> list[EvidenceItem]:
    """Order items by profile semantic emphasis, then stable source position."""
    return sorted(
        items,
        key=lambda item: (
            -_profile_priority(item, profile),
            item.provenance.path,
            item.provenance.chunk_index,
            item.title,
        ),
    )


def _profile_priority(item: EvidenceItem, profile: ProfileDefinition) -> int:
    emphasized = set(profile.emphasized_invariants)
    emphasized_count = sum(marker.kind in emphasized for marker in item.invariants)
    return emphasized_count * 100 + len(item.invariants)


def _profile_emphasis_label(
    invariants: list[InvariantMarker], profile: ProfileDefinition
) -> str | None:
    emphasized = set(profile.emphasized_invariants)
    counts: dict[str, int] = {}
    for marker in invariants:
        if marker.kind not in emphasized:
            continue
        counts[marker.kind] = counts.get(marker.kind, 0) + 1
    if not counts:
        return None
    return ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))


def _item_title(relative_path: str, line_start: int, line_end: int | None, chunk_count: int) -> str:
    if chunk_count == 1:
        return relative_path
    if line_end is None:
        return f"{relative_path}#L{line_start}"
    return f"{relative_path}#L{line_start}-L{line_end}"


def _pack_id(root: Path, items: list[EvidenceItem], *, profile: PackProfile) -> str:
    fingerprint_input = "\n".join(
        f"{profile}:{item.provenance.path}:{item.provenance.chunk_index}:{item.provenance.sha256}"
        for item in items
    ).encode("utf-8")
    fingerprint = sha256_digest(fingerprint_input)[:12]
    name = root.name or "root"
    return f"{name}-{fingerprint}"
