"""Rasterize a rendered label to a PNG via ``resvg`` (spec §7, §11.4).

Phase 4 of the build. The division of labour is:

* :func:`llm_facts.render_svg.render_svg` produces the SVG string — the single
  source of the label's geometry and text.
* This module rasterizes that SVG to a PNG through ``resvg`` (the ``resvg-py``
  binding, not ``cairosvg`` — spec §7), embedding the bundled ``.ttf`` fonts.

Two spec rules shape the module:

* **Embedded fonts** (spec §7): GitHub's SVG sanitizer strips external font
  loading, so the *SVG* path degrades to the system-font stacks. The *PNG* path
  instead embeds the vendored ``.ttf``s under ``templates/fonts/`` and skips
  system fonts entirely — the label renders with its real type on any host,
  independent of what fonts happen to be installed.
* **Determinism** (spec §7): the same ``(layout, data)`` in always yields a
  byte-identical PNG out. The SVG is deterministic upstream, ``resvg`` embeds no
  timestamps, and skipping system fonts removes the last host-dependent input,
  so the raster path is byte-stable across calls, re-parses, and processes.

The SVG references the documented ``system-ui, sans-serif`` /
``ui-monospace, monospace`` stacks. ``resvg`` does not know the ``system-ui`` /
``ui-monospace`` names, so it falls through to the generic ``sans-serif`` /
``monospace`` families — which we map to the two bundled faces below.
"""

from __future__ import annotations

import resvg_py

from llm_facts.layout import Layout
from llm_facts.render_svg import TEMPLATE_DIR, render_svg
from llm_facts.schema import LlmFacts

# --- Bundled fonts (spec §7) ------------------------------------------------

#: Directory holding the vendored SIL OFL ``.ttf``s, packaged with the wheel.
FONTS_DIR = TEMPLATE_DIR / "fonts"

#: The sans face (body text) and its family name, mapped to the ``sans-serif``
#: generic the SVG's ``system-ui, sans-serif`` stack falls through to.
SANS_FONT = FONTS_DIR / "Archivo-Regular.ttf"
SANS_FAMILY = "Archivo"

#: The mono face (eyebrow, row meta, footer) and its family name, mapped to the
#: ``monospace`` generic the SVG's ``ui-monospace, monospace`` stack reaches.
MONO_FONT = FONTS_DIR / "JetBrainsMono-Regular.ttf"
MONO_FAMILY = "JetBrains Mono"

#: The font files handed to ``resvg`` — the only faces it may draw from.
FONT_FILES = [SANS_FONT, MONO_FONT]

#: Skip host system fonts (spec §7): the render must depend only on the bundle,
#: which is what keeps the PNG byte-identical across machines.
SKIP_SYSTEM_FONTS = True


def svg_to_png(svg: str, width: int, height: int) -> bytes:
    """Rasterize ``svg`` to PNG ``bytes`` at ``width`` × ``height`` pixels.

    Draws glyphs only from the bundled fonts (:data:`FONT_FILES`) with system
    fonts skipped, so the output is deterministic and host-independent (spec §7).
    The SVG already paints its own opaque background, so no canvas colour is
    forced here.
    """
    return bytes(
        resvg_py.svg_to_bytes(
            svg_string=svg,
            width=int(width),
            height=int(height),
            skip_system_fonts=SKIP_SYSTEM_FONTS,
            font_files=[str(path) for path in FONT_FILES],
            font_family=SANS_FAMILY,
            sans_serif_family=SANS_FAMILY,
            monospace_family=MONO_FAMILY,
        )
    )


def render_png(layout: Layout, data: LlmFacts) -> bytes:
    """Render ``layout`` (geometry) + ``data`` (values) to PNG ``bytes`` (spec §7).

    Builds the SVG via :func:`~llm_facts.render_svg.render_svg`, then rasterizes
    it with the bundled fonts embedded. Deterministic: the same ``(layout,
    data)`` always yields byte-identical output.
    """
    svg = render_svg(layout, data)
    return svg_to_png(svg, layout.width, layout.total_height)
