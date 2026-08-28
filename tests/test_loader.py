"""Loader (spec §3, §9) — ruamel.yaml load with line-accurate errors.

Pins the loader contract: each valid fixture round-trips into the schema model;
malformed YAML raises a structured error carrying file/line/column with no
partial result; unknown fields are collected as warnings (never errors); missing
numeric fields stay absent rather than becoming ``0``; and a missing file fails
cleanly (the CLI turns that into an ``init`` hint).
"""

from pathlib import Path

import pytest

from llm_facts.loader import (
    LlmFactsError,
    LoadResult,
    MalformedYAMLError,
    MissingFileError,
    SchemaValidationError,
    load,
)
from llm_facts.schema import LlmFacts

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> Path:
    return FIXTURES / f"{name}.llm-facts.yml"


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_valid_fixtures_round_trip(name: str) -> None:
    result = load(fixture(name))
    assert isinstance(result, LoadResult)
    assert isinstance(result.data, LlmFacts)
    assert result.data.schema_version == 1
    assert result.warnings == []


def test_malformed_reports_file_line_and_column() -> None:
    with pytest.raises(MalformedYAMLError) as excinfo:
        load(fixture("malformed"))
    err = excinfo.value
    assert err.line == 9  # 1-indexed, at the unterminated flow sequence
    assert err.column is not None and err.column > 0
    assert Path(err.path).name == "malformed.llm-facts.yml"
    # The rendered message is useful on its own: path + line/col, no traceback.
    text = str(err)
    assert "malformed.llm-facts.yml" in text
    assert "9" in text


def test_malformed_is_an_llm_facts_error() -> None:
    with pytest.raises(LlmFactsError):
        load(fixture("malformed"))


def test_unknown_fields_collect_warnings_but_still_load(tmp_path: Path) -> None:
    doc = tmp_path / "unknown.llm-facts.yml"
    doc.write_text(
        "schema_version: 1\n"
        "mystery: 42\n"
        "serving:\n"
        "  scope: repository\n"
        "  surprise: yes\n"
    )
    result = load(doc)
    assert result.data.schema_version == 1  # loads fine
    joined = "\n".join(result.warnings)
    assert "mystery" in joined
    assert "serving.surprise" in joined


def test_unknown_field_inside_list_item_is_located(tmp_path: Path) -> None:
    doc = tmp_path / "list.llm-facts.yml"
    doc.write_text(
        "schema_version: 1\nmodels:\n  - name: A\n    weird: 1\n",
    )
    result = load(doc)
    assert any("models.0.weird" in w for w in result.warnings)


def test_missing_numbers_stay_absent(tmp_path: Path) -> None:
    doc = tmp_path / "sparse.llm-facts.yml"
    doc.write_text(
        "schema_version: 1\nmodels:\n  - name: Local\n    sessions: 4\n",
    )
    result = load(doc)
    row = result.data.models[0]
    assert row.sessions == 4
    assert row.tokens is None


def test_schema_failure_raises_schema_validation_error(tmp_path: Path) -> None:
    doc = tmp_path / "wrong.llm-facts.yml"
    doc.write_text("schema_version: 2\n")  # required to be 1 (spec §2)
    with pytest.raises(SchemaValidationError) as excinfo:
        load(doc)
    assert isinstance(excinfo.value, LlmFactsError)
    assert "wrong.llm-facts.yml" in str(excinfo.value)


def test_missing_schema_version_raises_schema_validation_error(tmp_path: Path) -> None:
    doc = tmp_path / "novers.llm-facts.yml"
    doc.write_text("serving:\n  scope: repository\n")
    with pytest.raises(SchemaValidationError):
        load(doc)


def test_missing_file_raises_missing_file_error(tmp_path: Path) -> None:
    with pytest.raises(MissingFileError) as excinfo:
        load(tmp_path / "nope.llm-facts.yml")
    assert "nope.llm-facts.yml" in str(excinfo.value)


def test_missing_file_is_an_llm_facts_error(tmp_path: Path) -> None:
    with pytest.raises(LlmFactsError):
        load(tmp_path / "nope.llm-facts.yml")


def test_accepts_str_path(tmp_path: Path) -> None:
    doc = tmp_path / "ok.llm-facts.yml"
    doc.write_text("schema_version: 1\n")
    result = load(str(doc))
    assert result.data.schema_version == 1
