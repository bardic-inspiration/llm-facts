# Issue Standards

The canonical reference for opening, scoping, and closing issues. The goal is
**iterative, traceable work**: every PR maps to exactly one issue, every issue
maps to a spec section, and anything that surfaces mid-work but isn't in scope
gets a paper trail instead of getting lost or silently folded in.

## Picking up an issue

- Pick the **lowest-numbered open issue** in the active phase — see
  [`roadmap.md`](roadmap.md) for current phase status and which deliverables
  belong to it.
- Read the [`docs/spec.md`](spec.md) section it references before touching
  code. The [Hard rules](../AGENTS.md#hard-rules) hold regardless of phase.
- Scope work to **that issue only** — don't range ahead into a later phase and
  don't pull in adjacent cleanup that isn't part of the acceptance criteria.

## Filing an issue

Use the template that fits:

- **[Feature / build task](../.github/ISSUE_TEMPLATE/feature_task.md)** — a
  build-order step or new capability sized for one PR. Requires: Goal, spec
  reference, testable acceptance criteria, fixtures/cases, and an explicit
  "Out of scope" note.
- **[Bug report](../.github/ISSUE_TEMPLATE/bug_report.md)** — behavior that
  contradicts the spec. Requires: what happened, expected behavior with a
  spec citation, a minimal reproduction (a `.llm-facts.yml` or a
  `tests/fixtures/` reference), and environment (version, Python, output
  format).

Other requirements, both templates:

- **Acceptance criteria must be testable statements.** They are the
  pre-written failing tests for TDD ([`testing-standards.md`](testing-standards.md))
  — if a criterion can't become a test, it isn't specific enough yet.
- **End with a TL;DR.** Every issue closes with a `## TL;DR` section: a few
  plain-English bullet points, no software-expert jargon, ELI5 style,
  covering why the issue exists and what its impact is. Someone unfamiliar
  with the code should be able to read just that section and get the point.
  Both issue templates already have the section built in — fill it in, don't
  delete it.
- **Label** with `task` or `bug` as appropriate. Work that falls under spec
  §10 (out of scope) does not get filed at all — it isn't a future issue,
  it's a different project.

## Scope discipline

- **One issue = one PR = one build-order concern.** If the work doesn't fit
  in a single PR, it isn't one issue — split it before starting, not
  mid-implementation.
- State explicitly what's **out of scope** in the issue body. This is the
  primary guard against scope creep into spec §10 items.
- **Implement the acceptance criteria — not more.** Once you're in the code,
  the issue's acceptance criteria are the entire spec for the PR. A file the
  acceptance criteria don't mention isn't part of this PR, even if the
  change is one line and obviously correct.
- A PR that touches more than its issue's concern is a sign the issue was
  under-scoped, not license to expand the PR — file the extra ground as its
  own issue (see below) and keep the PR narrow.
- This matters more here than in a single-contributor repo: the build is
  worked by many independent, memoryless agent sessions. Nobody is tracking
  "temporary" scope expansion across sessions, so an out-of-scope change
  doesn't get cleaned up later — it just becomes permanent drift from the
  issue trail. Treat every PR's diff as if a reviewer will check it
  file-by-file against the acceptance criteria, because eventually one will.

## Docs-only issues & PRs

Changes that touch only Markdown — no code, fixtures, or CI/config — follow a
leaner path than the rest of this doc: lighter issue filing, no TDD/CI gate.
See [`docs-only-changes.md`](docs-only-changes.md) for the full protocol and
the [Docs / spec change template](../.github/ISSUE_TEMPLATE/docs_change.md).
Everything else in this doc assumes a code change.

## Linking issues to PRs

- Every PR closes exactly one issue: `Closes #N` in the PR description
  (`.github/pull_request_template.md`). Trivial docs-only PRs (typos, broken
  links) are exempt — see [`docs-only-changes.md`](docs-only-changes.md).
- State the spec section the issue implements or affects in the PR — the
  reviewer should be able to trace PR → issue → spec section without asking.
- **End the PR with a TL;DR too**, same rule as issues: a few plain-English,
  jargon-free bullet points (ELI5 style) covering why the change was made
  and what its impact is. The PR template
  (`.github/pull_request_template.md`) has the section built in.
- Issues close **only** via a merged PR carrying `Closes #N`. Don't close an
  issue by hand outside that flow — it breaks the trace from issue to the
  commit that resolved it.
- If an issue turns out invalid, superseded, or out of scope after all,
  close it with a comment stating why rather than deleting it or letting it
  go stale silently.

## Open questions & sub-issues that surface mid-work

Cold-start sessions and reviewers alike surface things beyond the one issue
in front of them — edge cases, ambiguities, follow-on work. Handle these
without losing scope or traceability:

- **Don't solve it inline.** Finish the issue you were given first. An open
  question is not license to widen the current PR.
- **Spec ambiguity or defect** (the acceptance criteria conflict with
  `docs/spec.md`, or the spec looks wrong) → do not silently invent
  behavior. Follow [`spec-guidelines.md`](spec-guidelines.md): raise it and,
  if it's a genuine defect, amend the spec deliberately before writing code
  that guesses.
- **Everything else** (an out-of-scope edge case, a deferred feature, tech
  debt, a later-phase idea) → file it as a **new issue** using the criteria
  above, not a `TODO` comment or a note buried in a PR description that will
  rot.
  - Reference the originating issue/PR in the new issue's body (e.g.
    "Surfaced while working #N") so the chain is traceable later.
- **Link back once.** In the PR that surfaced the question, add a single
  line noting the new issue number (e.g. "opened #N for X, out of scope
  here"). Don't re-explain it in every later PR that touches nearby code —
  the issue link is the record.
- **Don't block on it.** An unresolved sub-issue should not stall the
  current issue's merge, unless it's the spec-ambiguity case above, where
  guessing would risk producing behavior the spec doesn't define.

## Quick decision rule

When something unplanned comes up mid-issue, ask one question: **does
proceeding require guessing at spec-defined behavior?**

- Yes → stop, don't guess, resolve via [`spec-guidelines.md`](spec-guidelines.md)
  before continuing.
- No → keep going on the current issue; file a new issue for the rest.
