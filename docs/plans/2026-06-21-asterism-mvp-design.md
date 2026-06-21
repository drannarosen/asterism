# Asterism MVP Design

**Date:** 2026-06-21
**Status:** approved for first build
**Owner:** Anna Rosen

## Goal

Build the first public skeleton of Asterism: a standalone Python package that creates deterministic,
provenance-preserving EvidencePacks from local directories and retrieves exact omitted content by key.

## Public Positioning

Asterism is a scientific context-reduction engine. It compresses context for focus and cost, but preserves the
details that can change a scientific conclusion: equations, units, priors, likelihoods, numerical tolerances,
failing tests, API contracts, citations, source paths, line spans, git commits, and retrieval keys.

The package is public and standalone under Anna's personal GitHub account, `drannarosen/asterism`. It must not
depend on Anna's private Brain repository. Brain and OmniBrain integrations should arrive later as adapters.

## Chosen MVP Approach

Use a schema-backed, CLI-first Python package with a pleasant public interface:

- `pydantic` for explicit pack and provenance schemas.
- `typer` for the command-line interface.
- `rich` for readable inspection output.
- `pathspec` for gitignore-compatible file selection.
- Standard-library hashing, JSON, pathlib, subprocess, and filesystem storage for the retrieval core.

This is better than a stdlib-only skeleton because the first public API should be clear, typed, and easy to use.
The conceptual model should still stay independent of the implementation libraries so later backends can evolve.

## Public API Shape

```python
from pathlib import Path

from asterism import EvidencePack, PackOptions, pack_directory
from asterism.retrieve import RetrievalStore

pack = pack_directory(
    Path("."),
    options=PackOptions(profile="repo", include_git=True),
)

pack.write_json("evidence-pack.json")
pack.write_markdown("evidence-pack.md")

store = RetrievalStore(".asterism/store")
text = store.retrieve_text("sha256:<hash>")
```

## CLI Shape

```bash
asterism pack PATH --out evidence-pack.md --json evidence-pack.json
asterism inspect evidence-pack.json
asterism retrieve sha256:<hash> --store .asterism/store
```

## Core Modules

- `asterism.evidence`: `EvidencePack`, `EvidenceItem`, `PreservedInvariant`, and omitted-material records.
- `asterism.provenance`: source paths, line spans, git commit metadata, content hashes, and retrieval keys.
- `asterism.packer`: local directory/repo walker, ignore handling, chunking, hashing, and pack assembly.
- `asterism.retrieve`: content-addressed exact retrieval store.
- `asterism.render`: Markdown and JSON rendering.
- `asterism.cli`: Typer application and user-facing commands.

## Storage Model

The first retrieval store is local and content-addressed:

```text
.asterism/store/blobs/sha256/<hash>
```

Each stored chunk is addressed as `sha256:<hash>`. EvidencePack JSON records the retrieval key, source path,
line span, byte length, character length, and content hash. Retrieval must return the exact bytes or text that
were packed.

## Deterministic v0.1 Scope

The first vertical slice includes:

- package skeleton and CLI entrypoint;
- `EvidencePack` schema;
- local directory/repo packer;
- file provenance records;
- content hashing;
- exact chunk retrieval store;
- Markdown and JSON output;
- `asterism pack`, `asterism retrieve`, and `asterism inspect`;
- focused tests for pack creation and exact retrieval.

The MVP does not include ML compression, Brain integration, Rust acceleration, MCP tools, paper equation
extraction, symbol graphs, hot-path proxying, or remote storage.

## Scientific Correctness Invariants

The packer should begin by preserving provenance and exact retrieval for every included text file. It should
also classify likely scientific invariants using deterministic pattern markers so the output highlights content
that should not be compressed casually. Initial marker families:

- equations and formulas;
- units and coordinate conventions;
- priors, likelihoods, parameters, and tolerances;
- failing tests and root errors;
- API contracts and schemas;
- citations, source paths, line spans, git commits, and retrieval keys.

These markers are advisory in the first slice. The hard correctness guarantee is exact retrieval.

## Testing Strategy

Use pytest with temporary directories. Tests should verify:

- creating a pack from a local directory produces stable file provenance and retrieval keys;
- retrieving a stored key returns exact original content;
- ignored directories such as `.git`, `.asterism`, caches, and virtual environments are skipped;
- JSON and Markdown outputs can be produced by the library and CLI.

## Open Questions After First Slice

- Should the stable on-disk pack format be versioned as `evidencepack/v1` before any public release?
- How aggressively should the deterministic invariant detector classify scientific text in v0.1?
- Should retrieval keys include file-relative aliases in addition to content hashes?
- Which project should be the first dogfood pack after the package can pack itself?
