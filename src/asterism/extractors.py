"""Deterministic domain extractors for scientific EvidencePacks."""

from __future__ import annotations

import re

from asterism.evidence import InvariantMarker

_EQUATION_WORD_RE = re.compile(r"(^|\b)(equation|formula)\b", re.IGNORECASE)
_EQUATION_LHS_RE = re.compile(r"[A-Za-z][A-Za-z0-9_{}^\\/\s+\-*()]*")
_DOI_RE = re.compile(r"\b(doi:|10\.\d{4,9}/|arxiv:)\b", re.IGNORECASE)


def available_domain_extractors() -> tuple[str, ...]:
    """Return stable names for built-in deterministic extractor domains."""
    return (
        "equation",
        "units",
        "probability",
        "tolerance",
        "api_contract",
        "failing_test",
        "citation",
    )


def extract_invariants(content: str, *, line_offset: int = 0) -> list[InvariantMarker]:
    """Extract deterministic invariant markers from text content."""
    markers: list[InvariantMarker] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        for kind in extract_line_invariant_kinds(stripped, lowered=lowered):
            markers.append(
                InvariantMarker(kind=kind, text=stripped, line_start=line_offset + line_number)
            )
    return markers


def extract_line_invariant_kinds(line: str, *, lowered: str | None = None) -> tuple[str, ...]:
    """Return invariant kinds detected for one source line."""
    normalized = lowered if lowered is not None else line.lower()
    kinds: list[str] = []
    if _is_equation_line(line):
        kinds.append("equation")
    if _is_units_line(normalized):
        kinds.append("units")
    if "prior" in normalized:
        kinds.append("prior")
    if "likelihood" in normalized:
        kinds.append("likelihood")
    if _is_tolerance_line(normalized):
        kinds.append("tolerance")
    if _is_api_contract_line(normalized):
        kinds.append("api_contract")
    if _is_failing_test_line(normalized):
        kinds.append("failing_test")
    if _is_citation_line(line, normalized):
        kinds.append("citation")
    return tuple(kinds)


def _is_equation_line(line: str) -> bool:
    if _EQUATION_WORD_RE.search(line):
        return True
    if "=" not in line or "==" in line:
        return False
    left, right = line.split("=", maxsplit=1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        return False
    if right.startswith(('"', "'", "{", "[")):
        return False
    if not _EQUATION_LHS_RE.fullmatch(left):
        return False
    math_signals = ("^", "\\", "_", "*", "/", "+", "-", " sin", " cos", " exp", " log", " sqrt")
    return any(signal in f" {right.lower()}" for signal in math_signals)


def _is_units_line(lowered: str) -> bool:
    return "unit" in lowered or "cgs" in lowered or "si " in lowered


def _is_tolerance_line(lowered: str) -> bool:
    return "tolerance" in lowered or "tol=" in lowered or "rtol" in lowered or "atol" in lowered


def _is_api_contract_line(lowered: str) -> bool:
    return "api" in lowered or "schema" in lowered or "contract" in lowered


def _is_failing_test_line(lowered: str) -> bool:
    return "traceback" in lowered or "failed" in lowered or "error:" in lowered


def _is_citation_line(line: str, lowered: str) -> bool:
    return "citation" in lowered or _DOI_RE.search(line) is not None
