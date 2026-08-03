# Contributing

Thanks for helping build **llm-facts**. This project is built test-first, in
small atomic steps. Read the [agent guide](AGENTS.md) for the big picture and the
[build spec](docs/spec.md) for authoritative behavior.

## Setup

```
git clone https://github.com/bardic-inspiration/llm-facts
cd llm-facts
pip install -e .[dev]
pytest
```

## Branching

- Branch off `main`. Name branches `type/short-description`
  (e.g. `feat/schema-models`, `fix/loader-line-numbers`).
- One concern per branch and PR.

## Workflow (TDD, required)

1. Open or claim an issue (feature/task template) tied to a spec section.
2. Write failing tests first — see [testing standards](docs/testing-standards.md).
3. Implement the minimum to pass; refactor with the suite green.
4. `ruff check . && ruff format . && pytest` must pass locally.

## Commits

Atomic, [Conventional Commits](docs/commit-standards.md) format. One logical
change per commit; imperative subject; the body says *why*.

## Pull requests

- Fill in the [PR template](.github/pull_request_template.md) — link the issue,
  name the spec section, describe testing.
- CI (lint + tests, Python 3.11/3.12) must be green.
- Keep the diff scoped; unrelated cleanups go in their own PR.

## Standards index

[Spec guidelines](docs/spec-guidelines.md) ·
[Testing](docs/testing-standards.md) · [Commits](docs/commit-standards.md) ·
[Documentation](docs/documentation-standards.md).
