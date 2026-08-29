<!--
One PR = one issue = one build-order concern. See AGENTS.md and CONTRIBUTING.md.

Docs/spec-only PR (Markdown files only, no code)? Use the leaner checklist
below and skip the code one — see docs/docs-only-changes.md. Mixing a doc
edit with any code change makes it a code change; use the code checklist.
-->

## Summary

<!-- What does this PR do, in one or two sentences? -->

## Linked issue

<!-- e.g. Closes #12 -->

<!-- Trivial docs/spec fixes (typos, broken links) may omit this — see docs/docs-only-changes.md. -->

## Spec section

<!-- Which part of docs/spec.md does this implement or change? e.g. §2 schema -->

## Testing

<!-- What did you test and how? Fixtures used, cases covered. N/A for docs-only PRs. -->

## Checklist — code changes

- [ ] Tests written first (TDD) and passing — `pytest` green
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] Commits are atomic and in Conventional Commits format
- [ ] Docs/spec updated if behavior changed
- [ ] Change stays within scope (spec §10 boundaries respected)

## Checklist — docs/spec-only changes

<!-- Use instead of the code checklist above. See docs/docs-only-changes.md. -->

- [ ] Every changed file is Markdown — no `llm_facts/`, `tests/`, `action/`, or `.github/workflows/` changes
- [ ] Atomic commits in Conventional Commits format (`docs: ...`)
- [ ] Cross-references updated where a shared term or section number changed (docs/documentation-standards.md)
- [ ] If `docs/spec.md` changed: versioned per docs/spec-guidelines.md

## TL;DR

<!--
Required. Plain English, no software-expert jargon, bullet points — explain
this like you're telling a friend who doesn't code. Cover:
- Why: what problem or reason this PR exists for.
- Impact: what changes for someone using or building the project.
-->

-
