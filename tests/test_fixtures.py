"""Fixture sanity checks.

This issue creates the shared fixtures; it adds no domain logic. These trivial
checks keep CI meaningful: the three valid fixtures parse as YAML, the malformed
one does not, and the caps in ``maxed`` really are exceeded (so later phases have
something to truncate). Schema, loader, and layout behavior are pinned by their
own test modules.
"""

from pathlib import Path

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

FIXTURES = Path(__file__).parent / "fixtures"
VALID = ["minimal", "typical", "maxed"]


def _load(name: str):
    with (FIXTURES / f"{name}.llm-facts.yml").open() as handle:
        return YAML().load(handle)


@pytest.mark.parametrize("name", VALID)
def test_valid_fixtures_parse_as_yaml(name: str) -> None:
    data = _load(name)
    assert isinstance(data, dict)
    assert data["schema_version"] == 1


def test_malformed_fixture_does_not_parse() -> None:
    with pytest.raises(YAMLError):
        _load("malformed")


def test_maxed_fixture_exceeds_every_cap() -> None:
    data = _load("maxed")
    assert len(data["models"]) > 5
    assert len(data["tools"]) > 8
    assert len(data["use"]) > 6


def test_readme_lists_each_fixture() -> None:
    readme = (FIXTURES / "README.md").read_text()
    for name in [*VALID, "malformed"]:
        assert f"{name}.llm-facts.yml" in readme
