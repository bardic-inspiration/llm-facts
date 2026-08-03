# CLAUDE.md

Claude Code specific notes. **Read [`AGENTS.md`](AGENTS.md) first** — it is the
canonical guide (purpose, hard rules, layout, build order, working loop). This
file only adds Claude-Code specifics.

## Before you start

- The build is delegated to agents via scheduled tasks; you may cold-start on a
  single build-order step. Scope your work to that step's issue and its spec
  section — don't range ahead into later steps.
- Read the relevant section of [`docs/spec.md`](docs/spec.md) before touching
  code.

## Workflow

- **TDD, always.** Failing test first
  ([`docs/testing-standards.md`](docs/testing-standards.md)). A red → green →
  refactor cycle fits this repo well.
- Run `ruff check . && ruff format . && pytest` before every commit; CI runs the
  same and must be green before merge.
- Atomic commits, Conventional Commits format
  ([`docs/commit-standards.md`](docs/commit-standards.md)).
- One build-order concern per PR; fill in the PR template.

## Useful commands

```
pip install -e .[dev]     # install with dev tools
pytest                    # run the suite
ruff check . && ruff format .
```
