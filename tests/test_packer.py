from pathlib import Path

import pytest

from asterism import PackOptions, pack_directory
from asterism.retrieve import RetrievalStore


def test_pack_directory_records_file_provenance_and_retrieval(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    content = "Equation: E = mc^2\nunits: cgs\n"
    (root / "notes.md").write_text(content, encoding="utf-8")

    pack = pack_directory(root, options=PackOptions(store_path=root / ".asterism" / "store"))

    assert len(pack.items) == 1
    item = pack.items[0]
    assert item.provenance.path == "notes.md"
    assert item.provenance.line_start == 1
    assert item.provenance.line_end == 2
    assert any(marker.kind == "equation" for marker in item.invariants)
    assert any(marker.kind == "units" for marker in item.invariants)

    store = RetrievalStore(root / ".asterism" / "store")
    assert store.retrieve_text(item.provenance.retrieval_key) == content


def test_pack_directory_chunks_large_text_files_by_line_span(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    content = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    (root / "notes.md").write_text(content, encoding="utf-8")

    pack = pack_directory(
        root,
        options=PackOptions(store_path=root / ".asterism" / "store", chunk_line_count=2),
    )

    assert [item.provenance.line_start for item in pack.items] == [1, 3, 5]
    assert [item.provenance.line_end for item in pack.items] == [2, 4, 5]
    assert [item.provenance.byte_start for item in pack.items] == [0, 14, 28]
    assert [item.provenance.byte_end for item in pack.items] == [14, 28, 35]
    assert [item.provenance.chunk_index for item in pack.items] == [0, 1, 2]
    assert [item.provenance.chunk_count for item in pack.items] == [3, 3, 3]
    assert all(item.provenance.granularity == "line_chunk" for item in pack.items)

    store = RetrievalStore(root / ".asterism" / "store")
    assert store.retrieve_text(pack.items[0].provenance.retrieval_key) == "line 1\nline 2\n"
    assert store.retrieve_text(pack.items[1].provenance.retrieval_key) == "line 3\nline 4\n"
    assert store.retrieve_text(pack.items[2].provenance.retrieval_key) == "line 5\n"


def test_chunked_invariant_markers_keep_source_line_numbers(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    content = "intro\ncontext\nEquation: E = mc^2\nunits: cgs\n"
    (root / "notes.md").write_text(content, encoding="utf-8")

    pack = pack_directory(
        root,
        options=PackOptions(store_path=root / ".asterism" / "store", chunk_line_count=2),
    )

    equation_markers = [
        marker
        for item in pack.items
        for marker in item.invariants
        if marker.kind == "equation"
    ]
    units_markers = [
        marker for item in pack.items for marker in item.invariants if marker.kind == "units"
    ]
    assert [marker.line_start for marker in equation_markers] == [3]
    assert [marker.line_start for marker in units_markers] == [4]


def test_pack_directory_skips_ignored_paths(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "keep.md").write_text("likelihood: gaussian\n", encoding="utf-8")
    (root / ".git").write_text("gitdir: ../.git/worktrees/project\n", encoding="utf-8")
    hidden_store = root / ".asterism"
    hidden_store.mkdir()
    (hidden_store / "generated.md").write_text("skip me\n", encoding="utf-8")
    cache = root / "__pycache__"
    cache.mkdir()
    (cache / "module.pyc").write_bytes(b"\x00\x01")

    pack = pack_directory(root, options=PackOptions(store_path=root / ".asterism" / "store"))

    assert [item.provenance.path for item in pack.items] == ["keep.md"]
    assert any(marker.kind == "likelihood" for marker in pack.items[0].invariants)


def test_pack_directory_applies_debug_profile_defaults(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    content = "".join(f"line {number}\n" for number in range(1, 122))
    (root / "debug.log").write_text(content, encoding="utf-8")

    pack = pack_directory(
        root,
        options=PackOptions(profile="debug", store_path=root / ".asterism" / "store"),
    )

    assert pack.profile == "debug"
    assert len(pack.items) == 2
    assert [item.provenance.line_start for item in pack.items] == [1, 81]
    assert [item.provenance.line_end for item in pack.items] == [80, 121]


def test_pack_directory_profile_can_ignore_generated_outputs(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("api contract\n", encoding="utf-8")
    (root / "coverage.xml").write_text("<coverage />\n", encoding="utf-8")

    pack = pack_directory(
        root,
        options=PackOptions(profile="review", store_path=root / ".asterism" / "store"),
    )

    assert pack.profile == "review"
    assert [item.provenance.path for item in pack.items] == ["notes.md"]


def test_pack_directory_respects_nested_gitignore(tmp_path: Path) -> None:
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / ".gitignore").write_text("ignored.md\nnested/\n", encoding="utf-8")
    (docs / "keep.md").write_text("units: cgs\n", encoding="utf-8")
    (docs / "ignored.md").write_text("do not pack\n", encoding="utf-8")
    nested = docs / "nested"
    nested.mkdir()
    (nested / "also-ignored.md").write_text("do not pack\n", encoding="utf-8")

    pack = pack_directory(root, options=PackOptions(store_path=root / ".asterism" / "store"))

    assert [item.provenance.path for item in pack.items] == ["docs/.gitignore", "docs/keep.md"]


def test_pack_directory_records_large_file_omission(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "large.txt").write_text("too large\n", encoding="utf-8")

    pack = pack_directory(
        root,
        options=PackOptions(store_path=root / ".asterism" / "store", max_file_bytes=4),
    )

    assert pack.items == []
    assert len(pack.omitted_material) == 1
    assert pack.omitted_material[0].source_path == "large.txt"
    assert pack.omitted_material[0].reason == "File exceeds max_file_bytes"


def test_pack_directory_records_binary_file_omission(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "data.bin").write_bytes(b"abc\x00def")

    pack = pack_directory(root, options=PackOptions(store_path=root / ".asterism" / "store"))

    assert pack.items == []
    assert len(pack.omitted_material) == 1
    assert pack.omitted_material[0].source_path == "data.bin"
    assert pack.omitted_material[0].reason == "Binary file"


def test_pack_directory_records_symlink_omission(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = root / "target.md"
    target.write_text("api contract\n", encoding="utf-8")
    link = root / "linked.md"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    pack = pack_directory(root, options=PackOptions(store_path=root / ".asterism" / "store"))

    assert [item.provenance.path for item in pack.items] == ["target.md"]
    assert len(pack.omitted_material) == 1
    assert pack.omitted_material[0].source_path == "linked.md"
    assert pack.omitted_material[0].reason == "Symlink skipped"


def test_pack_directory_omits_secret_looking_content_without_storing_it(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    store_path = root / ".asterism" / "store"
    secret_content = "OPENAI_API_KEY=sk-proj-" + ("a" * 32) + "\n"
    (root / ".env").write_text(secret_content, encoding="utf-8")
    (root / "notes.md").write_text("api contract\n", encoding="utf-8")

    pack = pack_directory(root, options=PackOptions(store_path=store_path))

    assert [item.provenance.path for item in pack.items] == ["notes.md"]
    assert len(pack.omitted_material) == 1
    assert pack.omitted_material[0].source_path == ".env"
    assert pack.omitted_material[0].reason.startswith("Secret-looking content omitted")
    assert "sk-proj" not in pack.to_canonical_json()

    store_blobs = list((store_path / "blobs" / "sha256").glob("*"))
    assert len(store_blobs) == 1
    assert store_blobs[0].read_text(encoding="utf-8") == "api contract\n"


def test_pack_directory_rejects_unknown_profile(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    try:
        PackOptions(profile="surprise")  # type: ignore[arg-type]
    except ValueError as exc:
        assert "Unknown pack profile" in str(exc)
    else:
        raise AssertionError("PackOptions should reject unknown profiles")
