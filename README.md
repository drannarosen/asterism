# Asterism

Asterism is a scientific context-reduction engine. It builds deterministic,
provenance-preserving EvidencePacks from local projects and keeps exact retrieval
keys for the source material it stores.

The first public package is Python-first and standalone. It does not depend on
Anna's private Brain repository; Brain and OmniBrain workflows will be adapters
later.

## Install

```bash
uv sync --extra dev
```

## CLI

Build Markdown and JSON packs from a local directory:

```bash
uv run asterism pack . --profile repo --out evidence-pack.md --json evidence-pack.json
```

List the deterministic profile presets:

```bash
uv run asterism profiles
```

Inspect a JSON pack:

```bash
uv run asterism inspect evidence-pack.json
```

Audit schema-valid pack metadata and retrieval integrity:

```bash
uv run asterism audit evidence-pack.json --store .asterism/store
```

Retrieve exact original content by key:

```bash
uv run asterism retrieve sha256:<hash> --store .asterism/store
```

## Python API

```python
from pathlib import Path

from asterism import PackOptions, RetrievalStore, pack_directory

pack = pack_directory(
    Path("."),
    options=PackOptions(profile="repo", include_git=True),
)

pack.write_markdown("evidence-pack.md")
pack.write_json("evidence-pack.json")

store = RetrievalStore(".asterism/store")
text = store.retrieve_text(pack.items[0].provenance.retrieval_key)
```

## Current Scope

The MVP focuses on deterministic local directory packing, file provenance,
content hashing, exact retrieval, and Markdown/JSON output. It intentionally
does not include ML compression or Rust acceleration yet.

Pack profiles currently include `repo`, `debug`, `review`, and `handoff`. They
set deterministic chunk sizes, max file sizes, generated-output ignores, and
document which invariant families the profile is meant to emphasize.

Files can be represented as whole-file records or deterministic line chunks.
Each record carries line spans, byte spans, chunk index/count, SHA-256 digest,
and an exact retrieval key.

The scientific invariant detector is deliberately conservative and deterministic.
It marks lines that look like equations, units, priors, likelihoods, tolerances,
API contracts, citations, or failures, but the hard v0.1 guarantee is exact
retrieval from content-addressed storage.

For public-package safety, files that are too large, binary or non-UTF-8,
symlinks, and secret-looking text files are omitted explicitly rather than
stored. Secret-looking content is not written to the retrieval store.

The current wire format is documented in
[docs/evidencepack-v1alpha1.md](docs/evidencepack-v1alpha1.md), with a canonical
example at [examples/evidencepack-v1alpha1.json](examples/evidencepack-v1alpha1.json).
JSON output is the canonical machine-readable record; Markdown output is an
agent handoff view with retrieval commands, invariant counts, and omission
summaries.

## Public Repository Target

This package is intended for `drannarosen/asterism`.
