"""Command-line entry points (spec §4, §6, §9).

The full CLI surface (Phase 5, spec §11.6):

* ``validate [path]`` — schema-check a file; the exit code is the whole answer
  (0 valid, non-zero on any parse or schema failure), nothing on stdout.
* ``init`` — scaffold a blank ``.llm-facts.yml`` from the bundled template,
  refusing to clobber an existing one.
* ``render [path]`` — run the load → layout → render pipeline, writing
  ``llm-facts.{svg,png,md}`` (``--format``, default ``png``) into ``--out``
  (default: the input's directory) at ``--width`` (default 420). ``--print``
  writes no files and prints a text preview instead; ``--strict`` refuses a §6
  self-contradiction, exiting non-zero and writing nothing (spec §6, §9).

Loader failures (missing file, malformed YAML, schema violation) are reported
as a single stderr line, never a traceback; a missing file suggests ``init``
(spec §9). Unknown-field warnings go to stderr and never change the exit code
(spec §3).
"""

from __future__ import annotations

from pathlib import Path

import click

from llm_facts import layout as L
from llm_facts.layout import layout
from llm_facts.loader import (
    LoadResult,
    MalformedYAMLError,
    MissingFileError,
    SchemaValidationError,
    load,
)
from llm_facts.render_md import render_md
from llm_facts.render_raster import render_png
from llm_facts.render_svg import render_svg
from llm_facts.schema import LlmFacts

DEFAULT_PATH = ".llm-facts.yml"

#: Fixed output basename — ``llm-facts.svg`` / ``.png`` / ``.md`` (spec §7).
OUTPUT_STEM = "llm-facts"

#: The scaffold ``init`` writes, packaged with the wheel (spec §4, §11.6).
BLANK_TEMPLATE = Path(__file__).parent / "templates" / "blank.llm-facts.yml"


@click.group()
def main() -> None:
    """Render a conformant .llm-facts.yml into a label."""


def _load_or_exit(path: str, *, missing_hint: str) -> LoadResult:
    """Load ``path`` or exit non-zero with a single stderr line (spec §9).

    On success, unknown-field warnings are echoed to stderr and the result is
    returned; the exit code is unaffected (spec §3). A missing file prints
    ``missing_hint`` (an ``init`` suggestion — spec §9); malformed YAML and
    schema violations print the loader's file/line/col message.
    """
    try:
        result = load(path)
    except MissingFileError as exc:
        click.echo(str(exc), err=True)
        click.echo(missing_hint, err=True)
        raise SystemExit(1) from None
    except (MalformedYAMLError, SchemaValidationError) as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from None
    for warning in result.warnings:
        click.echo(f"warning: {warning}", err=True)
    return result


def _strict_violation(data: LlmFacts) -> str | None:
    """The §6 self-contradiction ``--strict`` refuses, or ``None`` (spec §6).

    Only one inconsistency fails a strict run: a label that claims verification
    (``label.verified: true``) while a listed tool reports ``verified: false``
    — the "MIXED VERIFICATION" case. An absent ``label.verified`` (UNVERIFIED)
    or absent ``tools`` is not a contradiction, so strict treats those the same
    as a normal run.
    """
    label = data.label
    if label is not None and label.verified is True:
        if any(tool.verified is False for tool in (data.tools or [])):
            return "label.verified is true but a listed tool reports verified: false"
    return None


@main.command()
@click.argument("path", default=DEFAULT_PATH, type=click.Path())
def validate(path: str) -> None:
    """Schema-check PATH (default: .llm-facts.yml). Exit code only."""
    _load_or_exit(
        path,
        missing_hint=(
            f"No {DEFAULT_PATH} to validate. Run 'llm-facts init' to scaffold one."
        ),
    )
    # Valid: exit 0 implicitly. No output on stdout — the exit code is the answer.


@main.command()
def init() -> None:
    """Scaffold a blank .llm-facts.yml in the current directory."""
    target = Path(DEFAULT_PATH)
    if target.exists():
        click.echo(f"{DEFAULT_PATH} already exists — not overwriting.", err=True)
        raise SystemExit(1)
    target.write_text(BLANK_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    click.echo(f"Created {DEFAULT_PATH}. Edit it, then run 'llm-facts render'.")


@main.command()
@click.argument("path", default=DEFAULT_PATH, type=click.Path())
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["svg", "png", "md", "all"]),
    default="png",
    show_default=True,
    help="Output format(s) to write.",
)
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False),
    default=None,
    help="Output directory (default: the input file's directory).",
)
@click.option(
    "--width",
    type=int,
    default=L.DEFAULT_WIDTH,
    show_default=True,
    help="Label width in pixels.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Fail on a §6 self-contradiction instead of degrading.",
)
@click.option(
    "-p",
    "--print",
    "print_preview",
    is_flag=True,
    default=False,
    help="Print a text (Markdown) preview to stdout; write no files.",
)
def render(
    path: str,
    fmt: str,
    out_dir: str | None,
    width: int,
    strict: bool,
    print_preview: bool,
) -> None:
    """Render PATH (default: .llm-facts.yml) into a label."""
    data = _load_or_exit(
        path,
        missing_hint=(
            f"No such file. Run 'llm-facts init' to scaffold a {DEFAULT_PATH}."
        ),
    ).data

    # §6 strict check runs before any output: on a violation, write nothing.
    if strict:
        violation = _strict_violation(data)
        if violation is not None:
            click.echo(f"strict: {violation}", err=True)
            click.echo("no output written (--strict).", err=True)
            raise SystemExit(1)

    if print_preview:
        click.echo(render_md(data), nl=False)  # already ends with a newline
        return

    lay = layout(data, width=width, source_path=Path(path).name)
    out = Path(out_dir) if out_dir else Path(path).parent
    out.mkdir(parents=True, exist_ok=True)

    formats = ["svg", "png", "md"] if fmt == "all" else [fmt]
    for one in formats:
        target = out / f"{OUTPUT_STEM}.{one}"
        if one == "svg":
            target.write_text(render_svg(lay, data), encoding="utf-8")
        elif one == "png":
            target.write_bytes(render_png(lay, data))
        else:  # md
            target.write_text(render_md(data), encoding="utf-8")
        click.echo(f"wrote {target}")
