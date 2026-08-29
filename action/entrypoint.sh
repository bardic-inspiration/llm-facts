#!/usr/bin/env bash
# Entrypoint for the LLM Facts Action (spec §8).
#
# Positional args, forwarded from action.yml inputs:
#   $1 input       path to the .llm-facts.yml            (default .llm-facts.yml)
#   $2 output-dir  directory to write the label into     (default .github/)
#   $3 format      svg | png | md | all                  (default png)
#   $4 strict      "true"/"false" — fail on a §6 clash    (default false)
#   $5 commit      "true"/"false" — commit vs drift-check (default true)
set -euo pipefail

INPUT="${1:-.llm-facts.yml}"
OUTPUT_DIR="${2:-.github/}"
FORMAT="${3:-png}"
STRICT="${4:-false}"
COMMIT="${5:-true}"

WORKSPACE="${GITHUB_WORKSPACE:-$(pwd)}"
cd "$WORKSPACE"

# The checkout is owned by a different uid inside the container.
git config --global --add safe.directory "$WORKSPACE" 2>/dev/null || true

# No input file → fail loudly; never fabricate a label (spec §9).
if [ ! -f "$INPUT" ]; then
  echo "::error::input file not found: $INPUT" >&2
  exit 1
fi

strict_flag=()
if [ "$STRICT" = "true" ]; then
  strict_flag=(--strict)
fi

render() {
  llm-facts render "$INPUT" --format "$FORMAT" --out "$OUTPUT_DIR" "${strict_flag[@]}"
}

if [ "$COMMIT" = "true" ]; then
  # commit: true → regenerate and commit the label back to the branch (spec §8).
  render
  git config user.name "${GIT_AUTHOR_NAME:-github-actions[bot]}"
  git config user.email \
    "${GIT_AUTHOR_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}"
  git add "$OUTPUT_DIR"
  if git diff --cached --quiet; then
    echo "label already up to date — nothing to commit"
  else
    git commit -m "chore(llm-facts): regenerate label"
    git push
  fi
else
  # commit: false → re-render, then fail if the committed label is stale
  # (bytes differ from a fresh render). The fresh files stay in output-dir for
  # a follow-up actions/upload-artifact step in the caller's workflow (spec §8).
  render
  if [ -n "$(git status --porcelain -- "$OUTPUT_DIR")" ]; then
    echo "::error::committed label is stale — run 'llm-facts render' and commit it" >&2
    git --no-pager diff -- "$OUTPUT_DIR" >&2 || true
    exit 1
  fi
  echo "label is up to date"
fi
