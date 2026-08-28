"""Load and validate a ``.llm-facts.yml`` (spec §3, §9).

Reads a file with ``ruamel.yaml`` (chosen over ``pyyaml`` for its line/column
marks), validates it into the :mod:`llm_facts.schema` models, and reports
problems as structured errors rather than tracebacks:

* Malformed YAML → :class:`MalformedYAMLError` carrying file, line, and column;
  no partial result is returned (spec §3, §9).
* A schema violation (e.g. a missing or wrong ``schema_version``) →
  :class:`SchemaValidationError`.
* A missing file → :class:`MissingFileError` (the CLI turns this into an
  ``init`` suggestion — spec §9).

Unknown fields are never errors: they are collected as warnings on the returned
:class:`LoadResult` for the caller (the CLI) to surface (spec §3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from llm_facts.schema import LlmFacts


class LlmFactsError(Exception):
    """Base for every loader failure — one type for callers to catch."""


class MissingFileError(LlmFactsError):
    """The requested ``.llm-facts.yml`` does not exist."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        super().__init__(f"no such file: {self.path}")


class MalformedYAMLError(LlmFactsError):
    """YAML that could not be parsed, with the file/line/column of the fault."""

    def __init__(
        self, path: str | Path, line: int | None, column: int | None, problem: str
    ) -> None:
        self.path = str(path)
        self.line = line
        self.column = column
        self.problem = problem
        where = f"{self.path}"
        if line is not None:
            where += f":{line}"
            if column is not None:
                where += f":{column}"
        super().__init__(f"malformed YAML at {where}: {problem}")


class SchemaValidationError(LlmFactsError):
    """Valid YAML that does not satisfy the schema (spec §2)."""

    def __init__(self, path: str | Path, errors: str) -> None:
        self.path = str(path)
        self.errors = errors
        super().__init__(f"invalid .llm-facts.yml at {self.path}:\n{errors}")


@dataclass
class LoadResult:
    """A successfully loaded document plus any non-fatal warnings."""

    data: LlmFacts
    warnings: list[str] = field(default_factory=list)


def load(path: str | Path) -> LoadResult:
    """Load, parse, and validate ``path`` into an :class:`LlmFacts` model.

    Returns a :class:`LoadResult` on success. Raises an :class:`LlmFactsError`
    subclass — never a bare traceback — on a missing file, malformed YAML, or a
    schema violation.
    """
    path = Path(path)
    if not path.exists():
        raise MissingFileError(path)

    try:
        with path.open(encoding="utf-8") as handle:
            raw = YAML().load(handle)
    except YAMLError as exc:
        line, column = _mark(exc)
        raise MalformedYAMLError(path, line, column, _problem(exc)) from exc

    try:
        data = LlmFacts.model_validate(raw)
    except ValidationError as exc:
        raise SchemaValidationError(path, _format_validation_error(exc)) from exc

    return LoadResult(data=data, warnings=_collect_unknown_field_warnings(data))


def _mark(exc: YAMLError) -> tuple[int | None, int | None]:
    """Extract a 1-indexed (line, column) from a ruamel error, if it carries one."""
    mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
    if mark is None:
        return None, None
    return mark.line + 1, mark.column + 1


def _problem(exc: YAMLError) -> str:
    return getattr(exc, "problem", None) or str(exc).strip() or exc.__class__.__name__


def _format_validation_error(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"]) or "<root>"
        lines.append(f"  {loc}: {err['msg']}")
    return "\n".join(lines)


def _collect_unknown_field_warnings(data: LlmFacts) -> list[str]:
    """Walk the validated model, reporting every retained unknown key by path."""
    warnings: list[str] = []
    _walk(data, "", warnings)
    return warnings


def _walk(obj: object, prefix: str, warnings: list[str]) -> None:
    if isinstance(obj, BaseModel):
        for key in obj.model_extra or {}:
            warnings.append(f"unknown field ignored: {prefix}{key}")
        for name in type(obj).model_fields:
            _walk(getattr(obj, name), f"{prefix}{name}.", warnings)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _walk(item, f"{prefix}{index}.", warnings)
