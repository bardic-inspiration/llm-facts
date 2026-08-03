# LLM Facts Renderer — Build Spec

> Authoritative source of truth for the renderer's behavior. Change it via PR —
> see [spec-guidelines.md](spec-guidelines.md). Sections are referenced by
> number elsewhere (e.g. "spec §6").

Formatting only. Input is a conformant `.llm-facts.yml`; output is a rendered label. No telemetry collection, no log parsing, no data verification logic beyond internal consistency checks below. That's a separate project.

Stack: Python. CLI first; GitHub Action wraps the CLI.

---

## 1. Package layout

```
llm_facts/
  __init__.py
  schema.py           # pydantic models, schema v1
  loader.py            # ruamel.yaml load + validate, line-accurate errors
  layout.py            # row counts + text wrap -> Layout dataclass (slots, y-offsets, total_height)
  render_svg.py         # Jinja2 template -> SVG string
  render_raster.py       # SVG -> PNG via resvg
  render_md.py          # plain markdown table
  cli.py               # click entrypoints
  templates/
    label.svg.jinja
    blank.llm-facts.yml
    fonts/             # bundled .ttf: Archivo, Archivo Narrow, JetBrains Mono
action/
  action.yml
  Dockerfile           # python + resvg binary + fonts/
```

## 2. Schema (v1)

Implement as pydantic models in `schema.py`. Fields marked `(auto)` are populated by the separate data pipeline — this renderer treats them as ordinary optional fields, no special handling.

```yaml
schema_version: 1

serving:
  scope: repository | release | date-range
  period_start: date
  period_end: date | "ongoing"

summary:
  total_sessions: int
  total_tokens: int
  ai_touched_files_pct: int
  ai_touched_lines_pct: int

models:
  - name: str
    tokens: int
    sessions: int
    tool: str

tools:
  - name: str
    verified: bool

use:
  - category: boilerplate | refactor | debugging | tests | docs | review | design | other
    note: str

human:
  reviewed_by_human: bool
  note: str

label:
  verified: bool
  generated_by: str
  generated_at: datetime
```

All top-level keys except `schema_version` are optional. Missing optional field = omit that row/section, never render as zero or blank.

## 3. Validation rules

- Reject malformed YAML with file/line/col (use `ruamel.yaml`, not `pyyaml` — needed for position data).
- Unknown fields: ignore, but print a CLI warning. Never error on them.
- `models[].tokens` / `sessions` missing → omit that number from the row, don't render "0".
- `use[].category` outside the enum → accept it anyway, render as given (don't hard-fail on a subjective free-text-adjacent field).

## 4. CLI (click)

```
llm-facts init                    # scaffold blank .llm-facts.yml
llm-facts validate [path]         # schema check, exit code only
llm-facts render [path]
  --format svg|png|md|all         # default: png
  --out <dir>                     # default: dir of input yml
  --width <px>                    # default: 420
  --strict                        # see §6, fail instead of degrade
llm-facts render --print          # text preview, no file written
```

## 5. Layout → slot table

Fixed vertical stack. `layout.py` computes each slot's rendered height from actual data (row counts, text wrap at configured `--width`), returns a `Layout(slots, total_height, width)`. The Jinja template only places slots at pre-computed `y` offsets — no arithmetic in the template.

| Slot | Source | Cap | Height rule |
|---|---|---|---|
| Eyebrow | `label.generated_by`, `schema_version` | — | 18px fixed |
| Title + subtitle | static + `serving.scope` | — | 56px fixed |
| Serving info | `serving.*` | 2 rows | 16px × 2 |
| Big metrics | `summary.*` keys present | up to 4 across, wraps to 2×2 if >4 | 48px (1 row) / 90px (2 rows) |
| Models table | `models[]` | 5, then "+N more — see .llm-facts.yml" row | 22px × min(n,5) + 16px if truncated |
| Verification table | `tools[]` | 8 | 18px × min(n,8) |
| Use section | `use[]` | 6 | 30–48px per entry, wrap-dependent |
| Human box | `human.*` | — | 34px if key present at all, else 0 (section omitted) |
| Note line | static disclaimer + yml path | — | wraps ~2 lines, 24px |
| Footer | `label.generated_at`, `label.verified` | — | 22px fixed |

Rule dividers (thick/med/thin) between sections: fixed 3–8px, not listed per-row above — insert between every populated section, never before/after an omitted one.

Text wrap for `use[].note` and the footer disclaimer: estimate chars-per-line from `--width` and body font size; not true text measurement. Fine for v1.

`models[]` empty but `summary.total_sessions > 0`: render summary numbers as-is, show one placeholder row "No model breakdown provided" instead of blank space.

## 6. Internal consistency rules (render-time)

These check the label doesn't contradict itself — not whether the underlying data is true.

| Condition | Non-strict | `--strict` |
|---|---|---|
| `label.verified: true` but any `tools[].verified: false` | Render, footer shows "MIXED VERIFICATION" instead of "VERIFIED" | Exit non-zero, write nothing |
| `label.verified` absent | Footer shows "UNVERIFIED" | same |
| `tools[]` absent entirely | Omit verification section | same |

## 7. Rendering mechanics

- SVG built via Jinja2 template, not a headless browser. Deterministic: same YAML in → byte-identical SVG out.
- SVG → PNG via `resvg` (CLI binary or Python binding), not `cairosvg`.
- Fonts: GitHub's SVG sanitizer strips external font loading, so:
  - PNG output embeds bundled `.ttf`s (`templates/fonts/`) via `resvg --font-file` — full custom type.
  - SVG output falls back to system font stack (`system-ui, sans-serif` / `ui-monospace, monospace`) — documented, accepted degradation.
- Output paths: `llm-facts.png` / `.svg` / `.md` in `--out` dir (default: same dir as input yml).

## 8. GitHub Action

Docker-based (not composite) — needs the `resvg` binary and bundled fonts, can't rely on runner preinstalls.

Trigger: `push` on `paths: ['.llm-facts.yml']`, plus `workflow_dispatch`.

Inputs: `input` (default `.llm-facts.yml`), `output-dir` (default `.github/`), `format` (default `png`), `strict` (default `false`), `commit` (default `true`).

- `commit: true` → Action commits regenerated image back to the branch.
- `commit: false` → uploads as workflow artifact; fails run if committed image bytes differ from freshly rendered bytes.

## 9. Failure modes

| Case | Behavior |
|---|---|
| No `.llm-facts.yml` | CLI: suggest `init`. Action: fail, no fabricated label. |
| Malformed YAML | Fail with line/col, no partial output. |
| Any cap exceeded (models/tools/use) | Truncate + visible "+N more" row, never silent drop. |
| `--strict` + §6 violation | Non-zero exit, no file written. |

## 10. Out of scope

Log/telemetry parsing for any coding tool, token/session counting, git-blame-based percentages, proof of data accuracy, repo write-access control.

## 11. Build order (suggested)

1. `schema.py` + `loader.py` + `validate` CLI command — get validation solid first, everything else depends on it.
2. `layout.py` slot/height logic against fixture YAMLs (minimal, typical, maxed-out/truncated cases).
3. `label.svg.jinja` + `render_svg.py`.
4. `render_raster.py` (resvg integration).
5. `render_md.py` (trivial, do last).
6. CLI wiring (`cli.py`).
7. Action Dockerfile + `action.yml`, test in a scratch repo.
