"""Plain Markdown renderer (spec §1, §11.5).

Phase 4's text fallback: a GitHub-flavored Markdown document of the same label,
for places that can't show an image — a PR body, an issue, a README. It is the
simplest output (spec §11.5: "trivial, do last") and shares no geometry with the
SVG/PNG path; it just walks the validated :class:`~llm_facts.schema.LlmFacts` and
emits headings and tables.

Two spec rules shape the module:

* **Omit, never zero** (spec §2, §3): a missing optional field is left out, never
  rendered as ``0`` or blank. A section absent from the input (``None``) produces
  no heading at all; only present sections are emitted.
* **Determinism** (spec §7): pure string assembly over a stable field order — the
  same ``data`` always yields the same Markdown.

Unlike the fixed-height visual label, a Markdown document has no height budget,
so the §5 caps and "+N more" truncation do not apply here: every provided row is
listed in full (which is still "no silent drop" — spec §9).
"""

from __future__ import annotations

from llm_facts import layout as L
from llm_facts.schema import LlmFacts

TITLE = "# LLM Facts"

#: "not provided" placeholder for a cell in an otherwise-populated table row —
#: distinct from ``0`` and from an empty cell (spec §3).
ABSENT = "—"


def _grouped(value: int) -> str:
    """Integer with thousands separators — deterministic (``1234`` → ``1,234``)."""
    return f"{value:,}"


def _escape(text: str) -> str:
    r"""Escape the two characters that would break a Markdown table cell.

    A literal ``|`` would start a new column and a newline would end the row, so
    both are neutralized; everything else passes through unchanged.
    """
    return text.replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """A GitHub-flavored Markdown table as a list of lines."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _serving(data: LlmFacts) -> list[str]:
    serving = data.serving
    if serving is None:
        return []
    rows: list[list[str]] = []
    if serving.scope is not None:
        rows.append(["Scope", _escape(str(serving.scope))])
    if serving.period_start is not None or serving.period_end is not None:
        start = serving.period_start
        end = serving.period_end
        if start is not None and end is not None:
            period = f"{start} → {end}"
        elif start is not None:
            period = f"from {start}"
        else:
            period = f"until {end}"
        rows.append(["Period", _escape(period)])
    if not rows:
        return []
    return ["## Serving", "", *_table(["Field", "Value"], rows), ""]


#: ``summary`` fields we know a heading and formatting for; unknown extras follow.
_METRIC_LABELS = {
    "total_sessions": "Sessions",
    "total_tokens": "Tokens",
    "ai_touched_files_pct": "AI-touched files",
    "ai_touched_lines_pct": "AI-touched lines",
}
_PCT_FIELDS = {"ai_touched_files_pct", "ai_touched_lines_pct"}


def _summary(data: LlmFacts) -> list[str]:
    summary = data.summary
    if summary is None:
        return []
    rows: list[list[str]] = []
    for field, label in _METRIC_LABELS.items():
        value = getattr(summary, field)
        if value is None:
            continue
        text = f"{value}%" if field in _PCT_FIELDS else _grouped(value)
        rows.append([label, text])
    for key, value in (summary.model_extra or {}).items():
        rows.append([_escape(key.replace("_", " ")), _escape(str(value))])
    if not rows:
        return []
    return ["## Summary", "", *_table(["Metric", "Value"], rows), ""]


def _models(data: LlmFacts) -> list[str]:
    models = data.models
    if not models:  # None (absent) or [] (present-but-empty): nothing to table
        return []
    rows: list[list[str]] = []
    for model in models:
        tokens = _grouped(model.tokens) if model.tokens is not None else ABSENT
        sessions = str(model.sessions) if model.sessions is not None else ABSENT
        rows.append(
            [
                _escape(model.name or ABSENT),
                tokens,
                sessions,
                _escape(model.tool or ABSENT),
            ]
        )
    headers = ["Model", "Tokens", "Sessions", "Tool"]
    return ["## Models", "", *_table(headers, rows), ""]


def _tool_status(verified: bool | None) -> str:
    if verified is True:
        return "verified"
    if verified is False:
        return "unverified"
    return ABSENT


def _verification(data: LlmFacts) -> list[str]:
    tools = data.tools
    if not tools:
        return []
    rows = [
        [_escape(tool.name or ABSENT), _tool_status(tool.verified)] for tool in tools
    ]
    return ["## Verification", "", *_table(["Tool", "Verified"], rows), ""]


def _use(data: LlmFacts) -> list[str]:
    use = data.use
    if not use:
        return []
    rows = [
        [_escape(entry.category or ABSENT), _escape(entry.note or ABSENT)]
        for entry in use
    ]
    return ["## Use", "", *_table(["Category", "Note"], rows), ""]


def _human(data: LlmFacts) -> list[str]:
    human = data.human
    if human is None:
        return []
    rows: list[list[str]] = []
    if human.reviewed_by_human is not None:
        rows.append(["Reviewed by a human", "yes" if human.reviewed_by_human else "no"])
    if human.note:
        rows.append(["Note", _escape(str(human.note))])
    if not rows:
        return []
    return ["## Human review", "", *_table(["Field", "Value"], rows), ""]


def _header(data: LlmFacts) -> list[str]:
    lines = [TITLE, ""]
    # Eyebrow: generated_by (if any) and the schema version, as inline code.
    generated_by = data.label.generated_by if data.label else None
    eyebrow = f"{generated_by} · " if generated_by else ""
    lines.append(f"`{eyebrow}schema v{data.schema_version}`")
    lines.append("")
    scope = data.serving.scope if data.serving else None
    if scope is not None:
        lines.append(f"**{_escape(str(scope))}**")
        lines.append("")
    return lines


def _footer(data: LlmFacts) -> list[str]:
    status = L.verification_status(data)
    generated_at = data.label.generated_at if data.label else None
    parts = [f"**{status}**"]
    if generated_at is not None:
        parts.append(f"generated {generated_at}")
    return ["---", "", " · ".join(parts), ""]


def render_md(data: LlmFacts) -> str:
    """Render ``data`` to a plain Markdown document (spec §1, §11.5).

    Only populated sections appear; missing optional fields are omitted, never
    shown as ``0`` or blank (spec §2, §3). Deterministic: the same ``data``
    always yields the same string.
    """
    lines: list[str] = []
    lines += _header(data)
    lines += _serving(data)
    lines += _summary(data)
    lines += _models(data)
    lines += _verification(data)
    lines += _use(data)
    lines += _human(data)
    lines += _footer(data)
    return "\n".join(lines).rstrip("\n") + "\n"
