"""Smoke test: the package imports and exposes a version.

Placeholder until real behavior lands under the TDD workflow
(see docs/testing-standards.md). Keeps the suite green from day one.
"""

import llm_facts


def test_version_is_exposed() -> None:
    assert isinstance(llm_facts.__version__, str)
    assert llm_facts.__version__
