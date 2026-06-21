# Asterism

Asterism is a scientific context-reduction engine. It builds deterministic,
provenance-preserving EvidencePacks from local projects and keeps exact retrieval
keys for the source material it stores.

The first public package is Python-first and standalone. It does not depend on
Anna's private Brain repository; Brain and OmniBrain workflows will be adapters
later.

## Install

```bash
python -m pip install -e ".[dev]"
```

## CLI

```bash
asterism --help
```

## Current Scope

The MVP focuses on deterministic local directory packing, file provenance,
content hashing, exact retrieval, and Markdown/JSON output. It intentionally
does not include ML compression or Rust acceleration yet.
