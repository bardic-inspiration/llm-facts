"""Deterministic slot and height computation from validated data (spec §5).

``layout.py`` turns a validated :class:`~llm_facts.schema.LlmFacts` into a
:class:`Layout`: a fixed vertical stack of :class:`Slot`\\ s, each with a
pre-computed ``height`` and ``y`` offset. Later phases only *place* these slots —
the Jinja template does no arithmetic (spec §5).

Two rules from the spec shape everything here:

* **Estimate, don't measure.** Text wrap for the ``use[].note`` and the footer
  disclaimer is derived from ``--width`` and the body font size, not true glyph
  measurement — "fine for v1" (spec §5).
* **Determinism.** Same data in → byte-identical layout out: no wall-clock, no
  randomness, stable field order (spec §7). The dataclasses are frozen and
  compare by value so ``layout(data) == layout(data)`` holds every call.

This module is layout only — no SVG, no rasterization, and none of spec §10's
out-of-scope data-verification logic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

from llm_facts.schema import LlmFacts

# --- Tunable geometry (spec §5) --------------------------------------------

#: Default label width in px (spec §4 ``--width`` default).
DEFAULT_WIDTH = 420

#: Body font size and the average glyph width as a fraction of it. The wrap
#: estimator uses these to turn a pixel width into a chars-per-line budget. Both
#: are deliberately coarse — an estimate, not measurement (spec §5).
BODY_FONT_SIZE = 13.0
AVG_CHAR_WIDTH_RATIO = 0.52

#: Horizontal padding (both margins together) removed from ``width`` before the
#: text area is measured.
HORIZONTAL_PADDING = 24

#: Height of a rule divider interposed between two populated sections (spec §5
#: "3–8px"). One medium weight is used uniformly for a deterministic stack.
DIVIDER_HEIGHT = 4

# Fixed and simple data-driven section heights (spec §5 slot table).
EYEBROW_HEIGHT = 18
TITLE_HEIGHT = 56
SERVING_ROW = 16
SERVING_MAX_ROWS = 2
METRICS_ONE_ROW = 48
METRICS_TWO_ROW = 90
METRICS_WRAP_THRESHOLD = 4
HUMAN_HEIGHT = 34
NOTE_LINE_HEIGHT = 12
FOOTER_HEIGHT = 22

# Capped, list-driven sections (spec §5 caps, §9 visible "+N more" row). Each
# section keeps up to its cap of rows; a cap exceeded appends a visible
# truncation row, never a silent drop.
MODEL_ROW = 22
MODELS_CAP = 5
MODELS_TRUNC = 16
TOOL_ROW = 18
TOOLS_CAP = 8
TOOLS_TRUNC = 18
USE_CAP = 6
USE_ENTRY_MIN = 30
USE_ENTRY_MAX = 48
USE_LINE_STEP = 18
USE_TRUNC = 30

#: Placeholder row when ``models`` is present but empty and sessions were served
#: (spec §5) — shown instead of blank space, never as a zero.
NO_MODEL_BREAKDOWN = "No model breakdown provided"

#: Static note-line disclaimer (spec §5). The yml path is appended per call so
#: the reader knows where the authoritative data lives.
NOTE_DISCLAIMER = "Formatting only — this label does not verify the underlying data."

#: Default path shown in the note line and truncation rows.
DEFAULT_SOURCE_PATH = ".llm-facts.yml"


# --- Dataclasses ------------------------------------------------------------


@dataclass(frozen=True)
class Slot:
    """One placed element of the label.

    Carries its ``kind`` (which section it is, or ``"divider"``), its computed
    ``height``, its ``y`` offset from the top (set during assembly), and a
    ``content`` payload the renderer will read. Frozen so a built layout can't
    drift and so equality is by value (determinism, spec §7).
    """

    kind: str
    height: int
    y: int = 0
    content: Any = None


@dataclass(frozen=True)
class Layout:
    """The full vertical stack: ordered ``slots``, ``total_height``, ``width``.

    Immutable and value-compared: two layouts built from equal data are equal in
    every field (spec §7).
    """

    slots: tuple[Slot, ...]
    total_height: int
    width: int

    def kinds(self) -> list[str]:
        """The slot kinds top-to-bottom, dividers included."""
        return [s.kind for s in self.slots]

    def has(self, kind: str) -> bool:
        """Whether a slot of ``kind`` is present."""
        return any(s.kind == kind for s in self.slots)

    def slot(self, kind: str) -> Slot | None:
        """The first slot of ``kind``, or ``None`` if that section was omitted."""
        return next((s for s in self.slots if s.kind == kind), None)


# --- Text-wrap estimator (spec §5) -----------------------------------------


def chars_per_line(width: int, font_size: float = BODY_FONT_SIZE) -> int:
    """Estimate how many characters fit on one line at ``width``.

    Derived from the usable width and the average glyph width — not true text
    measurement (spec §5). Always at least 1 so a sliver-narrow width still
    yields a positive, finite line count.
    """
    usable = max(1, width - HORIZONTAL_PADDING)
    return max(1, int(usable / (font_size * AVG_CHAR_WIDTH_RATIO)))


def wrap_lines(text: str, width: int, font_size: float = BODY_FONT_SIZE) -> int:
    """Estimate the number of wrapped lines ``text`` occupies at ``width``.

    A pure function of its inputs (spec §5, §7): an empty string still occupies
    one line, never zero.
    """
    per_line = chars_per_line(width, font_size)
    return max(1, math.ceil(len(text) / per_line))


# --- Assembly ---------------------------------------------------------------


def assemble(sections: list[Slot], width: int) -> Layout:
    """Stack ``sections`` into a :class:`Layout`.

    Assigns each populated slot an increasing ``y`` offset, interposes a rule
    divider **between** adjacent sections only — never before the first, after
    the last, or where a section was omitted (the caller passes only populated
    slots) — and sets ``total_height`` to the sum of every slot height, dividers
    included (spec §5).
    """
    placed: list[Slot] = []
    y = 0
    for index, section in enumerate(sections):
        if index > 0:
            divider = Slot(
                kind="divider", height=DIVIDER_HEIGHT, y=y, content={"weight": "med"}
            )
            placed.append(divider)
            y += divider.height
        placed.append(replace(section, y=y))
        y += section.height
    return Layout(slots=tuple(placed), total_height=y, width=width)


# --- Fixed & simple data-driven sections (spec §5) --------------------------


def verification_status(data: LlmFacts) -> str:
    """Footer verification label from ``label.verified`` and the tools (spec §6).

    ``label.verified: true`` with any ``tools[].verified: false`` reads as
    ``"MIXED VERIFICATION"``; ``true`` with no dissent as ``"VERIFIED"``; an
    absent or false ``label.verified`` as ``"UNVERIFIED"``. This computes the
    footer text only — the ``--strict`` exit behavior lives in the CLI (spec §6).
    """
    label = data.label
    if label is not None and label.verified is True:
        tools = data.tools or []
        if any(tool.verified is False for tool in tools):
            return "MIXED VERIFICATION"
        return "VERIFIED"
    return "UNVERIFIED"


def _eyebrow(data: LlmFacts) -> Slot:
    generated_by = data.label.generated_by if data.label else None
    content = {"generated_by": generated_by, "schema_version": data.schema_version}
    return Slot("eyebrow", EYEBROW_HEIGHT, content=content)


def _title(data: LlmFacts) -> Slot:
    scope = data.serving.scope if data.serving else None
    return Slot("title", TITLE_HEIGHT, content={"scope": scope})


def _serving(data: LlmFacts) -> Slot | None:
    serving = data.serving
    if serving is None:
        return None
    rows = 0
    if serving.scope is not None:
        rows += 1
    if serving.period_start is not None or serving.period_end is not None:
        rows += 1
    rows = max(1, min(SERVING_MAX_ROWS, rows))
    content = {
        "rows": rows,
        "scope": serving.scope,
        "period_start": serving.period_start,
        "period_end": serving.period_end,
    }
    return Slot("serving", SERVING_ROW * rows, content=content)


def _metrics(data: LlmFacts) -> Slot | None:
    summary = data.summary
    if summary is None:
        return None
    known = (
        "total_sessions",
        "total_tokens",
        "ai_touched_files_pct",
        "ai_touched_lines_pct",
    )
    keys = [name for name in known if getattr(summary, name) is not None]
    count = len(keys) + len(summary.model_extra or {})
    height = METRICS_TWO_ROW if count > METRICS_WRAP_THRESHOLD else METRICS_ONE_ROW
    return Slot("metrics", height, content={"keys": keys, "count": count})


def _human(data: LlmFacts) -> Slot | None:
    human = data.human
    if human is None:
        return None
    has_key = (
        human.reviewed_by_human is not None
        or human.note is not None
        or bool(human.model_extra)
    )
    if not has_key:
        return None
    content = {"reviewed_by_human": human.reviewed_by_human, "note": human.note}
    return Slot("human", HUMAN_HEIGHT, content=content)


def _note(width: int, source_path: str) -> Slot:
    text = f"{NOTE_DISCLAIMER} See {source_path}."
    lines = wrap_lines(text, width)
    content = {"text": text, "lines": lines, "source_path": source_path}
    return Slot("note", NOTE_LINE_HEIGHT * lines, content=content)


def _footer(data: LlmFacts) -> Slot:
    generated_at = data.label.generated_at if data.label else None
    verified = data.label.verified if data.label else None
    content = {
        "generated_at": generated_at,
        "verified": verified,
        "status": verification_status(data),
    }
    return Slot("footer", FOOTER_HEIGHT, content=content)


# --- Capped list sections (spec §5, §9) -------------------------------------


def _more_label(more: int, source_path: str) -> str | None:
    """The visible truncation row text, or ``None`` when nothing is truncated.

    A cap exceeded is always shown — never a silent drop (spec §9).
    """
    if more <= 0:
        return None
    return f"+{more} more — see {source_path}"


def _models(data: LlmFacts, source_path: str) -> Slot | None:
    models = data.models
    if models is None:  # section absent → omitted entirely (omission-vs-zero)
        return None
    if len(models) == 0:
        # Present but empty: show a placeholder row only when sessions were
        # served, otherwise there is nothing to place (spec §5).
        sessions = data.summary.total_sessions if data.summary else None
        if sessions and sessions > 0:
            content = {
                "rows": [],
                "more": 0,
                "more_label": None,
                "placeholder": True,
                "text": NO_MODEL_BREAKDOWN,
            }
            return Slot("models", MODEL_ROW, content=content)
        return None
    total = len(models)
    shown = min(total, MODELS_CAP)
    more = total - shown
    height = MODEL_ROW * shown + (MODELS_TRUNC if more else 0)
    content = {
        "rows": list(models[:shown]),
        "more": more,
        "more_label": _more_label(more, source_path),
        "placeholder": False,
    }
    return Slot("models", height, content=content)


def _verification(data: LlmFacts, source_path: str) -> Slot | None:
    tools = data.tools
    if not tools:  # absent entirely → omit the verification section (spec §6)
        return None
    total = len(tools)
    shown = min(total, TOOLS_CAP)
    more = total - shown
    height = TOOL_ROW * shown + (TOOLS_TRUNC if more else 0)
    content = {
        "rows": list(tools[:shown]),
        "more": more,
        "more_label": _more_label(more, source_path),
    }
    return Slot("verification", height, content=content)


def _use(data: LlmFacts, width: int, source_path: str) -> Slot | None:
    uses = data.use
    if not uses:
        return None
    total = len(uses)
    more = max(0, total - USE_CAP)
    rows = []
    height = 0
    for entry in uses[:USE_CAP]:
        lines = wrap_lines(entry.note or "", width)
        entry_height = min(USE_ENTRY_MAX, USE_ENTRY_MIN + (lines - 1) * USE_LINE_STEP)
        rows.append({"entry": entry, "lines": lines, "height": entry_height})
        height += entry_height
    if more:
        height += USE_TRUNC
    content = {"rows": rows, "more": more, "more_label": _more_label(more, source_path)}
    return Slot("use", height, content=content)


# --- Public entry -----------------------------------------------------------


def layout(
    data: LlmFacts,
    width: int = DEFAULT_WIDTH,
    *,
    source_path: str = DEFAULT_SOURCE_PATH,
) -> Layout:
    """Compute the full :class:`Layout` for a validated document (spec §5).

    Builds every populated section top-to-bottom, skipping absent ones (an
    absent section produces no slot — omission, never a zero-height blank), then
    stacks them via :func:`assemble`.
    """
    ordered = (
        _eyebrow(data),
        _title(data),
        _serving(data),
        _metrics(data),
        _models(data, source_path),
        _verification(data, source_path),
        _use(data, width, source_path),
        _human(data),
        _note(width, source_path),
        _footer(data),
    )
    sections = [slot for slot in ordered if slot is not None]
    return assemble(sections, width)
