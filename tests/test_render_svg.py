"""SVG renderer (spec §5, §7) — deterministic Layout → SVG string.

Phase 3 builds ``llm_facts/render_svg.py`` and
``llm_facts/templates/label.svg.jinja`` across four issues; this module grows
with them:

* #14 — the SVG document frame, font stacks, and the ``render_svg`` entry.
* #15 — fixed and simple slots (eyebrow, title, serving, metrics, human, note,
  footer) and the dividers between sections.
* #16 — capped list sections (models, verification, use) with "+N more" rows.
* #17 — determinism and end-to-end integration across the fixtures.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from llm_facts import layout as L
from llm_facts import render_svg as R
from llm_facts.loader import load
from llm_facts.schema import LlmFacts

FIXTURES = Path(__file__).parent / "fixtures"
SVG_NS = "{http://www.w3.org/2000/svg}"


def _data(name: str) -> LlmFacts:
    return load(FIXTURES / f"{name}.llm-facts.yml").data


def _render(name: str) -> str:
    data = _data(name)
    return R.render_svg(L.layout(data), data)


def _root(svg: str) -> ET.Element:
    return ET.fromstring(svg)


# --- #14: document frame, dimensions, fonts, determinism --------------------


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_returns_wellformed_xml(name: str) -> None:
    root = _root(_render(name))
    assert root.tag == f"{SVG_NS}svg"


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_svg_dimensions_match_layout(name: str) -> None:
    data = _data(name)
    lay = L.layout(data)
    root = _root(R.render_svg(lay, data))
    assert int(root.attrib["width"]) == lay.width
    assert int(root.attrib["height"]) == lay.total_height
    assert root.attrib["viewBox"] == f"0 0 {lay.width} {lay.total_height}"


def test_svg_declares_system_font_stack() -> None:
    svg = _render("typical")
    # Spec §7: SVG falls back to the documented system-font stacks.
    assert "system-ui" in svg
    assert "sans-serif" in svg
    assert "ui-monospace" in svg
    assert "monospace" in svg


def test_svg_loads_no_external_fonts() -> None:
    # Spec §7: font embedding is PNG-only; the SVG must not pull in any font.
    svg = _render("maxed")
    assert "@font-face" not in svg
    assert "url(" not in svg


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_is_byte_identical_when_called_twice(name: str) -> None:
    data = _data(name)
    lay = L.layout(data)
    assert R.render_svg(lay, data) == R.render_svg(lay, data)


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_is_stable_across_a_reparse(name: str) -> None:
    # Two independent parses of the same fixture → byte-identical SVG (spec §7).
    assert _render(name) == _render(name)


def test_template_has_no_arithmetic() -> None:
    # Spec §5: the template only *places* pre-computed slots — all coordinate
    # math lives in Python. Guard it by scanning the template's Jinja regions.
    src = R.TEMPLATE_PATH.read_text(encoding="utf-8")
    regions = re.findall(r"{{.*?}}|{%.*?%}", src, re.DOTALL)
    assert regions  # the template does use Jinja
    for region in regions:
        inner = region[2:-2]  # strip the {{ }} / {% %} delimiters
        inner = re.sub(r"'[^']*'|\"[^\"]*\"", "", inner)  # drop string literals
        for op in ("+", "*", "/", "%", "-"):
            assert op not in inner, f"arithmetic operator {op!r} in {region!r}"


# --- #15: fixed & simple slots ----------------------------------------------


def test_eyebrow_shows_schema_version() -> None:
    assert "schema v1" in _render("minimal")


def test_title_is_present() -> None:
    assert R.TITLE_TEXT in _render("minimal")


def test_subtitle_shows_serving_scope() -> None:
    assert "repository" in _render("minimal")


def test_metrics_render_values_from_data() -> None:
    svg = _render("typical")
    # summary.total_sessions: 128, total_tokens: 4200000, files/lines pct.
    assert "128" in svg
    assert "4,200,000" in svg
    assert "63%" in svg
    assert "41%" in svg


def test_footer_shows_verification_status() -> None:
    # typical: label.verified true but a tool is verified:false → MIXED (§6).
    assert "MIXED VERIFICATION" in _render("typical")
    # maxed: label.verified false → UNVERIFIED.
    assert "UNVERIFIED" in _render("maxed")
    # minimal: no label at all → UNVERIFIED.
    assert "UNVERIFIED" in _render("minimal")


def test_human_box_rendered_when_present_and_omitted_when_absent() -> None:
    typical_root = _root(_render("typical"))
    kinds = {g.attrib.get("class", "") for g in typical_root.iter(f"{SVG_NS}g")}
    assert any("slot-human" in k for k in kinds)
    minimal_root = _root(_render("minimal"))
    minimal_kinds = {g.attrib.get("class", "") for g in minimal_root.iter(f"{SVG_NS}g")}
    assert not any("slot-human" in k for k in minimal_kinds)


def test_dividers_are_drawn_between_sections() -> None:
    lay = L.layout(_data("typical"))
    n_dividers = sum(1 for s in lay.slots if s.kind == "divider")
    root = _root(R.render_svg(lay, _data("typical")))
    divider_groups = [
        g
        for g in root.iter(f"{SVG_NS}g")
        if "slot-divider" in g.attrib.get("class", "")
    ]
    assert len(divider_groups) == n_dividers
    assert n_dividers > 0


def test_note_text_is_present() -> None:
    assert "Formatting only" in _render("minimal")


def test_dynamic_text_is_xml_escaped() -> None:
    # A note with XML-significant characters must not break well-formedness.
    data = LlmFacts.model_validate(
        {
            "schema_version": 1,
            "use": [{"category": "docs", "note": "a & b < c > d"}],
        }
    )
    svg = R.render_svg(L.layout(data), data)
    root = _root(svg)  # parses → escaping worked
    assert root.tag == f"{SVG_NS}svg"
    assert "a &amp; b" in svg


# --- #16: capped list sections ----------------------------------------------


def test_models_rows_rendered_with_values() -> None:
    svg = _render("typical")
    assert "Claude Opus 4.8" in svg
    assert "Claude Sonnet 4.5" in svg


def test_models_missing_number_is_not_rendered_as_zero() -> None:
    # A model that omits tokens must never render a "0 tok" count (spec §3).
    data = LlmFacts.model_validate(
        {
            "schema_version": 1,
            "models": [{"name": "Local model", "sessions": 20, "tool": "Ollama"}],
        }
    )
    svg = R.render_svg(L.layout(data), data)
    assert "Local model" in svg
    assert "20 sess" in svg
    assert "0 tok" not in svg


def test_more_row_is_visible_when_truncated() -> None:
    svg = _render("maxed")
    # Each of the three capped sections is over by one in the maxed fixture.
    assert svg.count("+1 more") >= 3


def test_no_more_row_within_cap() -> None:
    assert "more —" not in _render("typical")


def test_empty_models_placeholder_is_rendered() -> None:
    data = LlmFacts.model_validate(
        {"schema_version": 1, "models": [], "summary": {"total_sessions": 12}}
    )
    svg = R.render_svg(L.layout(data), data)
    assert "No model breakdown provided" in svg


def test_verification_rows_rendered() -> None:
    svg = _render("typical")
    assert "Claude Code" in svg
    assert "GitHub Copilot" in svg


def test_use_entries_rendered() -> None:
    svg = _render("typical")
    assert "refactor" in svg
    assert "Extracted the layout engine" in svg


def test_out_of_enum_use_category_rendered_as_given() -> None:
    # An out-of-enum category (within cap) is rendered as given (spec §3).
    data = LlmFacts.model_validate(
        {"schema_version": 1, "use": [{"category": "migration", "note": "x"}]}
    )
    assert "migration" in R.render_svg(L.layout(data), data)


def test_absent_list_sections_are_omitted() -> None:
    root = _root(_render("minimal"))
    classes = " ".join(g.attrib.get("class", "") for g in root.iter(f"{SVG_NS}g"))
    for kind in ("slot-models", "slot-verification", "slot-use"):
        assert kind not in classes


# --- #17: integration -------------------------------------------------------


def test_minimal_renders_only_its_populated_sections() -> None:
    root = _root(_render("minimal"))
    slot_kinds = {
        c.split("slot-")[-1]
        for g in root.iter(f"{SVG_NS}g")
        for c in [g.attrib.get("class", "")]
        if "slot-" in c
    }
    # Dividers plus the five populated sections; nothing else.
    assert "eyebrow" in slot_kinds
    assert "title" in slot_kinds
    assert "serving" in slot_kinds
    assert "note" in slot_kinds
    assert "footer" in slot_kinds
    for absent in ("metrics", "models", "verification", "use", "human"):
        assert absent not in slot_kinds
