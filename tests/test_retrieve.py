import pytest

from asterism.retrieve import RetrievalKeyError, RetrievalStore


def test_store_puts_and_retrieves_exact_text(tmp_path) -> None:
    store = RetrievalStore(tmp_path / "store")
    content = "alpha\nbeta\n"

    key = store.put_text(content, source_path="notes.txt")

    assert key.startswith("sha256:")
    assert store.retrieve_text(key) == content


def test_store_rejects_unknown_key(tmp_path) -> None:
    store = RetrievalStore(tmp_path / "store")

    with pytest.raises(RetrievalKeyError):
        store.retrieve_bytes("sha256:" + "0" * 64)
