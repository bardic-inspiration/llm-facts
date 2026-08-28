"""CLI ``validate`` command (spec §4, §9).

``validate`` is exit-code only: 0 on a valid file, non-zero on any parse or
schema failure, with no rendered output on stdout. Malformed YAML reports
file/line/col; a missing file suggests ``init``; unknown-field warnings go to
stderr without changing a 0 exit. Driven with click's ``CliRunner`` (spec §4).
"""

from pathlib import Path

from click.testing import CliRunner

from llm_facts.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return str(FIXTURES / f"{name}.llm-facts.yml")


def test_valid_file_exits_zero_with_no_stdout() -> None:
    result = CliRunner().invoke(main, ["validate", fixture("typical")])
    assert result.exit_code == 0
    assert result.stdout == ""  # exit-code only: nothing rendered


def test_valid_minimal_and_maxed_exit_zero() -> None:
    runner = CliRunner()
    for name in ("minimal", "maxed"):
        result = runner.invoke(main, ["validate", fixture(name)])
        assert result.exit_code == 0, name


def test_malformed_exits_nonzero_with_line_info() -> None:
    result = CliRunner().invoke(main, ["validate", fixture("malformed")])
    assert result.exit_code != 0
    assert "malformed.llm-facts.yml" in result.stderr
    assert "9" in result.stderr  # the reported line


def test_missing_file_suggests_init_without_traceback() -> None:
    result = CliRunner().invoke(main, ["validate", "does-not-exist.llm-facts.yml"])
    assert result.exit_code != 0
    assert "init" in result.stderr.lower()
    assert "Traceback" not in result.stderr
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_schema_failure_exits_nonzero(tmp_path: Path) -> None:
    doc = tmp_path / "bad.llm-facts.yml"
    doc.write_text("schema_version: 2\n")
    result = CliRunner().invoke(main, ["validate", str(doc)])
    assert result.exit_code != 0


def test_unknown_field_warns_but_exits_zero(tmp_path: Path) -> None:
    doc = tmp_path / "unknown.llm-facts.yml"
    doc.write_text("schema_version: 1\nmystery: 42\n")
    result = CliRunner().invoke(main, ["validate", str(doc)])
    assert result.exit_code == 0
    assert "mystery" in result.stderr
    assert result.stdout == ""


def test_path_defaults_to_dot_llm_facts_yml(tmp_path, monkeypatch) -> None:
    (tmp_path / ".llm-facts.yml").write_text("schema_version: 1\n")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["validate"])
    assert result.exit_code == 0


def test_default_path_missing_suggests_init(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["validate"])
    assert result.exit_code != 0
    assert "init" in result.stderr.lower()
