"""Layout engine (spec §5) — slot/height computation.

Phase 2 builds ``llm_facts/layout.py`` in four issues; this module grows with
them:

* #8 — the ``Slot`` / ``Layout`` dataclasses, the width-based wrap estimator, and
  the assembly step (dividers + ``y`` offsets + ``total_height``).
* #9 — fixed and simple data-driven section heights, and the ``layout()`` entry.
* #10 — capped list sections (models / tools / use) and "+N more" truncation.
* #11 — the empty-models placeholder, end-to-end integration, and determinism.
"""

from pathlib import Path

import pytest

from llm_facts import layout as L
from llm_facts.layout import Layout, Slot
from llm_facts.loader import load
from llm_facts.schema import LlmFacts

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> LlmFacts:
    return load(FIXTURES / f"{name}.llm-facts.yml").data


# --- #8: text-wrap estimator ------------------------------------------------


def test_wrap_estimator_is_deterministic() -> None:
    # Same inputs → same output: an estimate, not measurement (spec §5, §7).
    text = "a fairly long note that spans more than a single rendered line here"
    assert L.wrap_lines(text, 420) == L.wrap_lines(text, 420)


def test_wrap_estimator_short_text_is_one_line() -> None:
    assert L.wrap_lines("short", 420) == 1


def test_wrap_estimator_empty_text_is_one_line() -> None:
    # An empty note still occupies its row; never zero lines.
    assert L.wrap_lines("", 420) == 1


def test_wrap_estimator_wraps_when_text_exceeds_a_line() -> None:
    cpl = L.chars_per_line(420)
    one_line = "x" * cpl
    two_lines = "x" * (cpl + 1)
    assert L.wrap_lines(one_line, 420) == 1
    assert L.wrap_lines(two_lines, 420) == 2


def test_wrap_estimator_narrower_width_wraps_more() -> None:
    text = "x" * 120
    assert L.wrap_lines(text, 200) > L.wrap_lines(text, 600)


def test_chars_per_line_is_at_least_one_even_when_width_tiny() -> None:
    assert L.chars_per_line(1) >= 1


# --- #8: Slot / Layout dataclasses ------------------------------------------


def test_slot_carries_kind_height_y_and_content() -> None:
    slot = Slot(kind="eyebrow", height=18, y=0, content={"k": "v"})
    assert slot.kind == "eyebrow"
    assert slot.height == 18
    assert slot.y == 0
    assert slot.content == {"k": "v"}


def test_layout_exposes_slots_total_height_and_width() -> None:
    layout = Layout(slots=(), total_height=0, width=420)
    assert layout.slots == ()
    assert layout.total_height == 0
    assert layout.width == 420


# --- #8: assembly (y-offsets, dividers, total_height) -----------------------


def test_assemble_stacks_slots_with_increasing_y_offsets() -> None:
    sections = [Slot("a", height=10), Slot("b", height=20), Slot("c", height=5)]
    layout = L.assemble(sections, width=420)
    non_dividers = [s for s in layout.slots if s.kind != "divider"]
    ys = [s.y for s in non_dividers]
    assert ys == sorted(ys)
    # y offsets are strictly increasing down the stack.
    assert all(b > a for a, b in zip(ys, ys[1:], strict=False))


def test_assemble_total_height_is_sum_of_all_slot_heights() -> None:
    sections = [Slot("a", height=10), Slot("b", height=20)]
    layout = L.assemble(sections, width=420)
    assert layout.total_height == sum(s.height for s in layout.slots)
    # And the last slot ends exactly at total_height.
    last = layout.slots[-1]
    assert last.y + last.height == layout.total_height


def test_assemble_inserts_one_divider_between_each_adjacent_section() -> None:
    sections = [Slot("a", height=10), Slot("b", height=20), Slot("c", height=5)]
    layout = L.assemble(sections, width=420)
    kinds = [s.kind for s in layout.slots]
    # 3 sections → exactly 2 interposed dividers: a, div, b, div, c.
    assert kinds == ["a", "divider", "b", "divider", "c"]


def test_assemble_never_puts_a_divider_first_or_last() -> None:
    sections = [Slot("a", height=10), Slot("b", height=20)]
    layout = L.assemble(sections, width=420)
    assert layout.slots[0].kind != "divider"
    assert layout.slots[-1].kind != "divider"


def test_assemble_single_section_has_no_divider() -> None:
    layout = L.assemble([Slot("solo", height=10)], width=420)
    assert [s.kind for s in layout.slots] == ["solo"]
    assert layout.total_height == 10


def test_assemble_omitted_mid_stack_section_yields_one_divider() -> None:
    # B is omitted upstream; only A and C are passed in. There must be exactly
    # one divider between them — never a stray rule where B would have been.
    layout = L.assemble([Slot("a", height=10), Slot("c", height=5)], width=420)
    assert [s.kind for s in layout.slots] == ["a", "divider", "c"]


def test_assemble_empty_input_is_an_empty_layout() -> None:
    layout = L.assemble([], width=420)
    assert layout.slots == ()
    assert layout.total_height == 0
    assert layout.width == 420


def test_assemble_is_deterministic() -> None:
    sections = [Slot("a", height=10), Slot("b", height=20)]
    assert L.assemble(sections, width=420) == L.assemble(sections, width=420)


# --- #9: fixed & simple data-driven section heights -------------------------


def test_eyebrow_is_always_present_at_fixed_height() -> None:
    # Eyebrow draws from schema_version (always present) + label.generated_by.
    layout = L.layout(_fixture("minimal"))
    eyebrow = layout.slot("eyebrow")
    assert eyebrow is not None
    assert eyebrow.height == L.EYEBROW_HEIGHT


def test_title_is_always_present_at_fixed_height() -> None:
    layout = L.layout(_fixture("minimal"))
    title = layout.slot("title")
    assert title is not None
    assert title.height == L.TITLE_HEIGHT


def test_footer_is_always_present_at_fixed_height() -> None:
    layout = L.layout(_fixture("minimal"))
    footer = layout.slot("footer")
    assert footer is not None
    assert footer.height == L.FOOTER_HEIGHT


def test_note_line_is_always_present() -> None:
    layout = L.layout(_fixture("minimal"))
    note = layout.slot("note")
    assert note is not None
    assert note.height > 0


def test_serving_present_when_serving_data_present() -> None:
    # minimal has serving.scope only → one 16px row.
    layout = L.layout(_fixture("minimal"))
    serving = layout.slot("serving")
    assert serving is not None
    assert serving.height == L.SERVING_ROW  # single row


def test_serving_two_rows_when_scope_and_period_present() -> None:
    # typical has scope + a period → two rows, capped at 2.
    layout = L.layout(_fixture("typical"))
    serving = layout.slot("serving")
    assert serving is not None
    assert serving.height == L.SERVING_ROW * 2


def test_serving_omitted_when_serving_absent() -> None:
    data = LlmFacts.model_validate({"schema_version": 1})
    assert L.layout(data).slot("serving") is None


def test_big_metrics_one_row_for_up_to_four_keys() -> None:
    # typical carries all four summary keys → a single 48px row.
    layout = L.layout(_fixture("typical"))
    metrics = layout.slot("metrics")
    assert metrics is not None
    assert metrics.height == L.METRICS_ONE_ROW


def test_big_metrics_two_rows_when_more_than_four_keys() -> None:
    data = LlmFacts.model_validate(
        {
            "schema_version": 1,
            "summary": {
                "total_sessions": 1,
                "total_tokens": 1,
                "ai_touched_files_pct": 1,
                "ai_touched_lines_pct": 1,
                "extra_metric": 1,  # a fifth present key (retained as extra)
            },
        }
    )
    metrics = L.layout(data).slot("metrics")
    assert metrics is not None
    assert metrics.height == L.METRICS_TWO_ROW


def test_metrics_omitted_when_summary_absent() -> None:
    assert L.layout(_fixture("minimal")).slot("metrics") is None


def test_human_box_present_when_any_human_key_present() -> None:
    layout = L.layout(_fixture("typical"))
    human = layout.slot("human")
    assert human is not None
    assert human.height == L.HUMAN_HEIGHT


def test_human_box_omitted_when_human_absent() -> None:
    # This pins omission-vs-zero: no human key → no slot, not a zero-height blank.
    assert L.layout(_fixture("minimal")).slot("human") is None


def test_minimal_yields_only_the_sections_it_populates() -> None:
    layout = L.layout(_fixture("minimal"))
    populated = [s.kind for s in layout.slots if s.kind != "divider"]
    # minimal has schema_version + serving.scope only.
    assert populated == ["eyebrow", "title", "serving", "note", "footer"]


def test_absent_section_produces_no_zero_height_slot() -> None:
    layout = L.layout(_fixture("minimal"))
    assert all(s.height > 0 for s in layout.slots)


# --- #10: capped list sections and "+N more" truncation ---------------------


def test_models_within_cap_has_no_truncation_row() -> None:
    # typical has 2 models (≤ 5): 22px each, no "+N more" row.
    models = L.layout(_fixture("typical")).slot("models")
    assert models is not None
    assert models.height == L.MODEL_ROW * 2
    assert models.content["more"] == 0
    assert models.content["more_label"] is None


def test_models_over_cap_truncates_with_visible_more_row() -> None:
    # maxed has 6 models (cap 5): keep 5, append a "+1 more" row, add 16px.
    models = L.layout(_fixture("maxed")).slot("models")
    assert models is not None
    assert len(models.content["rows"]) == L.MODELS_CAP
    assert models.content["more"] == 1  # 6 − 5
    assert models.height == L.MODEL_ROW * L.MODELS_CAP + L.MODELS_TRUNC
    # The truncation is visible, never a silent drop (spec §9).
    assert "+1 more" in models.content["more_label"]
    assert ".llm-facts.yml" in models.content["more_label"]


def test_verification_within_cap_has_no_truncation_row() -> None:
    # typical has 2 tools (≤ 8).
    ver = L.layout(_fixture("typical")).slot("verification")
    assert ver is not None
    assert ver.height == L.TOOL_ROW * 2
    assert ver.content["more"] == 0


def test_verification_over_cap_truncates_with_visible_more_row() -> None:
    # maxed has 9 tools (cap 8): keep 8, "+1 more" row (spec §9).
    ver = L.layout(_fixture("maxed")).slot("verification")
    assert ver is not None
    assert len(ver.content["rows"]) == L.TOOLS_CAP
    assert ver.content["more"] == 1  # 9 − 8
    assert ver.height == L.TOOL_ROW * L.TOOLS_CAP + L.TOOLS_TRUNC
    assert "+1 more" in ver.content["more_label"]


def test_verification_omitted_when_tools_absent() -> None:
    # tools absent entirely → omit verification section (spec §6).
    assert L.layout(_fixture("minimal")).slot("verification") is None


def test_use_within_cap_has_no_truncation_row() -> None:
    # typical has 3 short-note use entries (≤ 6), each a single 30px row.
    use = L.layout(_fixture("typical")).slot("use")
    assert use is not None
    assert use.content["more"] == 0
    assert all(row["height"] == L.USE_ENTRY_MIN for row in use.content["rows"])


def test_use_over_cap_truncates_with_visible_more_row() -> None:
    # maxed has 7 use entries (cap 6): keep 6, "+1 more" row (spec §9).
    use = L.layout(_fixture("maxed")).slot("use")
    assert use is not None
    assert len(use.content["rows"]) == L.USE_CAP
    assert use.content["more"] == 1  # 7 − 6
    assert "+1 more" in use.content["more_label"]


def test_use_entry_height_varies_with_note_length() -> None:
    data = LlmFacts.model_validate(
        {
            "schema_version": 1,
            "use": [
                {"category": "tests", "note": "short"},
                {"category": "docs", "note": "z" * 200},
            ],
        }
    )
    rows = L.layout(data).slot("use").content["rows"]
    assert rows[0]["height"] == L.USE_ENTRY_MIN  # one line
    assert rows[1]["height"] == L.USE_ENTRY_MAX  # wraps, capped at the max
    assert rows[1]["height"] > rows[0]["height"]


def test_out_of_enum_use_category_is_laid_out_as_given() -> None:
    # An out-of-enum category is kept and laid out as given, never hard-failed
    # (spec §3), consistent with the loader.
    data = LlmFacts.model_validate(
        {"schema_version": 1, "use": [{"category": "migration", "note": "x"}]}
    )
    use = L.layout(data).slot("use")
    categories = [row["entry"].category for row in use.content["rows"]]
    assert categories == ["migration"]


def test_typical_stays_within_every_cap_with_no_truncation_row() -> None:
    layout = L.layout(_fixture("typical"))
    for kind in ("models", "verification", "use"):
        slot = layout.slot(kind)
        assert slot is not None
        assert slot.content["more"] == 0


# --- #11: empty-models placeholder ------------------------------------------


def test_empty_models_with_sessions_shows_one_placeholder_row() -> None:
    # models present but empty AND total_sessions > 0 → exactly one
    # "No model breakdown provided" row, not blank space (spec §5).
    data = LlmFacts.model_validate(
        {"schema_version": 1, "models": [], "summary": {"total_sessions": 12}}
    )
    models = L.layout(data).slot("models")
    assert models is not None
    assert models.content["placeholder"] is True
    assert models.content["rows"] == []
    assert models.height == L.MODEL_ROW
    assert "No model breakdown provided" in models.content["text"]


def test_absent_models_shows_no_models_section() -> None:
    # models absent → no models section at all (omission-vs-zero, spec §5).
    data = LlmFacts.model_validate(
        {"schema_version": 1, "summary": {"total_sessions": 12}}
    )
    assert L.layout(data).slot("models") is None


def test_empty_models_without_sessions_is_omitted() -> None:
    # Present-but-empty with no qualifying session count → nothing to place.
    data = LlmFacts.model_validate({"schema_version": 1, "models": []})
    assert L.layout(data).slot("models") is None


# --- #11: end-to-end integration across the fixtures ------------------------


def _populated(layout: Layout) -> list[str]:
    return [s.kind for s in layout.slots if s.kind != "divider"]


def test_integration_minimal_slot_presence_and_omission() -> None:
    layout = L.layout(_fixture("minimal"))
    assert _populated(layout) == ["eyebrow", "title", "serving", "note", "footer"]
    # Everything else is omitted, not zeroed.
    for absent in ("metrics", "models", "verification", "use", "human"):
        assert layout.slot(absent) is None


def test_integration_typical_slots_heights_and_within_caps() -> None:
    layout = L.layout(_fixture("typical"))
    assert _populated(layout) == [
        "eyebrow",
        "title",
        "serving",
        "metrics",
        "models",
        "verification",
        "use",
        "human",
        "note",
        "footer",
    ]
    assert layout.slot("serving").height == L.SERVING_ROW * 2
    assert layout.slot("metrics").height == L.METRICS_ONE_ROW
    assert layout.slot("models").height == L.MODEL_ROW * 2
    assert layout.slot("verification").height == L.TOOL_ROW * 2
    assert layout.slot("human").height == L.HUMAN_HEIGHT
    for kind in ("models", "verification", "use"):
        assert layout.slot(kind).content["more"] == 0


def test_integration_maxed_truncation_caps_and_more_counts() -> None:
    layout = L.layout(_fixture("maxed"))
    models = layout.slot("models")
    ver = layout.slot("verification")
    use = layout.slot("use")
    # Every cap exceeded by exactly one; each shows a visible "+1 more" row.
    assert len(models.content["rows"]) == L.MODELS_CAP
    assert models.content["more"] == 1
    assert models.height == L.MODEL_ROW * L.MODELS_CAP + L.MODELS_TRUNC
    assert len(ver.content["rows"]) == L.TOOLS_CAP
    assert ver.content["more"] == 1
    assert ver.height == L.TOOL_ROW * L.TOOLS_CAP + L.TOOLS_TRUNC
    assert len(use.content["rows"]) == L.USE_CAP
    assert use.content["more"] == 1
    for kind in ("models", "verification", "use"):
        assert "+1 more" in layout.slot(kind).content["more_label"]


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_integration_total_height_is_slots_plus_dividers(name: str) -> None:
    layout = L.layout(_fixture(name))
    # total_height is the sum of every slot height, dividers included...
    assert layout.total_height == sum(s.height for s in layout.slots)
    # ...and equivalently the populated slots plus one divider between each.
    populated = [s for s in layout.slots if s.kind != "divider"]
    dividers = [s for s in layout.slots if s.kind == "divider"]
    assert len(dividers) == len(populated) - 1
    expected = sum(s.height for s in populated) + len(dividers) * L.DIVIDER_HEIGHT
    assert layout.total_height == expected


# --- #11: determinism (spec §7) ---------------------------------------------


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_layout_called_twice_is_equal(name: str) -> None:
    data = _fixture(name)
    assert L.layout(data) == L.layout(data)


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_layout_is_stable_across_a_reparse(name: str) -> None:
    # Two independent parses of the same fixture yield equal layouts (spec §7).
    assert L.layout(_fixture(name)) == L.layout(_fixture(name))
