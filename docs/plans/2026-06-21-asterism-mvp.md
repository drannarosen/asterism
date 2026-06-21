# Asterism MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first public Python package skeleton for Asterism with deterministic EvidencePack creation,
provenance records, exact content retrieval, Markdown/JSON output, and a basic CLI.

**Architecture:** The package is a small library with a Typer CLI. `packer.py` walks a local directory using
ignore rules, stores exact text chunks in `RetrievalStore`, and assembles pydantic models from `evidence.py`
and `provenance.py`. `render.py` owns Markdown output; JSON output uses the schema models directly.

**Tech Stack:** Python 3.11+, pydantic, typer, rich, pathspec, pytest, ruff.

---

### Task 1: Package Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `README.md`
- Create: `src/asterism/__init__.py`
- Create: `src/asterism/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write the smoke tests**

```python
from typer.testing import CliRunner

from asterism.cli import app


def test_cli_help_renders():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "pack" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: fail because the package does not exist yet.

**Step 3: Write the skeleton**

Create package metadata, dependencies, CLI entrypoint, package exports, README, license, and ignore rules.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: pass.

**Step 5: Commit**

```bash
git add pyproject.toml .gitignore LICENSE README.md src/asterism tests/test_cli.py
git commit -m "feat: scaffold python package"
```

### Task 2: Exact Retrieval Store

**Files:**
- Create: `src/asterism/retrieve.py`
- Create: `tests/test_retrieve.py`

**Step 1: Write retrieval tests**

```python
from asterism.retrieve import RetrievalStore


def test_store_puts_and_retrieves_exact_text(tmp_path):
    store = RetrievalStore(tmp_path / "store")
    key = store.put_text("alpha\nbeta\n", source_path="notes.txt")

    assert key.startswith("sha256:")
    assert store.retrieve_text(key) == "alpha\nbeta\n"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieve.py -v`
Expected: fail because `RetrievalStore` is not implemented.

**Step 3: Implement minimal retrieval**

Implement SHA-256 keys, atomic-ish blob writes, byte retrieval, text retrieval, and missing-key errors.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_retrieve.py -v`
Expected: pass.

**Step 5: Commit**

```bash
git add src/asterism/retrieve.py tests/test_retrieve.py
git commit -m "feat: add exact retrieval store"
```

### Task 3: EvidencePack Schemas

**Files:**
- Create: `src/asterism/provenance.py`
- Create: `src/asterism/evidence.py`
- Create: `tests/test_evidence.py`

**Step 1: Write schema tests**

```python
from asterism.evidence import EvidencePack, EvidenceItem
from asterism.provenance import FileProvenance


def test_evidence_pack_round_trips_json():
    item = EvidenceItem(
        kind="file",
        title="notes.txt",
        provenance=FileProvenance(path="notes.txt", sha256="abc", retrieval_key="sha256:abc"),
        summary="Stored exactly.",
    )
    pack = EvidencePack(id="pack-demo", source_scope=".", items=[item])

    restored = EvidencePack.model_validate_json(pack.model_dump_json())
    assert restored.items[0].provenance.path == "notes.txt"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_evidence.py -v`
Expected: fail because schemas are not implemented.

**Step 3: Implement schemas**

Implement pydantic models for provenance, evidence items, invariant markers, omitted material, and packs. Add
`write_json()` and `write_markdown()` convenience methods on `EvidencePack`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_evidence.py -v`
Expected: pass.

**Step 5: Commit**

```bash
git add src/asterism/provenance.py src/asterism/evidence.py tests/test_evidence.py
git commit -m "feat: add evidence pack schemas"
```

### Task 4: Local Directory Packer

**Files:**
- Create: `src/asterism/packer.py`
- Create: `tests/test_packer.py`
- Modify: `src/asterism/__init__.py`

**Step 1: Write packer tests**

```python
from asterism import PackOptions, pack_directory
from asterism.retrieve import RetrievalStore


def test_pack_directory_records_file_provenance_and_retrieval(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("Equation: E = mc^2\nunits: cgs\n", encoding="utf-8")

    pack = pack_directory(root, options=PackOptions(store_path=root / ".asterism" / "store"))

    assert len(pack.items) == 1
    item = pack.items[0]
    assert item.provenance.path == "notes.md"
    assert any(marker.kind == "equation" for marker in item.invariants)
    store = RetrievalStore(root / ".asterism" / "store")
    assert store.retrieve_text(item.provenance.retrieval_key) == "Equation: E = mc^2\nunits: cgs\n"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_packer.py -v`
Expected: fail because `pack_directory` is not implemented.

**Step 3: Implement minimal packer**

Implement `PackOptions`, deterministic directory walking, pathspec ignore support, binary-file skipping,
content hashing, line counts, git commit detection, and simple invariant markers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_packer.py -v`
Expected: pass.

**Step 5: Commit**

```bash
git add src/asterism/packer.py src/asterism/__init__.py tests/test_packer.py
git commit -m "feat: pack local directories"
```

### Task 5: Rendering And CLI Commands

**Files:**
- Create: `src/asterism/render.py`
- Modify: `src/asterism/evidence.py`
- Modify: `src/asterism/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Write CLI tests**

```python
from typer.testing import CliRunner

from asterism.cli import app


def test_pack_inspect_and_retrieve_cli(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("likelihood: gaussian\n", encoding="utf-8")
    md_out = tmp_path / "pack.md"
    json_out = tmp_path / "pack.json"

    runner = CliRunner()
    result = runner.invoke(app, ["pack", str(root), "--out", str(md_out), "--json", str(json_out)])
    assert result.exit_code == 0
    assert md_out.exists()
    assert json_out.exists()

    inspect = runner.invoke(app, ["inspect", str(json_out)])
    assert inspect.exit_code == 0
    assert "EvidencePack" in inspect.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: fail until rendering and CLI implementation are complete.

**Step 3: Implement rendering and commands**

Implement Markdown rendering, `pack`, `inspect`, and `retrieve` commands. Keep output deterministic and concise.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: pass.

**Step 5: Commit**

```bash
git add src/asterism/render.py src/asterism/evidence.py src/asterism/cli.py tests/test_cli.py
git commit -m "feat: add evidence pack cli"
```

### Task 6: Polish And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-06-21-asterism-mvp.md`

**Step 1: Run full verification**

Run:

```bash
pytest
ruff check .
python -m asterism.cli --help
```

Expected: all pass.

**Step 2: Pack the repository itself**

Run:

```bash
asterism pack . --out evidence-pack.md --json evidence-pack.json
asterism inspect evidence-pack.json
```

Expected: pack and JSON are created, inspect prints item and retrieval counts.

**Step 3: Update docs**

Update README with installation, CLI examples, Python API examples, current limitations, and the public repo
target `drannarosen/asterism`.

**Step 4: Commit**

```bash
git add README.md docs/plans/2026-06-21-asterism-mvp.md
git commit -m "docs: document asterism mvp usage"
```
