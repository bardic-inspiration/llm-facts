# Documentation standards

## Voice

- Concise and imperative. Short sentences. Say what to do.
- Skimmable: headings, tables, and lists over walls of prose.
- Write for a cold-start agent or a first-time contributor.

## Structure

- One canonical source per topic. Link to it; don't restate it. If two files
  would say the same thing, one owns it and the other links.
- Keep files short. If a doc grows past a screen or two, split it.
- Cross-link with relative paths so links work on GitHub and in clones.

## When a change needs docs

- New or changed behavior → update [`spec.md`](spec.md) (see
  [spec guidelines](spec-guidelines.md)) in the same PR.
- New workflow, command, or convention → update the relevant standards doc and
  link it from [`AGENTS.md`](../AGENTS.md).
- A PR that changes behavior without touching docs should say why in its
  description.

## Markdown conventions

- ATX headings (`#`), sentence case.
- Fenced code blocks with a language tag.
- Wrap prose near 88 columns to match code.
