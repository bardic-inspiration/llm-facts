# Agent guide

Instructions for any AI coding agent (Claude Code and others) working in this
repository. This is the **canonical** agent guide; tool-specific files such as
[`CLAUDE.md`](CLAUDE.md) point here. Humans, start at
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## What this project is

A **formatting-only** renderer: a conformant `.llm-facts.yml` in, a rendered
label out (SVG / PNG / Markdown). Python, CLI first; a Docker GitHub Action wraps
the CLI. Authoritative behavior lives in [`docs/spec.md`](docs/spec.md) — read
the relevant section before writing code.

## Hard rules

- **Scope is formatting only.** No telemetry, log parsing, token/session
  counting, git-blame math, or data-accuracy proof (spec §10). If a task drifts
  out of scope, stop and flag it.
- **TDD is required.** Write a failing test first, then the code. See
  [`docs/testing-standards.md`](docs/testing-standards.md). No PR without tests.
- **Determinism.** Same YAML in → byte-identical SVG out. No headless browser,
  no wall-clock or randomness in output.
- **Locked tech choices.** `ruamel.yaml` (not `pyyaml` — need line/col), `resvg`
  (not `cairosvg`), Jinja2 templates (no arithmetic in the template), pydantic
  v2, click.
- **Atomic, Conventional Commits, linear history.** One logical change per
  commit; no merge commits — rebase onto `main`, never merge it in
  ([`docs/commit-standards.md`](docs/commit-standards.md)).

## Package layout

```
llm_facts/
  schema.py         pydantic models (schema v1)
  loader.py         ruamel load + validate, line-accurate errors
  layout.py         row counts + wrap -> Layout(slots, y-offsets, height)
  render_svg.py     Jinja2 -> SVG string
  render_raster.py  SVG -> PNG via resvg
  render_md.py      plain markdown table
  cli.py            click entrypoints
  templates/        label.svg.jinja, blank.llm-facts.yml, fonts/
action/             action.yml, Dockerfile
tests/              mirrors llm_facts/; fixtures under tests/fixtures/
```

## Build order

The renderer is built and working — all six phases below are done (see the
[archived roadmap](docs/archive/roadmap.md) for how the build got there).
New work is regular issues against the spec, not phase-ordered; see
[`docs/issue-standards.md`](docs/issue-standards.md). The steps, for
reference:

1. `schema.py` + `loader.py` + `validate` command — get validation solid first.
2. `layout.py` slot/height logic against fixtures.
3. `label.svg.jinja` + `render_svg.py`.
4. `render_raster.py` (resvg).
5. `render_md.py`.
6. CLI wiring (`cli.py`) — enable the `llm-facts` script in `pyproject.toml`.
7. Action `Dockerfile` + `action.yml`.

## Working loop

See [`docs/issue-standards.md`](docs/issue-standards.md) for the full
contract on picking up, filing, and closing issues — including how to
handle open questions or follow-on work that surfaces mid-issue. Summary:

1. Pick or open an issue (feature/task template), scoped to one build-order
   step. Implement only what its acceptance criteria require; resist
   folding in adjacent fixes, refactors, or improvements you notice along
   the way, even small ones — file those as separate issues instead
   ([`docs/issue-standards.md`](docs/issue-standards.md)). Each cold start
   has no memory of prior sessions, so this restraint is the only thing
   standing between the build and scope drift across agents — don't rely on
   a later session to notice and revert an out-of-scope change.
2. Write failing tests from the spec + fixtures. Run them; watch them fail.
3. Implement the smallest change to pass. Refactor with tests green.
4. `ruff check . && ruff format . && pytest` before every commit.
5. Atomic commits; open a PR with the template filled in.

Changing only Markdown (`docs/spec.md`, `docs/**`, `AGENTS.md`, etc.) — no
code? Steps 2–4 don't apply; use the leaner path in
[`docs/docs-only-changes.md`](docs/docs-only-changes.md) instead.

## When in doubt

- The spec is authoritative. If it's ambiguous or looks wrong, **do not
  silently invent behavior** — flag it in the issue/PR and, if it's a spec
  defect, follow [`docs/spec-guidelines.md`](docs/spec-guidelines.md) to
  amend the spec rather than diverging in code.
- Stay in scope. Implement only what your issue's acceptance criteria call
  for — nothing more. Spec §10 lists things that are explicitly out of
  scope; do not scope-creep into them.
- Anything else that comes up mid-issue — an edge case, a follow-on idea, a
  question that isn't a spec defect — gets filed as its own issue per
  [`docs/issue-standards.md`](docs/issue-standards.md), not solved inline.

## Docs map

[Spec](docs/spec.md) · [Issue standards](docs/issue-standards.md) ·
[Spec changes](docs/spec-guidelines.md) ·
[Testing](docs/testing-standards.md) · [Commits](docs/commit-standards.md) ·
[Documentation](docs/documentation-standards.md) ·
[Docs-only changes](docs/docs-only-changes.md) ·
[Roadmap (archived)](docs/archive/roadmap.md).
