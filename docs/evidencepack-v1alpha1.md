# EvidencePack v1alpha1 Format

`asterism.evidencepack.v1alpha1` is the first public EvidencePack wire format. It is intentionally small:
the format stabilizes provenance, retrieval keys, and deterministic serialization before Asterism grows a
larger scientific compression layer.

## Compatibility Promise

While the schema is marked `v1alpha1`, Asterism treats the following as compatibility-sensitive:

- serialized field names;
- `schema_version`;
- retrieval key syntax;
- SHA-256 digest semantics;
- relative source path semantics;
- line-span semantics;
- canonical JSON output from `EvidencePack.to_canonical_json()`.

Breaking any of those requires a new `schema_version`.

## Top-Level Object

An EvidencePack JSON object has these fields:

| Field | Type | Required | Meaning |
|:--|:--|:--|:--|
| `schema_version` | string literal | yes | Must be `asterism.evidencepack.v1alpha1`. |
| `id` | string | yes | Stable-ish pack identifier generated from packed source content. |
| `profile` | string | yes | Deterministic pack profile used to construct the pack. Defaults to `repo`. |
| `source_scope` | string | yes | Source scope label or path that was packed. |
| `task_intent` | string or null | yes | Optional user intent for the pack. |
| `created_at` | RFC 3339 datetime | yes | Pack creation timestamp. |
| `items` | array | yes | Provenance-bearing evidence items. |
| `omitted_material` | array | yes | Explicit records for skipped or omitted material. |
| `audit_status` | string | yes | Current audit status. MVP packs default to `draft`. |
| `audit_summary` | object or null | yes | Compact audit counts when a pack was audited during creation. |

`id`, `profile`, and `source_scope` must not be empty.

Current profile names are `repo`, `debug`, `review`, and `handoff`.

## Evidence Items

Each `items[]` entry has:

| Field | Type | Required | Meaning |
|:--|:--|:--|:--|
| `kind` | string | yes | Current MVP emits `file`. |
| `title` | string | yes | Human-readable item title, usually the relative path. |
| `provenance` | object | yes | Exact source provenance. |
| `summary` | string | yes | Deterministic item summary. |
| `invariants` | array | yes | Deterministic markers for content that should be preserved carefully. |

`kind` and `title` must not be empty.

## File Provenance

Each `provenance` object has:

| Field | Type | Required | Meaning |
|:--|:--|:--|:--|
| `path` | relative POSIX path | yes | Path relative to the packed source root. Absolute paths are invalid. |
| `granularity` | string | yes | `file` for a whole file or `line_chunk` for a deterministic line chunk. |
| `sha256` | lowercase hex string | yes | SHA-256 digest of the exact stored bytes. |
| `retrieval_key` | string | yes | Must be `sha256:<sha256>`. |
| `chunk_index` | integer | yes | Zero-indexed chunk position for this source path. |
| `chunk_count` | integer | yes | Total chunks emitted for this source path. |
| `line_start` | integer | yes | First source line represented by this item, 1-indexed. |
| `line_end` | integer or null | yes | Last source line represented by this item. Must be >= `line_start` when present. |
| `byte_start` | integer | yes | First source byte offset represented by this item, zero-indexed. |
| `byte_end` | integer or null | yes | Exclusive byte end offset represented by this item. Must be >= `byte_start` when present. |
| `byte_length` | integer | yes | Length of exact stored bytes. |
| `char_length` | integer | yes | Length of decoded text in Python characters. |
| `git_commit` | string or null | yes | Lowercase 40-character commit SHA when available. |

The `sha256` field is computed from stored bytes, not normalized text. `retrieval_key` must use the same digest.
For `file` granularity, `chunk_index` must be `0` and `chunk_count` must be `1`. For `line_chunk` granularity,
`chunk_index` must be less than `chunk_count`.

## Invariant Markers

Each `invariants[]` entry has:

| Field | Type | Required | Meaning |
|:--|:--|:--|:--|
| `kind` | string | yes | Marker family, such as `equation`, `units`, or `likelihood`. |
| `text` | string | yes | Matched source text. |
| `line_start` | integer or null | yes | First source line for the marker. |
| `line_end` | integer or null | yes | Last source line for the marker. |

Invariant markers are advisory in `v1alpha1`. Exact retrieval is the correctness guarantee.
Built-in deterministic extractor domains are `equation`, `units`, `probability`,
`tolerance`, `api_contract`, `failing_test`, and `citation`.

## Omitted Material

Each `omitted_material[]` entry has:

| Field | Type | Required | Meaning |
|:--|:--|:--|:--|
| `reason` | string | yes | Why the material was not represented as an evidence item. |
| `retrieval_key` | string or null | yes | Retrieval key if exact content is still stored. |
| `source_path` | string or null | yes | Source path associated with the omission. |

The MVP records omissions for unreadable, oversized, binary, or non-UTF-8 files.

## Audit Summary

When present, `audit_summary` contains compact counts from the retrieval-integrity audit run during
pack creation:

| Field | Type | Required | Meaning |
|:--|:--|:--|:--|
| `status` | string | yes | Audit status such as `passed`, `passed_with_warnings`, or `failed`. |
| `checked_items` | integer | yes | Number of evidence items checked. |
| `checked_retrieval_keys` | integer | yes | Number of retrieval keys checked. |
| `errors` | integer | yes | Count of audit errors. |
| `warnings` | integer | yes | Count of audit warnings. |

The detailed finding list remains the responsibility of `asterism audit`; the pack embeds only summary
counts so JSON and Markdown handoffs can surface integrity state without rerunning the audit.

## Canonical JSON

`EvidencePack.to_canonical_json()` emits indented JSON with sorted object keys. `EvidencePack.write_json()`
writes that canonical JSON plus a trailing newline.

The canonical example is [examples/evidencepack-v1alpha1.json](../examples/evidencepack-v1alpha1.json).

## Retrieval Key Semantics

Retrieval keys currently have one supported form:

```text
sha256:<64 lowercase hex characters>
```

The key identifies the exact bytes stored in the local retrieval store. A retrieval implementation must return
those bytes unchanged or fail explicitly.
