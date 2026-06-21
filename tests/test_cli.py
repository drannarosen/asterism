from pathlib import Path

from typer.testing import CliRunner

from asterism.cli import app
from asterism.evidence import EvidencePack


def test_cli_help_renders() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "pack" in result.output


def test_pack_inspect_and_retrieve_cli(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    content = "likelihood: gaussian\n"
    (root / "notes.md").write_text(content, encoding="utf-8")
    store = tmp_path / "store"
    md_out = tmp_path / "pack.md"
    json_out = tmp_path / "pack.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "pack",
            str(root),
            "--out",
            str(md_out),
            "--json",
            str(json_out),
            "--store",
            str(store),
        ],
    )

    assert result.exit_code == 0
    assert md_out.exists()
    assert json_out.exists()
    assert "# EvidencePack:" in md_out.read_text(encoding="utf-8")

    pack = EvidencePack.model_validate_json(json_out.read_text(encoding="utf-8"))
    key = pack.items[0].provenance.retrieval_key

    inspect = runner.invoke(app, ["inspect", str(json_out)])
    assert inspect.exit_code == 0
    assert "EvidencePack" in inspect.output
    assert "1 item" in inspect.output

    retrieve = runner.invoke(app, ["retrieve", key, "--store", str(store)])
    assert retrieve.exit_code == 0
    assert retrieve.output == content
