"""Schema v1 as pydantic models (spec §2).

The typed shape every later phase reads. Two rules from the spec shape every
model here:

* **Optional means absent, not zero.** Every field except ``schema_version`` is
  optional and defaults to ``None``. Missing fields must stay ``None`` so the
  renderer can omit the row/section instead of printing ``0`` or ``""``
  (spec §2, §3). ``None`` (section absent) is deliberately distinct from an
  empty list (section present but empty).

* **Tolerate the unexpected.** Unknown keys are retained rather than rejected
  (``extra="allow"``) so the loader can surface them as warnings, never errors
  (spec §3). Subjective free-text-adjacent fields (``serving.scope``,
  ``use.category``) accept any string — the spec's enums are guidance, not hard
  constraints.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Section(BaseModel):
    """Base for every model: keep unknown keys instead of rejecting them."""

    model_config = ConfigDict(extra="allow")


class Serving(_Section):
    scope: str | None = None
    period_start: date | None = None
    period_end: date | Literal["ongoing"] | None = None


class Summary(_Section):
    total_sessions: int | None = None
    total_tokens: int | None = None
    ai_touched_files_pct: int | None = None
    ai_touched_lines_pct: int | None = None


class ModelUsage(_Section):
    name: str | None = None
    tokens: int | None = None
    sessions: int | None = None
    tool: str | None = None


class Tool(_Section):
    name: str | None = None
    verified: bool | None = None


class Use(_Section):
    # category is guidance, not a constraint: accept any string (spec §3).
    category: str | None = None
    note: str | None = None


class Human(_Section):
    reviewed_by_human: bool | None = None
    note: str | None = None


class Label(_Section):
    verified: bool | None = None
    generated_by: str | None = None
    generated_at: datetime | None = None


class LlmFacts(_Section):
    """Top-level container for a ``.llm-facts.yml`` document."""

    schema_version: Literal[1]
    serving: Serving | None = None
    summary: Summary | None = None
    models: list[ModelUsage] | None = None
    tools: list[Tool] | None = None
    use: list[Use] | None = None
    human: Human | None = None
    label: Label | None = None
