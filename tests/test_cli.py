"""CLI commands (spec §4, §6, §9).

``validate`` is exit-code only: 0 on a valid file, non-zero on any parse or
schema failure, with no rendered output on stdout. Malformed YAML reports
file/line/col; a missing file suggests ``init``; unknown-field warnings go to
stderr without changing a 0 exit.

``init`` scaffolds a blank ``.llm-facts.yml``; ``render`` drives the full
pipeline (``--format/--out/--width/--strict/--print``) and, under ``--strict``,
refuses a §6 self-contradiction without writing anything. Driven with click's
``CliRunner`` (spec §4).
"""

from pathlib import Path

from click.testing import CliRunner

from llm_facts.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def fixture(name: str) -> str:
    return str(FIXTURES / f"{name}.llm-facts.yml")


def write_fixture(tmp_path: Path, name: str, dest: str = ".llm-facts.yml") -> Path:
    """Copy fixture ``name`` into ``tmp_path`` so a run can't touch the repo."""
    target = tmp_path / dest
    target.write_text(Path(fixture(name)).read_text(encoding="utf-8"), encoding="utf-8")
    return target


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


# --- init (spec §4) ---------------------------------------------------------


def test_init_scaffolds_a_valid_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code == 0
    scaffold = tmp_path / ".llm-facts.yml"
    assert scaffold.exists()
    assert "schema_version: 1" in scaffold.read_text(encoding="utf-8")
    # The scaffold must itself validate (spec §4 — a usable starting point).
    assert CliRunner().invoke(main, ["validate"]).exit_code == 0


def test_init_refuses_to_clobber_existing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / ".llm-facts.yml"
    existing.write_text("schema_version: 1\n# keep me\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code != 0
    # The user's file is untouched — never silently overwritten.
    assert existing.read_text(encoding="utf-8") == "schema_version: 1\n# keep me\n"


# --- render: outputs (spec §4, §7) ------------------------------------------


def test_render_writes_png_by_default(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render"])
    assert result.exit_code == 0, result.output
    png = tmp_path / "llm-facts.png"
    assert png.exists()
    assert png.read_bytes()[:8] == PNG_SIGNATURE


def test_render_format_all_writes_three_files(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--format", "all"])
    assert result.exit_code == 0, result.output
    for name in ("llm-facts.svg", "llm-facts.png", "llm-facts.md"):
        assert (tmp_path / name).exists(), name


def test_render_format_svg_writes_only_svg(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--format", "svg"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "llm-facts.svg").exists()
    assert not (tmp_path / "llm-facts.png").exists()
    assert not (tmp_path / "llm-facts.md").exists()


def test_render_out_dir_is_created_and_used(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "build" / "labels"
    result = CliRunner().invoke(main, ["render", "--format", "md", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "llm-facts.md").exists()


def test_render_width_flows_into_the_svg(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--format", "svg", "--width", "300"])
    assert result.exit_code == 0, result.output
    svg = (tmp_path / "llm-facts.svg").read_text(encoding="utf-8")
    assert 'width="300"' in svg


def test_render_print_previews_and_writes_nothing(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "minimal")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--print"])
    assert result.exit_code == 0, result.output
    assert "# LLM Facts" in result.stdout
    assert list(tmp_path.glob("llm-facts.*")) == []  # no files written


def test_render_takes_an_explicit_path(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "typical", dest="custom.llm-facts.yml")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "custom.llm-facts.yml", "-f", "md"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "llm-facts.md").exists()


# --- render: determinism (spec §7) ------------------------------------------


def test_render_png_is_deterministic(tmp_path, monkeypatch) -> None:
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    CliRunner().invoke(main, ["render"])
    first = (tmp_path / "llm-facts.png").read_bytes()
    CliRunner().invoke(main, ["render"])
    second = (tmp_path / "llm-facts.png").read_bytes()
    assert first == second


# --- render: failure modes (spec §9) ----------------------------------------


def test_render_missing_file_suggests_init(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "nope.llm-facts.yml"])
    assert result.exit_code != 0
    assert "init" in result.stderr.lower()
    assert list(tmp_path.glob("llm-facts.*")) == []


def test_render_malformed_reports_location_and_writes_nothing(
    tmp_path, monkeypatch
) -> None:
    write_fixture(tmp_path, "malformed")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render"])
    assert result.exit_code != 0
    assert "9" in result.stderr  # the reported line
    assert list(tmp_path.glob("llm-facts.*")) == []


def test_render_unknown_field_warns_but_succeeds(tmp_path, monkeypatch) -> None:
    (tmp_path / ".llm-facts.yml").write_text(
        "schema_version: 1\nmystery: 42\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--format", "md"])
    assert result.exit_code == 0, result.output
    assert "mystery" in result.stderr


# --- render: --strict and §6 consistency ------------------------------------


def test_strict_exits_nonzero_and_writes_nothing_on_mixed(
    tmp_path, monkeypatch
) -> None:
    # typical: label.verified true but a tool is verified:false → MIXED (spec §6).
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--format", "all", "--strict"])
    assert result.exit_code != 0
    assert list(tmp_path.glob("llm-facts.*")) == []  # nothing written (spec §6)


def test_strict_passes_when_consistent(tmp_path, monkeypatch) -> None:
    # minimal: no tools, no label.verified → UNVERIFIED, not a contradiction.
    write_fixture(tmp_path, "minimal")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--format", "svg", "--strict"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "llm-facts.svg").exists()


def test_nonstrict_mixed_renders_with_mixed_footer(tmp_path, monkeypatch) -> None:
    # Without --strict the mixed case still renders, footer shows the state (spec §6).
    write_fixture(tmp_path, "typical")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["render", "--format", "svg"])
    assert result.exit_code == 0, result.output
    svg = (tmp_path / "llm-facts.svg").read_text(encoding="utf-8")
    assert "MIXED VERIFICATION" in svg
