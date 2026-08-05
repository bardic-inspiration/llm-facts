# Roadmap

The phased view of the [build spec §11](spec.md). Each phase is a slice of the
renderer that lands as a small set of atomic, test-first PRs. Phases are
sequential — each builds on the one before.

**How this drives the build:** each phase's work is tracked as GitHub issues
(the [feature/task template](../.github/ISSUE_TEMPLATE/feature_task.md)), labeled
`phase:N`. Scheduled agents pull the lowest open issue in the active phase, follow
the [working loop](../AGENTS.md#working-loop), and open one PR per issue. A phase
is done when every issue under its label is closed and its exit criteria hold.

Status legend: `planned` · `in progress` · `done`.

## Phase 1 — Validation foundation · `in progress`

- **Goal:** load and validate a `.llm-facts.yml`; `llm-facts validate` works end
  to end.
- **Spec:** §2 (schema), §3 (validation), §4 (`validate`), §11.1.
- **Deliverables:** `schema.py`, `loader.py`, the `validate` CLI command, and the
  shared test fixtures.
- **Exit criteria:** `validate` returns correct exit codes across the
  minimal / typical / maxed fixtures; malformed YAML reports file/line/col;
  unknown fields warn (never error); full TDD coverage; CI green.

## Phase 2 — Layout engine · `planned`

- **Goal:** deterministic slot and height computation from validated data.
- **Spec:** §5 (layout → slot table), §11.2.
- **Deliverables:** `layout.py` → `Layout(slots, total_height, width)`.
- **Exit criteria:** layout tests assert slot presence, caps and "+N more"
  truncation, height rules, and section-omission-vs-zero across the fixtures.

## Phase 3 — SVG renderer · `planned`

- **Goal:** render a `Layout` to a deterministic SVG string.
- **Spec:** §5 (template places pre-computed slots, no arithmetic), §7
  (determinism, system-font fallback), §11.3.
- **Deliverables:** `templates/label.svg.jinja`, `render_svg.py`.
- **Exit criteria:** byte-identical SVG for identical input; system-font stack in
  SVG output; no arithmetic in the template.

## Phase 4 — Raster & Markdown outputs · `planned`

- **Goal:** PNG via resvg with embedded fonts; a plain Markdown table.
- **Spec:** §7 (resvg, font embedding), §11.4–5.
- **Deliverables:** `render_raster.py`, `render_md.py`, bundled fonts under
  `templates/fonts/`.
- **Exit criteria:** PNG embeds the bundled `.ttf`s; Markdown table renders;
  raster path is deterministic.
- **De-risk first:** resvg and the fonts are free but not pre-provisioned — see
  [Dependencies](#dependencies). Run the resvg spike before building on it.

## Phase 5 — CLI surface · `planned`

- **Goal:** the full click CLI — `init`, `render` with `--format/--out/--width/
  --strict/--print` — wired to the render pipeline.
- **Spec:** §4 (CLI), §6 (`--strict`), §9 (failure modes), §11.6.
- **Deliverables:** `cli.py`, `templates/blank.llm-facts.yml`; enable the
  `llm-facts` console script in `pyproject.toml`.
- **Exit criteria:** every command works; `--strict` exits non-zero and writes
  nothing on a §6 violation; a missing file suggests `init`.

## Phase 6 — GitHub Action · `planned`

- **Goal:** a Docker-based Action wrapping the CLI.
- **Spec:** §8, §11.7.
- **Deliverables:** `action/Dockerfile`, `action/action.yml`.
- **Exit criteria:** renders on push to `.llm-facts.yml`; `commit` and artifact
  modes both work; verified in a scratch repo.

## Dependencies

All tooling is free and open-source; two items need sourcing before Phase 4:

- **Python deps** (pydantic, ruamel.yaml, jinja2, click, pytest, ruff) — pinned in
  `pyproject.toml`, installed in CI. No action needed.
- **resvg** (Phase 4) — free (MPL/MIT), but a Rust binary/binding. Spike at
  Phase 4 start: confirm a pip-installable binding or a pinned release binary runs
  in CI *and* the Docker image before depending on it.
- **Fonts** (Phase 4) — Archivo, Archivo Narrow, JetBrains Mono, all SIL Open Font
  License. Fetch and vendor the `.ttf`s into `templates/fonts/`; free to
  redistribute.
- **Docker + Actions** (Phase 6) — GitHub-hosted runners build the Action free for
  this repo.
