# Spec guidelines

How to read and change [`spec.md`](spec.md).

## The spec is authoritative

`spec.md` defines what the renderer does. When code and spec disagree, the spec
wins — fix the code, or change the spec first. Never encode undocumented
behavior.

## Changing the spec

- Spec changes go through a PR, like code. State the motivation.
- A spec change that alters behavior lands **before or with** the code and tests
  that implement it — never after.
- Keep the numbered sections and tables intact; agents and issues reference them
  by number (e.g. "spec §6").

## Keep in sync

- **Schema (§2)** ↔ `llm_facts/schema.py`. New or renamed fields change both.
- **Layout table (§5)** ↔ `llm_facts/layout.py`. Slot caps and height rules are
  the contract layout tests assert.
- **Consistency rules (§6)** ↔ render-time checks and their tests.
- **Out of scope (§10)** is a hard boundary. Adding anything listed there is a
  new project, not a PR here.

## When in doubt

Open an issue that quotes the spec section and asks the question. Don't guess in
code.
