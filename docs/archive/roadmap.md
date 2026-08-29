# Roadmap (archived)

> **Archived.** This was the preliminary, phase-by-phase build plan for
> reaching the working alpha. All six phases are done — the plan it describes
> is complete, so it's kept here as a historical record, not a live-status
> doc. For current behavior see [the spec](../spec.md); for how to pick up
> new work see [issue standards](../issue-standards.md).

The phased view of the [build spec §11](../spec.md). Each phase is a slice of
the renderer that landed as a small set of atomic, test-first PRs. Phases were
sequential — each built on the one before.

**How this drove the build:** each phase's work was tracked as GitHub issues
(the [feature/task template](../../.github/ISSUE_TEMPLATE/feature_task.md)),
labeled `phase:N`. Agents pulled the lowest open issue in the active phase,
followed the [working loop](../../AGENTS.md#working-loop), and opened one PR
per issue. A phase was done when every issue under its label was closed and
its exit criteria held. New work no longer uses phase labels — see
[issue standards](../issue-standards.md) for the current workflow.

Status legend: `planned` · `in progress` · `done`.

## Phase 1 — Validation foundation · `done`

- **Goal:** load and validate a `.llm-facts.yml`; `llm-facts validate` works end
  to end.
- **Spec:** §2 (schema), §3 (validation), §4 (`validate`), §11.1.
- **Deliverables:** `schema.py`, `loader.py`, the `validate` CLI command, and the
  shared test fixtures.
- **Exit criteria:** `validate` returns correct exit codes across the
  minimal / typical / maxed fixtures; malformed YAML reports file/line/col;
  unknown fields warn (never error); full TDD coverage; CI green.

## Phase 2 — Layout engine · `done`

- **Goal:** deterministic slot and height computation from validated data.
- **Spec:** §5 (layout → slot table), §11.2.
- **Deliverables:** `layout.py` → `Layout(slots, total_height, width)`, built as
  `Slot`/`Layout` dataclasses, a width-based wrap estimator, per-section height
  rules, the capped "+N more" tables, and the empty-models placeholder.
- **Exit criteria:** met — layout tests assert slot presence, caps and "+N more"
  truncation, height rules, and section-omission-vs-zero across the fixtures,
  plus determinism (equal `Layout`s across repeated calls and a re-parse).

## Phase 3 — SVG renderer · `done`

- **Goal:** render a `Layout` to a deterministic SVG string.
- **Spec:** §5 (template places pre-computed slots, no arithmetic), §7
  (determinism, system-font fallback), §11.3.
- **Deliverables:** `templates/label.svg.jinja`, `render_svg.py`.
- **Exit criteria:** met — byte-identical SVG for identical input; system-font
  stack in SVG output; no arithmetic in the template.

## Phase 4 — Raster & Markdown outputs · `done`

- **Goal:** PNG via resvg with embedded fonts; a plain Markdown table.
- **Spec:** §7 (resvg, font embedding), §11.4–5.
- **Deliverables:** `render_raster.py`, `render_md.py`, bundled fonts under
  `templates/fonts/`.
- **Exit criteria:** met — PNG embeds the bundled `.ttf`s; Markdown table
  renders; raster path is deterministic.

## Phase 5 — CLI surface · `done`

- **Goal:** the full click CLI — `init`, `render` with `--format/--out/--width/
  --strict/--print` — wired to the render pipeline.
- **Spec:** §4 (CLI), §6 (`--strict`), §9 (failure modes), §11.6.
- **Deliverables:** `cli.py`, `templates/blank.llm-facts.yml`; enable the
  `llm-facts` console script in `pyproject.toml`.
- **Exit criteria:** met — every command works; `--strict` exits non-zero and
  writes nothing on a §6 violation; a missing file suggests `init`.

## Phase 6 — GitHub Action · `done`

- **Goal:** a Docker-based Action wrapping the CLI.
- **Spec:** §8, §11.7.
- **Deliverables:** `action.yml` (repo root — see §1 for why), `action/Dockerfile`,
  `action/entrypoint.sh`.
- **Exit criteria:** met — `commit` (render → commit back) and artifact
  (render → drift-check, fail if the committed label is stale) modes both work;
  a missing input fails without fabricating a label. Wire it to `push` on
  `.llm-facts.yml` in a consuming repo to render on change.

## Dependencies

All tooling was free and open-source; two items needed sourcing before Phase 4:

- **Python deps** (pydantic, ruamel.yaml, jinja2, click, pytest, ruff) — pinned in
  `pyproject.toml`, installed in CI. No action needed.
- **resvg** (Phase 4) — free (MPL/MIT), a Rust binary/binding. Confirmed a
  pip-installable binding (`resvg-py`, pinned in `pyproject.toml`) works in CI
  and the Docker image.
- **Fonts** (Phase 4) — Archivo, Archivo Narrow, JetBrains Mono, all SIL Open Font
  License. Vendored as `.ttf`s under `templates/fonts/`; free to redistribute.
- **Docker + Actions** (Phase 6) — GitHub-hosted runners build the Action free for
  this repo.
