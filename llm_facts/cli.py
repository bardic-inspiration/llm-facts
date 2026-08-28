"""Command-line entry points (spec §4).

Only ``validate`` lands in Phase 1 — it schema-checks a file and communicates
the result purely through the exit code (spec §4): ``0`` for a valid file,
non-zero for any parse or schema failure, with nothing rendered on stdout.
Unknown-field warnings and error detail go to stderr. ``render`` / ``init`` and
enabling the ``llm-facts`` console script arrive with the full CLI in Phase 5.
"""

from __future__ import annotations

import click

from llm_facts.loader import (
    MalformedYAMLError,
    MissingFileError,
    SchemaValidationError,
    load,
)

DEFAULT_PATH = ".llm-facts.yml"


@click.group()
def main() -> None:
    """Render a conformant .llm-facts.yml into a label."""


@main.command()
@click.argument("path", default=DEFAULT_PATH, type=click.Path())
def validate(path: str) -> None:
    """Schema-check PATH (default: .llm-facts.yml). Exit code only."""
    try:
        result = load(path)
    except MissingFileError as exc:
        click.echo(str(exc), err=True)
        click.echo(
            f"No {DEFAULT_PATH} to validate. Run 'llm-facts init' to scaffold one.",
            err=True,
        )
        raise SystemExit(1) from None
    except (MalformedYAMLError, SchemaValidationError) as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from None

    for warning in result.warnings:
        click.echo(f"warning: {warning}", err=True)
    # Valid: exit 0 implicitly. No output on stdout — the exit code is the answer.
