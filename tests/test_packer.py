from asterism import PackOptions, pack_directory
from asterism.retrieve import RetrievalStore


def test_pack_directory_records_file_provenance_and_retrieval(tmp_path) -> None:
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


def test_pack_directory_skips_ignored_paths(tmp_path) -> None:
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
