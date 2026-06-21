# Asterism Overview And Next Steps

Last updated: 2026-06-21

## Human-Readable Overview

Asterism is a deterministic context-reduction engine for scientific software projects. Its job is
to turn a local repository into an `EvidencePack`: a compact handoff artifact that preserves where
important context came from and how to retrieve the exact original bytes later.

The central design principle is that compression must not break scientific correctness. Asterism
does not summarize with a model in the MVP. Instead, it records provenance, hashes, line spans,
byte spans, git commits, retrieval keys, and conservative invariant markers for scientific details
such as equations, units, priors, likelihoods, numerical tolerances, failing tests, API contracts,
citations, and source paths.

The current package is Python-first, standalone, public-package safe, and independent of Brain,
OmniBrain, and jaxstro. Private workflows can use it, but the package itself does not depend on
private repositories.

## What It Can Do Now

- Pack a local directory into Markdown and canonical JSON EvidencePack output.
- Store exact source chunks in a local SHA-256 content-addressed retrieval store.
- Retrieve exact stored chunks by `sha256:<digest>` retrieval key.
- Track file provenance: relative path, line span, byte span, chunk index/count, byte length,
  character length, git commit, SHA-256 digest, and retrieval key.
- Emit deterministic line chunks for larger files.
- Respect ignore rules, including nested `.gitignore` files.
- Explicitly omit oversized files, binary/non-UTF-8 files, symlinks, and secret-looking text.
- Audit retrieval integrity and embed compact audit summary counts in pack output.
- Search EvidencePack metadata for paths, invariants, hashes, and retrieval keys.
- Render Markdown as an agent handoff view with invariant counts, retrieval commands, omissions,
  and audit summary.
- Use semantic profiles: `repo`, `debug`, `review`, and `handoff`.
- Prioritize profile-relevant chunks earlier in pack output without changing exact retrieval.
- Run deterministic extractors for scientific invariant domains.

## Current Quality

The package is in a strong MVP state. It has a clean public package layout, strict mypy enabled,
Ruff linting, focused tests across schema, provenance, packing, retrieval, CLI, audit, search,
rendering, and extractors, plus a dogfood run on the public Asterism repository itself.

The hard guarantee is exact retrieval, not semantic compression. That is the right foundation:
scientific users can trust the pack because stored bytes can be recovered and audited. The current
extractors are conservative and intentionally simple; they are useful for prioritization and handoff,
but not yet a full scientific parser.

## Known Limits

- Extractors are heuristic and deterministic, not domain-complete.
- Search operates over EvidencePack metadata and invariant markers, not full-text retrieval-store
  content.
- The local retrieval store is filesystem-based; there is no portable bundle format yet.
- There is no installed CI workflow yet.
- There is no published PyPI release yet.
- Rust acceleration is intentionally absent until the Python contract stabilizes.
- Private science-repository pilot artifacts must stay private unless explicitly sanitized.

## Next High-Leverage Steps

1. Pilot on one private science jaxstro repository.

   Use `docs/pilots/jaxstro-science-repo-pilot.md`. This is the highest-value next step because
   it will expose the real failure modes: noisy extractors, missing ignores, awkward handoff shape,
   retrieval-store ergonomics, and whether profile ordering helps with actual scientific work.

2. Add CI for the public repository.

   Add a GitHub Actions workflow that runs tests, Ruff, mypy, and a CLI pack/inspect/audit smoke.
   This turns the current local quality gate into a public maintenance guardrail.

3. Add a portable pack bundle command.

   A pilot user will eventually want one artifact that contains `evidence-pack.json`,
   `evidence-pack.md`, and the retrieval blobs needed by that pack. A command like
   `asterism bundle evidence-pack.json --store .asterism/store --out pack.tar.zst` would make
   handoff more practical.

4. Improve extractor precision using pilot evidence.

   Add small deterministic extractors for common scientific file types and patterns: Python tests,
   Markdown/Quarto equations, BibTeX/citations, YAML/TOML configs, and simulation logs. Keep these
   rule-based and covered by synthetic fixtures.

5. Add a private-pilot report template.

   The runbook says what to record, but a template would make the first jaxstro pilot faster and
   more consistent while keeping private material out of the public repo.

6. Add release hygiene.

   Before publishing, add a changelog, package build check, license/readme metadata check, and a
   first version tag process. This can wait until after the first private pilot validates the API.

## Recommended Immediate Sequence

1. Run the jaxstro pilot locally and privately.
2. Convert only public-safe learnings into synthetic tests and extractor improvements.
3. Add CI once the first pilot-driven fixes land.
4. Reassess whether `EvidencePack v1alpha1` needs a small schema revision before any package
   release.
