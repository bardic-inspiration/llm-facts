# Docker image for the LLM Facts Action (spec §8).
#
# Self-contained by design: it bundles Python, the renderer, resvg (via the
# pinned resvg-py binding), and the vendored fonts, so it does not rely on
# whatever the runner has preinstalled. git is included because commit mode
# commits the regenerated label back to the branch (spec §8).
#
# Build context is the repository root (action.yml lives there), so the COPY
# lines below see pyproject.toml and the llm_facts package — templates/fonts/
# included — and `pip install .` installs the exact revision the workflow
# checked out. Nothing is fetched over the network, so private repos work too.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY llm_facts ./llm_facts
RUN pip install --no-cache-dir .

COPY action/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
