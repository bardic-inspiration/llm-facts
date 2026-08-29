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
