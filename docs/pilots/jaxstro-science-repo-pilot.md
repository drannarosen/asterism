# Pilot Runbook: Science jaxstro Repository

Purpose: pilot Asterism on one private science repository without making Asterism depend on
jaxstro, Brain, OmniBrain, or private source material.

This runbook is intentionally repo-agnostic. Choose the target repository at pilot time, then run
the commands inside that repository with Asterism installed from the public package checkout.

## Preconditions

- Use a private working copy of the target science repository.
- Do not commit generated `evidence-pack.md`, `evidence-pack.json`, or `.asterism/` into the
  target repository unless Anna explicitly approves a sanitized artifact.
- Confirm the target repository already ignores local generated artifacts, or add local-only excludes.
- Do not publish private source paths, retrieval blobs, logs, pack JSON, or Markdown output.
- Use deterministic profiles only; do not add ML compression, remote inference, or model calls.

## Recommended First Pilot

Start with the `handoff` profile for a broad scientific context handoff:

```bash
uv run --extra dev asterism pack . \
  --profile handoff \
  --task "Pilot Asterism handoff pack for this science repository" \
  --out evidence-pack.md \
  --json evidence-pack.json

uv run --extra dev asterism inspect evidence-pack.json
uv run --extra dev asterism audit evidence-pack.json --store .asterism/store
```

Then exercise retrieval on one high-value hit:

```bash
uv run --extra dev asterism search evidence-pack.json likelihood --limit 10
uv run --extra dev asterism search evidence-pack.json units --limit 10
uv run --extra dev asterism search evidence-pack.json tolerance --limit 10
uv run --extra dev asterism retrieve <retrieval-key> --store .asterism/store
```

## Success Criteria

- `asterism pack` completes without exposing secret-looking content in JSON, Markdown, or the
  retrieval store.
- `asterism inspect` reports an embedded audit summary.
- `asterism audit` exits successfully with 0 errors.
- Any warnings are understood and documented; duplicate retrieval-key warnings are acceptable when
  identical bytes appear in multiple files.
- Search returns relevant scientific material for at least two of: equations, units, priors,
  likelihoods, tolerances, failing tests, API contracts, citations.
- At least one retrieved chunk exactly matches the corresponding source lines.
- The first page of Markdown is usable as an agent handoff: high-value source/test/context files
  appear before generated or dependency-lock material.

## Stop Conditions

Stop the pilot and fix Asterism before broader use if any of these occur:

- Audit errors for missing or tampered retrieval blobs.
- Secret-looking content appears in pack JSON, Markdown, or retrieval output.
- Generated files or dependency lockfiles dominate the first handoff section for the chosen profile.
- Source line spans, byte spans, hashes, git commits, or retrieval keys are missing or inconsistent.
- Exact retrieval fails for any selected source chunk.

## Pilot Notes To Capture

Record the following in a private pilot note:

- Target repository name and commit SHA.
- Asterism commit SHA.
- Profile and task intent.
- Pack id, item count, retrieval-key count, omitted-material count.
- Audit status, error count, warning count, and warning codes.
- Three search queries tried and whether results were useful.
- One retrieval key tested and the source path/line span it restored.
- Any missing extractor domains or noisy false positives.

## Public Follow-Up Boundary

Only move learnings back into `drannarosen/asterism` as public-safe code, tests, docs, or synthetic
fixtures. Do not copy private source text, private paths, unpublished results, credentials, or private
pack artifacts into the public package.
