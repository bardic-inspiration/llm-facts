"""Schema (spec §2) — pydantic models for schema v1.

Pins the shape every later phase reads: what is optional vs required, that
missing optional fields stay ``None`` (never coerced to ``0``/``""``), date and
datetime coercion, ``period_end`` accepting a date or the literal ``"ongoing"``,
free-text ``use.category``, and tolerance of unknown fields (§3 leaves the
warning itself to the loader).
"""

from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from llm_facts.schema import LlmFacts

FIXTURES = Path(__file__).parent / "fixtures"


def _yaml(name: str) -> dict:
    with (FIXTURES / f"{name}.llm-facts.yml").open() as handle:
        return YAML().load(handle)


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_every_valid_fixture_parses(name: str) -> None:
    model = LlmFacts.model_validate(_yaml(name))
    assert model.schema_version == 1


def test_schema_version_is_required() -> None:
    with pytest.raises(ValidationError):
        LlmFacts.model_validate({"serving": {"scope": "repository"}})


def test_schema_version_must_be_one() -> None:
    with pytest.raises(ValidationError):
        LlmFacts.model_validate({"schema_version": 2})


def test_only_schema_version_is_valid_and_sections_are_none() -> None:
    model = LlmFacts.model_validate({"schema_version": 1})
    assert model.serving is None
    assert model.summary is None
    assert model.models is None
    assert model.tools is None
    assert model.use is None
    assert model.human is None
    assert model.label is None


def test_missing_numbers_stay_none_not_zero() -> None:
    # A model row without tokens/sessions keeps them absent so rendering can
    # omit the number rather than print "0" (spec §2, §3).
    model = LlmFacts.model_validate(
        {"schema_version": 1, "models": [{"name": "Local", "sessions": 3}]}
    )
    row = model.models[0]
    assert row.sessions == 3
    assert row.tokens is None


def test_empty_list_is_distinct_from_absent_section() -> None:
    model = LlmFacts.model_validate({"schema_version": 1, "models": []})
    assert model.models == []
    assert model.tools is None


def test_dates_are_coerced() -> None:
    model = LlmFacts.model_validate(
        {
            "schema_version": 1,
            "serving": {"period_start": "2026-01-01"},
            "label": {"generated_at": "2026-08-28T12:00:00Z"},
        }
    )
    assert model.serving.period_start == date(2026, 1, 1)
    assert isinstance(model.label.generated_at, datetime)


def test_period_end_accepts_a_date() -> None:
    model = LlmFacts.model_validate(
        {"schema_version": 1, "serving": {"period_end": "2026-06-30"}}
    )
    assert model.serving.period_end == date(2026, 6, 30)


def test_period_end_accepts_the_ongoing_literal() -> None:
    model = LlmFacts.model_validate(
        {"schema_version": 1, "serving": {"period_end": "ongoing"}}
    )
    assert model.serving.period_end == "ongoing"


def test_out_of_enum_use_category_is_accepted() -> None:
    model = LlmFacts.model_validate(
        {"schema_version": 1, "use": [{"category": "migration", "note": "x"}]}
    )
    assert model.use[0].category == "migration"


def test_unknown_fields_are_tolerated_and_retained() -> None:
    # Never raise on unknown keys; retain them so the loader can warn (§3).
    model = LlmFacts.model_validate(
        {"schema_version": 1, "surprise": "hi", "serving": {"scope": "repo", "wat": 1}}
    )
    assert model.model_extra == {"surprise": "hi"}
    assert model.serving.model_extra == {"wat": 1}
