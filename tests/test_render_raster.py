"""Raster (PNG) renderer (spec §7, §11.4).

Phase 4 builds ``llm_facts/render_raster.py``: it takes the SVG that
``render_svg`` produces and rasterizes it to a PNG through ``resvg``, embedding
the bundled ``.ttf`` fonts so the output uses the label's real type and does not
depend on whatever fonts the host happens to have (spec §7).

Two spec rules shape the tests:

* **Determinism** (spec §7): same ``(layout, data)`` in → byte-identical PNG out,
  across repeated calls and across a re-parse of the same fixture.
* **Embedded fonts** (spec §7): the PNG path skips system fonts and draws glyphs
  from the vendored ``.ttf``s alone — this is what separates it from the SVG
  path, which falls back to system fonts.
"""

import struct
from pathlib import Path

import pytest

from llm_facts import layout as L
from llm_facts import render_raster as RR
from llm_facts import render_svg as R
from llm_facts.loader import load

FIXTURES = Path(__file__).parent / "fixtures"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _data(name: str):
    return load(FIXTURES / f"{name}.llm-facts.yml").data


def _png(name: str) -> bytes:
    data = _data(name)
    return RR.render_png(L.layout(data), data)


def _png_dimensions(png: bytes) -> tuple[int, int]:
    """Width, height from the IHDR chunk (bytes 16:24, two big-endian uint32)."""
    assert png[:8] == PNG_SIGNATURE
    width, height = struct.unpack(">II", png[16:24])
    return width, height


# --- PNG output & dimensions ------------------------------------------------


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_png_returns_png_bytes(name: str) -> None:
    assert _png(name)[:8] == PNG_SIGNATURE


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_png_dimensions_match_layout(name: str) -> None:
    data = _data(name)
    lay = L.layout(data)
    width, height = _png_dimensions(RR.render_png(lay, data))
    assert width == lay.width
    assert height == lay.total_height


# --- Determinism (spec §7) --------------------------------------------------


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_png_is_byte_identical_when_called_twice(name: str) -> None:
    data = _data(name)
    lay = L.layout(data)
    assert RR.render_png(lay, data) == RR.render_png(lay, data)


@pytest.mark.parametrize("name", ["minimal", "typical", "maxed"])
def test_render_png_is_stable_across_a_reparse(name: str) -> None:
    # Two independent parses of the same fixture → byte-identical PNG (spec §7).
    assert _png(name) == _png(name)


# --- Embedded fonts (spec §7) -----------------------------------------------


def test_bundled_font_files_exist_and_are_truetype() -> None:
    # The PNG path embeds these; they ship in the package (spec §7).
    assert RR.FONT_FILES, "no bundled fonts declared"
    sfnt_magics = {b"\x00\x01\x00\x00", b"true", b"OTTO", b"ttcf"}
    for path in RR.FONT_FILES:
        assert path.exists(), f"missing bundled font {path}"
        assert path.stat().st_size > 0
        assert path.read_bytes()[:4] in sfnt_magics, f"{path} is not a TrueType font"


def test_system_fonts_are_skipped() -> None:
    # The render must not depend on host fonts — it skips them (spec §7).
    assert RR.SKIP_SYSTEM_FONTS is True


def test_glyphs_are_drawn_from_embedded_fonts() -> None:
    # Rasterizing with the bundled fonts must differ from rasterizing the same
    # SVG with no fonts available at all: the difference is the embedded glyphs.
    import resvg_py

    data = _data("typical")
    lay = L.layout(data)
    svg = R.render_svg(lay, data)
    with_fonts = RR.svg_to_png(svg, lay.width, lay.total_height)
    without_fonts = bytes(
        resvg_py.svg_to_bytes(
            svg_string=svg,
            width=lay.width,
            height=lay.total_height,
            skip_system_fonts=True,
            font_files=[],
        )
    )
    assert with_fonts != without_fonts
