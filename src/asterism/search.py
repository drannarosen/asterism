"""Deterministic EvidencePack metadata search."""

from __future__ import annotations

from dataclasses import dataclass

from asterism.evidence import EvidenceItem, EvidencePack


@dataclass(frozen=True)
class SearchHit:
    """A deterministic metadata search hit for an EvidencePack item."""

    item: EvidenceItem
    score: int
    matched_fields: tuple[str, ...]


def search_pack(pack: EvidencePack, query: str, *, limit: int = 20) -> list[SearchHit]:
    """Search pack metadata and return ranked evidence-item hits."""
    normalized_query = query.strip().casefold()
    if not normalized_query:
        raise ValueError("query must not be empty")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    hits: list[SearchHit] = []
    for item in pack.items:
        score, matched_fields = _score_item(item, normalized_query)
        if score == 0:
            continue
        hits.append(SearchHit(item=item, score=score, matched_fields=matched_fields))

    hits.sort(
        key=lambda hit: (
            -hit.score,
            hit.item.provenance.path,
            hit.item.provenance.chunk_index,
            hit.item.title,
        )
    )
    return hits[:limit]


def _score_item(item: EvidenceItem, query: str) -> tuple[int, tuple[str, ...]]:
    score = 0
    matched_fields: list[str] = []
    for field_name, value, weight in _search_fields(item):
        if query not in value.casefold():
            continue
        score += weight
        matched_fields.append(field_name)
    return score, tuple(dict.fromkeys(matched_fields))


def _search_fields(item: EvidenceItem) -> list[tuple[str, str, int]]:
    provenance = item.provenance
    fields = [
        ("path", provenance.path, 100),
        ("title", item.title, 90),
        ("kind", item.kind, 60),
        ("summary", item.summary, 50),
        ("granularity", provenance.granularity, 40),
        ("sha256", provenance.sha256, 30),
        ("retrieval_key", provenance.retrieval_key, 30),
    ]
    if provenance.git_commit:
        fields.append(("git_commit", provenance.git_commit, 20))
    for marker in item.invariants:
        fields.append(("invariant_kind", marker.kind, 70))
        fields.append(("invariant_text", marker.text, 70))
    return fields
