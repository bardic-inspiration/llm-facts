"""GitHub Action metadata & wiring (spec §8, §11.7).

Phase 6 ships a Docker-based Action wrapping the CLI. There is no Actions
runner here to exercise a live job, so these tests pin the parts that are
checkable offline and deterministically: the input contract and defaults from
spec §8, and that the metadata, Dockerfile, and entrypoint are wired together.

Layout note: ``action.yml`` lives at the repository root (not under ``action/``)
so a Docker *container* action builds with the repo root as its build context —
the only way the Dockerfile can ``pip install`` the co-located ``llm_facts``
package (fonts included) without fetching the source over the network, which
also keeps it working for private repositories. The ``Dockerfile`` and
``entrypoint.sh`` live under ``action/`` per the spec §1 layout.
"""

from pathlib import Path

from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTION_YML = REPO_ROOT / "action.yml"
DOCKERFILE = REPO_ROOT / "action" / "Dockerfile"
ENTRYPOINT = REPO_ROOT / "action" / "entrypoint.sh"


def _action() -> dict:
    with ACTION_YML.open(encoding="utf-8") as handle:
        return YAML(typ="safe").load(handle)


# --- Files exist ------------------------------------------------------------


def test_action_files_exist() -> None:
    assert ACTION_YML.is_file(), "action.yml must live at the repo root"
    assert DOCKERFILE.is_file(), "action/Dockerfile must exist"
    assert ENTRYPOINT.is_file(), "action/entrypoint.sh must exist"


# --- Inputs & defaults (spec §8) --------------------------------------------


def test_inputs_match_spec_section_8() -> None:
    inputs = _action()["inputs"]
    assert set(inputs) == {"input", "output-dir", "format", "strict", "commit"}


def test_input_defaults_match_spec_section_8() -> None:
    inputs = _action()["inputs"]
    # GitHub treats input defaults as strings — quoted, so booleans stay strings.
    assert inputs["input"]["default"] == ".llm-facts.yml"
    assert inputs["output-dir"]["default"] == ".github/"
    assert inputs["format"]["default"] == "png"
    assert inputs["strict"]["default"] == "false"
    assert inputs["commit"]["default"] == "true"


# --- Docker wiring (spec §8) ------------------------------------------------


def test_runs_is_a_docker_action() -> None:
    runs = _action()["runs"]
    assert runs["using"] == "docker"
    # Container action, not composite (spec §8); Dockerfile lives under action/.
    assert runs["image"] == "action/Dockerfile"


def test_all_inputs_are_forwarded_to_the_container() -> None:
    args = _action()["runs"]["args"]
    joined = " ".join(str(a) for a in args)
    for name in ("input", "output-dir", "format", "strict", "commit"):
        assert f"inputs.{name}" in joined, name


# --- Dockerfile is self-contained (spec §8) ---------------------------------


def test_dockerfile_installs_the_renderer_and_git() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "pip install" in text  # bundles the renderer (resvg-py + fonts)
    assert "git" in text  # commit mode needs git (spec §8)
    assert "llm_facts" in text  # copies the package into the build
    assert "entrypoint.sh" in text  # wired to the entrypoint


# --- Entrypoint covers both modes (spec §8) ---------------------------------


def test_entrypoint_covers_commit_and_artifact_modes() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")
    assert "llm-facts render" in text  # wraps the CLI
    assert "git commit" in text  # commit: true → commit back
    assert "git status" in text or "git diff" in text  # commit: false → drift check
