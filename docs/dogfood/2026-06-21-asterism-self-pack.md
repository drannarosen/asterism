# Dogfood: Asterism Self-Pack

Date: 2026-06-21

Repository: `drannarosen/asterism`

## Purpose

Exercise Asterism on a real public repository without touching private Brain or jaxstro material.
This run used Asterism itself as the first non-private dogfood target.

## Commands Run

```bash
uv run --extra dev asterism pack . --profile handoff \
  --task "Dogfood Asterism on its own public repository" \
  --out evidence-pack.md \
  --json evidence-pack.json

uv run --extra dev asterism inspect evidence-pack.json
uv run --extra dev asterism audit evidence-pack.json --store .asterism/store
uv run --extra dev asterism search evidence-pack.json profile --limit 5
uv run --extra dev asterism retrieve \
  sha256:0207af787d7260681348ac2c340b3b7b596568e3f39ecdd8bddb573c85eab4e1 \
  --store .asterism/store
```

## Results

- Pack succeeded: `asterism-add9c7847582`.
- Profile: `handoff`.
- Items: 37.
- Retrieval keys: 37.
- Omitted material: 0.
- Audit passed with 0 errors.
- Audit reported 1 warning: duplicate stored bytes for identical fixture/example content.
- Search returned relevant profile-related hits in `src/asterism/packer.py` and `tests/test_packer.py`.
- Exact retrieval returned the selected `src/asterism/packer.py` chunk.

## Quality Notes

- The dogfood run caught a real quality issue: broad equation detection was causing lockfile assignments
  to dominate profile-prioritized handoff output.
- The detector was tightened so quoted/bracketed lockfile assignments are not treated as equations.
- After the fix, the generated handoff prioritized Asterism source and tests instead of `uv.lock`.

## Follow-Up Status

- Done: audit-summary metadata is now embedded in pack output and surfaced by `inspect` and Markdown.
- Done: deterministic domain extractors now own invariant detection outside the packer.
- Next: run a private pilot on one science jaxstro repository, keeping generated packs and retrieval
  stores out of version control unless Anna explicitly chooses a sanitized artifact to publish.
