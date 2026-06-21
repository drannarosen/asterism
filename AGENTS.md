# Asterism Agent Instructions

These instructions apply to the entire repository.

## Mission

Asterism is a standalone public Python package for scientific context reduction. It emits deterministic,
provenance-preserving `EvidencePack`s and supports exact retrieval of original content by key.

The package target is `drannarosen/asterism`. Do not place it under the `jaxstro` organization.

## Non-Negotiable Invariants

- Asterism must not depend on Anna's private Brain repository or private local paths.
- Brain/OmniBrain integration belongs in a later adapter, not in the core package.
- Python is the primary implementation for the MVP.
- Rust may only be added later as an optional accelerator backend.
- v0.1 must stay deterministic. Do not add ML compression, learned summaries, remote inference, or model calls.
- Exact retrieval is the hard guarantee. Any packed source content must be recoverable byte-for-byte by its retrieval key.
- Preserve scientific correctness details: equations, units, coordinate conventions, priors, likelihoods,
  numerical tolerances, failing tests, API contracts, citations, source paths, line spans, git commits,
  content hashes, and retrieval keys.

## Development Workflow

- Work directly on `main` by default. Do not create feature branches or git worktrees unless Anna explicitly asks.
- Use `uv` for environment and command execution.
- Keep the package installable from a fresh checkout with:

```bash
uv sync --extra dev
```

- Run commands through `uv run --extra dev ...` unless there is a specific reason not to.
- Keep dependencies intentional and public-package appropriate. Do not add a new dependency without a clear reason.
- Do not commit generated pack output, retrieval stores, virtual environments, caches, or local worktrees.

## Required Checks

Before claiming work is complete, run:

```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check .
```

For CLI or packing changes, also run:

```bash
uv run --extra dev python -m asterism.cli --help
uv run --extra dev asterism pack . --out evidence-pack.md --json evidence-pack.json
uv run --extra dev asterism inspect evidence-pack.json
```

Generated `evidence-pack.md`, `evidence-pack.json`, and `.asterism/` are ignored and should stay untracked.

## Code Boundaries

- Public library exports live in `src/asterism/__init__.py`.
- CLI behavior lives in `src/asterism/cli.py`.
- Schema models live in `src/asterism/evidence.py` and `src/asterism/provenance.py`.
- Local directory packing lives in `src/asterism/packer.py`.
- Exact retrieval lives in `src/asterism/retrieve.py`.
- Markdown rendering lives in `src/asterism/render.py`.

When changing any public API, update tests and README examples in the same commit.

## Schema And Retrieval Rules

- Keep `EvidencePack.schema_version` explicit.
- Do not silently change serialized field names or retrieval key format.
- Retrieval keys are currently `sha256:<hex-digest>`.
- Hashes must be computed from exact stored bytes, not normalized text.
- If content is omitted, record why in `omitted_material`.
- Binary or non-UTF-8 files may be skipped in the MVP, but the omission must be explicit.

## Testing Rules

- Add or update focused tests for every behavior change.
- Prefer temporary directories for packer and retrieval tests.
- Tests must not depend on network access, user-specific paths, or private repositories.
- Tests should verify exact retrieval, not only metadata shape.

## Git And GitHub

- Commit meaningful completed slices on `main`.
- Keep `git status -sb` clean before handing work back.
- The intended remote is `git@github.com:drannarosen/asterism.git` or `https://github.com/drannarosen/asterism.git`.
- Ask before using credentials, creating remotes, pushing, publishing packages, or calling external services unless
  Anna has explicitly approved that action in the current session.

## Public Package Hygiene

- Do not commit secrets, access tokens, private notes, private source material, or local absolute paths.
- Keep README and examples suitable for a public repository.
- Keep error messages useful but avoid exposing private machine details beyond normal Python tracebacks.
- Prefer clear, boring interfaces over clever abstractions.
