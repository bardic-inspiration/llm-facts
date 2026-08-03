# Testing standards

**TDD is the required workflow.** Write a failing test before the code that makes
it pass. Every behavior in the [spec](spec.md) is pinned by a test.

## The loop

1. **Red** — write a test for one spec behavior. Run it; watch it fail for the
   right reason.
2. **Green** — write the smallest code that passes.
3. **Refactor** — clean up with the suite green.

Repeat per behavior, not per module. Small steps.

## What to test

- **Schema (§2)** — each field optional vs required, type coercion, unknown-field
  warnings (not errors).
- **Validation (§3)** — malformed YAML reports file/line/col; missing numbers
  omit rather than render `0`; out-of-enum `use.category` is accepted.
- **Layout (§5)** — slot presence, caps and "+N more" truncation, height rules,
  section omission vs zero.
- **Consistency (§6)** — VERIFIED / MIXED / UNVERIFIED footer states; `--strict`
  exits non-zero and writes nothing.
- **Determinism (§7)** — same YAML in → byte-identical SVG out.
- **Failure modes (§9)** — missing file, malformed YAML, cap exceeded.

## Fixtures

Keep `.llm-facts.yml` fixtures under `tests/fixtures/`, at least:

- `minimal.llm-facts.yml` — one or two sections only.
- `typical.llm-facts.yml` — a realistic label.
- `maxed.llm-facts.yml` — every cap exceeded (models/tools/use) to exercise
  truncation.

Tests read fixtures; they don't hand-build large YAML inline.

## Layout

- `tests/` mirrors `llm_facts/` (`test_schema.py`, `test_loader.py`, …).
- Name tests for the behavior:
  `test_strict_exits_nonzero_on_mixed_verification`.
- Prefer plain `assert`; use `pytest.mark.parametrize` for enum and table cases.

## Bar for merge

- The suite is green. No test is skipped without an inline reason.
- New behavior arrives with tests in the same PR.
- A bug fix arrives with a regression test that fails before the fix.
- Determinism tests must pass — a non-deterministic renderer is a bug.

## Running

```
pytest                              # whole suite
pytest tests/test_layout.py -k truncation
```

CI runs `pytest` on Python 3.11 and 3.12; both must pass.
