from pathlib import Path

from typer.testing import CliRunner

from asterism.cli import app
from asterism.evidence import EvidencePack


def test_cli_help_renders() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "pack" in result.output


def test_cli_profiles_renders_supported_profiles() -> None:
    result = CliRunner().invoke(app, ["profiles"])
    assert result.exit_code == 0
    assert "repo" in result.output
    assert "debug" in result.output
    assert "review" in result.output
    assert "handoff" in result.output


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
            "--profile",
            "debug",
        ],
    )

    assert result.exit_code == 0
    assert md_out.exists()
    assert json_out.exists()
    assert "# EvidencePack:" in md_out.read_text(encoding="utf-8")

    pack = EvidencePack.model_validate_json(json_out.read_text(encoding="utf-8"))
    assert pack.profile == "debug"
    key = pack.items[0].provenance.retrieval_key

    inspect = runner.invoke(app, ["inspect", str(json_out)])
    assert inspect.exit_code == 0
    assert "EvidencePack" in inspect.output
    assert "1 item" in inspect.output

    retrieve = runner.invoke(app, ["retrieve", key, "--store", str(store)])
    assert retrieve.exit_code == 0
    assert retrieve.output == content


def test_audit_cli_reports_success_and_failure(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "notes.md").write_text("api contract\n", encoding="utf-8")
    store = tmp_path / "store"
    json_out = tmp_path / "pack.json"
    runner = CliRunner()

    pack_result = runner.invoke(
        app,
        ["pack", str(root), "--json", str(json_out), "--store", str(store)],
    )
    assert pack_result.exit_code == 0

    success = runner.invoke(app, ["audit", str(json_out), "--store", str(store)])
    assert success.exit_code == 0
    assert "passed" in success.output

    failure = runner.invoke(app, ["audit", str(json_out), "--store", str(tmp_path / "missing")])
    assert failure.exit_code == 1
    assert "missing_retrieval_blob" in failure.output
