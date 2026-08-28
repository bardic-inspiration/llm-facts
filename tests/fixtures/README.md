# Test fixtures

Shared `.llm-facts.yml` inputs every phase tests against. Tests read these
files rather than hand-building large YAML inline
(see [testing standards](../../docs/testing-standards.md)). They are the
reference inputs later phases assert against, so keep them consistent with the
schema in [spec §2](../../docs/spec.md).

| Fixture | Purpose |
|---|---|
| `minimal.llm-facts.yml` | The required `schema_version` plus a single section. Everything else absent — proves optional sections are omitted, not zeroed (spec §2). |
| `typical.llm-facts.yml` | A realistic label exercising most sections, all within caps (models ≤ 5, tools ≤ 8, use ≤ 6). The everyday reference input. |
| `maxed.llm-facts.yml` | Every cap exceeded (6 models, 9 tools, 7 use) to drive "+N more" truncation (spec §5, §9). Also carries a model with `tokens` omitted (stays absent, never `0`) and one out-of-enum `use.category` (accepted as-is) — spec §3. |
| `malformed.llm-facts.yml` | Invalid YAML (an unclosed flow sequence) that fails with a knowable file/line/column, for the loader's error-path tests (spec §3, §9). |

The malformed fixture is broken on purpose; do not repair it.
