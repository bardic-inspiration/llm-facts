# Commit standards

Commits are **atomic** and follow **Conventional Commits**.

## Atomic

- One logical change per commit. It builds and the suite passes at that commit.
- Don't mix concerns (e.g. a feature and an unrelated rename) in one commit.
- Don't split one logical change across commits that each leave the tree broken.

## Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`.
- **scope** (optional): the area, e.g. `schema`, `layout`, `cli`, `action`.
- **subject**: imperative, lower-case, no trailing period, ≤ ~72 chars.
- **body** (optional): *why*, not *what* — the diff shows what. Wrap near 72.
- **footer** (optional): `Refs #12`, `Closes #12`.

## Examples

```
feat(schema): add pydantic models for schema v1

Cover serving, summary, models, tools, use, human, label. All top-level
keys optional per spec §2.

Refs #3
```

```
test(loader): pin line/col reporting for malformed yaml
```

## History: no merge commits

History stays linear — every commit is discrete and independently legible, which
matters for agents reading `git log`. No merge commits, ever.

- **Integrate `main` by rebasing, not merging:**
  `git fetch origin && git rebase origin/main`. Same when updating a PR branch or
  resolving conflicts — rebase, don't merge.
- **Land PRs with "Rebase and merge."** It replays the branch's atomic commits
  onto `main` and keeps them separate. Never "Create a merge commit"; never
  "Squash and merge" (it fuses discrete commits into one).
- **Keep a branch's commits clean:** amend or `git rebase -i` to fold
  work-in-progress and "address review" fixups into the commit they belong to,
  rather than stacking noise commits.

## TDD and commits

TDD happens locally: write the failing test, then the code. Commit them together
as one atomic change so every commit on the branch builds green. If you must
commit a not-yet-passing test, mark it `xfail`/`skip` with a reason so CI stays
green. See [testing standards](testing-standards.md).
