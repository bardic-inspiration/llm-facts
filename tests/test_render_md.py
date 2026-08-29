"""Markdown renderer (spec §1, §11.5) — a plain Markdown document of the label.

Phase 4 builds ``llm_facts/render_md.py``: a text fallback for places that can't
show an image (a PR body, an issue, a README). Two spec rules shape the tests:

* **Omit, never zero** (spec §2, §3): a missing optional field is left out, never
  rendered as ``0`` or blank; an absent section produces no heading.
* **Determinism** (spec §7 in spirit): the same ``data`` yields a byte-identical
  string across repeated calls and a re-parse.
"""

from pathlib import Path

import pytest

from llm_facts import render_md as M
from llm_facts.loader import load
from llm_facts.schema import LlmFacts

FIXTURES = Path(__file__).parent / "fixtures"


def _data(name: str):
    return load(FIXTURES / f"{name}.llm-facts.yml").data


def _md(name: str) -> str:
    return M.render_md(_data(name))


# --- Structure --------------------------------------------------------------


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_md_returns_str(name: str) -> None:
    out = _md(name)
    assert isinstance(out, str)
    assert out.strip()


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_has_title_heading(name: str) -> None:
    assert "# LLM Facts" in _md(name)


def test_uses_gfm_tables() -> None:
    # A GitHub-flavored Markdown table separator row (spec §1: "markdown table").
    assert "| --- |" in _md("typical")


# --- Populated values surface -----------------------------------------------


def test_serving_scope_rendered() -> None:
    assert "repository" in _md("minimal")


def test_summary_metrics_rendered() -> None:
    md = _md("typical")
    assert "128" in md
    assert "4,200,000" in md
    assert "63%" in md
    assert "41%" in md


def test_model_rows_rendered() -> None:
    md = _md("typical")
    assert "Claude Opus 4.8" in md
    assert "Claude Sonnet 4.5" in md
    assert "2,600,000" in md


def test_verification_rows_rendered() -> None:
    md = _md("typical")
    assert "Claude Code" in md
    assert "GitHub Copilot" in md


def test_use_entries_rendered() -> None:
    md = _md("typical")
    assert "refactor" in md
    assert "Extracted the layout engine into its own module." in md


def test_human_review_rendered() -> None:
    md = _md("typical")
    assert "Reviewed and edited by the maintainer before release." in md


def test_footer_verification_status() -> None:
    # Same wording as the visual label (spec §6).
    assert "MIXED VERIFICATION" in _md("typical")  # verified + a false tool
    assert "UNVERIFIED" in _md("minimal")  # no label at all
    assert "UNVERIFIED" in _md("maxed")  # label.verified false


# --- Omission (spec §2, §3) -------------------------------------------------


def test_absent_sections_have_no_heading() -> None:
    md = _md("minimal")  # only schema_version + serving.scope
    for heading in (
        "## Summary",
        "## Models",
        "## Verification",
        "## Use",
        "## Human",
    ):
        assert heading not in md


def test_missing_number_is_not_rendered_as_zero() -> None:
    # A model with sessions but no tokens must not print a 0 for the tokens
    # (spec §3). The session count is chosen with no zero digit, so any "0" in
    # the output would have to be a fabricated tokens value.
    data = LlmFacts.model_validate(
        {
            "schema_version": 1,
            "models": [{"name": "Local model", "sessions": 7, "tool": "Ollama"}],
        }
    )
    md = M.render_md(data)
    assert "Local model" in md
    assert "7" in md
    assert "0" not in md


# --- Determinism ------------------------------------------------------------


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_md_is_byte_identical_when_called_twice(name: str) -> None:
    data = _data(name)
    assert M.render_md(data) == M.render_md(data)


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_md_is_stable_across_a_reparse(name: str) -> None:
    assert _md(name) == _md(name)
