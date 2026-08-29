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
