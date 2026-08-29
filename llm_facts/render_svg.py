"""Render a :class:`~llm_facts.layout.Layout` to a deterministic SVG string.

Phase 3 of the build (spec §5, §7, §11.3). The division of labour is:

* :mod:`llm_facts.layout` owns the **macro** vertical stack — which sections are
  present, each slot's ``height`` and top ``y`` offset, caps and "+N more"
  truncation, and wrap line counts.
* This module owns the **micro** typographic placement *inside* each slot — the
  per-line baselines, column centres, and the exact text strings — and resolves
  every coordinate here, in Python.
* ``templates/label.svg.jinja`` is a dumb serializer: it places the pre-computed
  elements and does **no arithmetic** (spec §5).

Two spec rules shape the module:

* **Determinism** (spec §7): same ``(layout, data)`` in → byte-identical SVG out.
  No wall-clock, no randomness, stable ordering, integer coordinates.
* **System-font fallback** (spec §7): the SVG references the documented
  ``system-ui, sans-serif`` / ``ui-monospace, monospace`` stacks and embeds no
  fonts — font embedding is the PNG path's job (Phase 4).

The renderer needs the validated :class:`~llm_facts.schema.LlmFacts` alongside
the layout: the layout's metric slot records only *which* ``summary`` keys are
present, so the actual numbers are read from ``data`` at render time.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from llm_facts import layout as L
from llm_facts.layout import Layout, Slot
from llm_facts.schema import LlmFacts

# --- Template location ------------------------------------------------------

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "label.svg.jinja"
TEMPLATE_PATH = TEMPLATE_DIR / TEMPLATE_NAME

# --- Fonts (spec §7) --------------------------------------------------------

#: Documented system-font stacks. The SVG output falls back to these — it never
#: loads or embeds a font file (that is the PNG path's job, Phase 4).
FONT_BODY = "system-ui, sans-serif"
FONT_MONO = "ui-monospace, monospace"

# --- Typography / intra-slot geometry --------------------------------------
#
# All arithmetic using these constants happens here in Python; the template only
# consumes the resolved coordinates.

#: Left/right text margin. Mirrors ``layout.HORIZONTAL_PADDING`` split in two so
#: the wrap budget the layout used and the text inset here agree.
MARGIN_X = L.HORIZONTAL_PADDING // 2

TITLE_TEXT = "LLM FACTS"
ARIA_LABEL = "LLM Facts label"

# Baseline offsets from a slot's top ``y`` (px). Deliberately coarse — legible,
# not pixel-perfect typesetting.
EYEBROW_BASE = 13
TITLE_BASE = 30
SUBTITLE_BASE = 50
SERVING_BASE = 12
METRIC_VALUE_BASE = 30
METRIC_LABEL_GAP = 16
METRIC_ROW_STEP = 45
HUMAN_LINE1_BASE = 14
HUMAN_LINE2_BASE = 30
NOTE_BASE = 10
NOTE_STEP = L.NOTE_LINE_HEIGHT
FOOTER_BASE = 15
ROW_BASE = 15  # first-row text baseline inside a list section
TOOL_BASE = 13


# --- SVG text escaping is handled by Jinja autoescape (xml) -----------------


def _text(x: int, y: int, cls: str, content: str, anchor: str | None = None) -> dict:
    """One ``<text>`` element for the template."""
    return {"x": int(x), "y": int(y), "cls": cls, "content": content, "anchor": anchor}


def _rule(x1: int, y1: int, x2: int, y2: int, cls: str) -> dict:
    """One ``<line>`` element for the template."""
    return {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2), "cls": cls}


def _group(slot: Slot, texts: list[dict], rules: list[dict] | None = None) -> dict:
    """A rendered slot group the template iterates over."""
    return {"kind": slot.kind, "texts": texts, "rules": rules or []}


# --- Value formatting -------------------------------------------------------


def _grouped(value: int) -> str:
    """Integer with thousands separators — deterministic (``1234`` → ``1,234``)."""
    return f"{value:,}"


#: ``summary`` fields we know a short label and formatting for. Extra (unknown)
#: keys are rendered generically after these, preserving insertion order.
_METRIC_LABELS = {
    "total_sessions": "sessions",
    "total_tokens": "tokens",
    "ai_touched_files_pct": "files",
    "ai_touched_lines_pct": "lines",
}
_PCT_FIELDS = {"ai_touched_files_pct", "ai_touched_lines_pct"}


def _metric_items(data: LlmFacts) -> list[tuple[str, str]]:
    """The ``(value, label)`` pairs to draw, in a stable order.

    Values come from ``data`` because the metrics slot records only which keys
    are present, not their numbers.
    """
    summary = data.summary
    if summary is None:
        return []
    items: list[tuple[str, str]] = []
    for field, label in _METRIC_LABELS.items():
        value = getattr(summary, field)
        if value is None:
            continue
        text = f"{value}%" if field in _PCT_FIELDS else _grouped(value)
        items.append((text, label))
    for key, value in (summary.model_extra or {}).items():
        items.append((str(value), key.replace("_", " ")))
    return items


# --- Per-slot builders ------------------------------------------------------


def _build_eyebrow(slot: Slot, _data: LlmFacts, width: int) -> dict:
    generated_by = slot.content.get("generated_by")
    schema_version = slot.content.get("schema_version")
    parts = []
    if generated_by:
        parts.append(str(generated_by))
    parts.append(f"schema v{schema_version}")
    text = " · ".join(parts)
    return _group(slot, [_text(MARGIN_X, slot.y + EYEBROW_BASE, "eyebrow", text)])


def _build_title(slot: Slot, _data: LlmFacts, width: int) -> dict:
    texts = [_text(MARGIN_X, slot.y + TITLE_BASE, "title", TITLE_TEXT)]
    scope = slot.content.get("scope")
    if scope is not None:
        texts.append(_text(MARGIN_X, slot.y + SUBTITLE_BASE, "subtitle", str(scope)))
    return _group(slot, texts)


def _period_text(period_start: Any, period_end: Any) -> str:
    if period_start is not None and period_end is not None:
        return f"{period_start} → {period_end}"
    if period_start is not None:
        return f"from {period_start}"
    return f"until {period_end}"


def _build_serving(slot: Slot, _data: LlmFacts, width: int) -> dict:
    lines: list[str] = []
    scope = slot.content.get("scope")
    if scope is not None:
        lines.append(f"Scope: {scope}")
    period_start = slot.content.get("period_start")
    period_end = slot.content.get("period_end")
    if period_start is not None or period_end is not None:
        lines.append(f"Period: {_period_text(period_start, period_end)}")
    texts = [
        _text(MARGIN_X, slot.y + SERVING_BASE + index * L.SERVING_ROW, "serving", line)
        for index, line in enumerate(lines)
    ]
    return _group(slot, texts)


def _build_metrics(slot: Slot, data: LlmFacts, width: int) -> dict:
    items = _metric_items(data)
    if not items:
        return _group(slot, [])
    count = len(items)
    columns = count if count <= L.METRICS_WRAP_THRESHOLD else math.ceil(count / 2)
    col_width = width / columns
    texts: list[dict] = []
    for index, (value, label) in enumerate(items):
        row = 0 if count <= L.METRICS_WRAP_THRESHOLD or index < columns else 1
        column = index if row == 0 else index - columns
        cx = int(col_width * column + col_width / 2)
        value_y = slot.y + METRIC_VALUE_BASE + row * METRIC_ROW_STEP
        texts.append(_text(cx, value_y, "metric-value", value, anchor="middle"))
        texts.append(
            _text(
                cx, value_y + METRIC_LABEL_GAP, "metric-label", label, anchor="middle"
            )
        )
    return _group(slot, texts)


def _build_human(slot: Slot, _data: LlmFacts, width: int) -> dict:
    reviewed = slot.content.get("reviewed_by_human")
    if reviewed is True:
        status = "Reviewed by a human"
    elif reviewed is False:
        status = "Not reviewed by a human"
    else:
        status = "Human review"
    texts = [_text(MARGIN_X, slot.y + HUMAN_LINE1_BASE, "human-status", status)]
    note = slot.content.get("note")
    if note:
        texts.append(
            _text(MARGIN_X, slot.y + HUMAN_LINE2_BASE, "human-note", str(note))
        )
    return _group(slot, texts)


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    """Greedy word-wrap ``text`` to at most ``max_lines`` lines (deterministic).

    Uses the same chars-per-line budget as the layout's estimator so the wrapped
    lines fit the height the layout reserved (spec §5 — estimate, not measure).
    """
    budget = L.chars_per_line(width)
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= budget or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines] or [""]


def _build_note(slot: Slot, _data: LlmFacts, width: int) -> dict:
    text = slot.content.get("text", "")
    max_lines = slot.content.get("lines", 1)
    lines = _wrap(str(text), width, max_lines)
    texts = [
        _text(MARGIN_X, slot.y + NOTE_BASE + index * NOTE_STEP, "note", line)
        for index, line in enumerate(lines)
    ]
    return _group(slot, texts)


def _build_footer(slot: Slot, _data: LlmFacts, width: int) -> dict:
    status = slot.content.get("status", "UNVERIFIED")
    texts = [_text(MARGIN_X, slot.y + FOOTER_BASE, "footer-status", str(status))]
    generated_at = slot.content.get("generated_at")
    if generated_at is not None:
        texts.append(
            _text(
                width - MARGIN_X,
                slot.y + FOOTER_BASE,
                "footer-date",
                f"generated {generated_at}",
                anchor="end",
            )
        )
    return _group(slot, texts)


def _build_divider(slot: Slot, _data: LlmFacts, width: int) -> dict:
    y = slot.y + slot.height // 2
    return _group(slot, [], [_rule(MARGIN_X, y, width - MARGIN_X, y, "divider")])


def _model_meta(model: Any) -> str:
    """Right-aligned model detail — omitting any absent number (never ``0``)."""
    parts: list[str] = []
    if getattr(model, "tokens", None) is not None:
        parts.append(f"{_grouped(model.tokens)} tok")
    if getattr(model, "sessions", None) is not None:
        parts.append(f"{model.sessions} sess")
    if getattr(model, "tool", None):
        parts.append(str(model.tool))
    return " · ".join(parts)


def _build_models(slot: Slot, _data: LlmFacts, width: int) -> dict:
    content = slot.content
    texts: list[dict] = []
    if content.get("placeholder"):
        texts.append(
            _text(MARGIN_X, slot.y + ROW_BASE, "muted", str(content.get("text", "")))
        )
        return _group(slot, texts)
    rows = content.get("rows", [])
    for index, model in enumerate(rows):
        base = slot.y + ROW_BASE + index * L.MODEL_ROW
        name = getattr(model, "name", None) or ""
        texts.append(_text(MARGIN_X, base, "row-name", str(name)))
        meta = _model_meta(model)
        if meta:
            texts.append(_text(width - MARGIN_X, base, "row-meta", meta, anchor="end"))
    more_label = content.get("more_label")
    if more_label:
        base = slot.y + ROW_BASE + len(rows) * L.MODEL_ROW
        texts.append(_text(MARGIN_X, base, "more", str(more_label)))
    return _group(slot, texts)


def _tool_status(tool: Any) -> str:
    verified = getattr(tool, "verified", None)
    if verified is True:
        return "verified"
    if verified is False:
        return "unverified"
    return "—"


def _build_verification(slot: Slot, _data: LlmFacts, width: int) -> dict:
    content = slot.content
    texts: list[dict] = []
    rows = content.get("rows", [])
    for index, tool in enumerate(rows):
        base = slot.y + TOOL_BASE + index * L.TOOL_ROW
        name = getattr(tool, "name", None) or ""
        texts.append(_text(MARGIN_X, base, "row-name", str(name)))
        texts.append(
            _text(width - MARGIN_X, base, "row-meta", _tool_status(tool), anchor="end")
        )
    more_label = content.get("more_label")
    if more_label:
        base = slot.y + TOOL_BASE + len(rows) * L.TOOL_ROW
        texts.append(_text(MARGIN_X, base, "more", str(more_label)))
    return _group(slot, texts)


def _build_use(slot: Slot, _data: LlmFacts, width: int) -> dict:
    content = slot.content
    texts: list[dict] = []
    cursor = slot.y
    for row in content.get("rows", []):
        entry = row["entry"]
        height = row["height"]
        category = getattr(entry, "category", None) or ""
        note = getattr(entry, "note", None) or ""
        texts.append(
            _text(MARGIN_X, cursor + HUMAN_LINE1_BASE, "use-cat", str(category))
        )
        # One header line plus however many note lines fit the reserved height.
        max_note_lines = max(1, height // L.USE_LINE_STEP - 1)
        note_lines = _wrap(str(note), width, max_note_lines)
        for index, line in enumerate(note_lines):
            note_y = cursor + HUMAN_LINE2_BASE + index * L.USE_LINE_STEP
            texts.append(_text(MARGIN_X, note_y, "use-note", line))
        cursor += height
    more_label = content.get("more_label")
    if more_label:
        texts.append(
            _text(MARGIN_X, cursor + HUMAN_LINE1_BASE, "more", str(more_label))
        )
    return _group(slot, texts)


_BUILDERS = {
    "eyebrow": _build_eyebrow,
    "title": _build_title,
    "serving": _build_serving,
    "metrics": _build_metrics,
    "models": _build_models,
    "verification": _build_verification,
    "use": _build_use,
    "human": _build_human,
    "note": _build_note,
    "footer": _build_footer,
    "divider": _build_divider,
}


# --- Stylesheet -------------------------------------------------------------


def _stylesheet() -> str:
    """The embedded CSS. Kept free of ``&<>\"'`` so autoescape leaves it intact.

    References only the system-font stacks (spec §7) — no ``@font-face``, no
    external ``url(...)``.
    """
    return (
        f"text{{font-family:{FONT_BODY};fill:#1b1f24}}"
        ".bg{fill:#ffffff}"
        f".eyebrow{{font-size:10px;fill:#6a737d;font-family:{FONT_MONO};"
        "letter-spacing:0.08em}"
        ".title{font-size:22px;font-weight:700;letter-spacing:0.04em}"
        ".subtitle{font-size:12px;fill:#57606a}"
        ".serving{font-size:11px;fill:#57606a}"
        ".metric-value{font-size:20px;font-weight:700}"
        ".metric-label{font-size:9px;fill:#6a737d}"
        f".row-name{{font-size:12px}}"
        f".row-meta{{font-size:11px;fill:#57606a;font-family:{FONT_MONO}}}"
        ".more{font-size:10px;fill:#6a737d;font-style:italic}"
        ".muted{font-size:12px;fill:#6a737d;font-style:italic}"
        ".use-cat{font-size:11px;font-weight:700;fill:#24292f}"
        ".use-note{font-size:11px;fill:#57606a}"
        ".human-status{font-size:12px;font-weight:700}"
        ".human-note{font-size:11px;fill:#57606a}"
        ".note{font-size:9px;fill:#6a737d}"
        f".footer-status{{font-size:11px;font-weight:700;font-family:{FONT_MONO}}}"
        f".footer-date{{font-size:10px;fill:#6a737d;font-family:{FONT_MONO}}}"
        ".divider{stroke:#d0d7de;stroke-width:1}"
    )


# --- Environment (built once, reused; deterministic) ------------------------


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(default=True, default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


_ENV = _environment()


# --- Public entry -----------------------------------------------------------


def render_svg(layout: Layout, data: LlmFacts) -> str:
    """Render ``layout`` (geometry) + ``data`` (values) to an SVG string (spec §5).

    Deterministic: the same ``(layout, data)`` always yields byte-identical
    output (spec §7). The returned string references the system-font stacks and
    embeds no fonts — the documented SVG degradation (spec §7).
    """
    width = layout.width
    groups = [
        _BUILDERS[slot.kind](slot, data, width)
        for slot in layout.slots
        if slot.kind in _BUILDERS
    ]
    template = _ENV.get_template(TEMPLATE_NAME)
    return template.render(
        width=width,
        height=layout.total_height,
        viewbox=f"0 0 {width} {layout.total_height}",
        aria_label=ARIA_LABEL,
        css=_stylesheet(),
        slots=groups,
    )
