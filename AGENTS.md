# Python Environment

Use the `.venv` virtual environment for all Python development in this project. Install dependencies only into `.venv`, never into the system Python.

# Language

Create all generated artifacts in English unless explicitly asked otherwise.

# Secrets

Never expose private data from environment files in the context window, whether by directly reading files, using commands such as `cat`, `head`, `tail`, or `grep`, or through scripts or any other extraction method.

# Design

Apply YAGNI and KISS: implement only what is needed, using the simplest clear solution.

# GitHub CLI

Run `gh` commands outside the sandbox.

# Container Runtime

Use Docker Compose for deployment and configured end-to-end runs. Before starting, verify required configuration without printing environment-file values.

Production uses published images. Staging uses the single shared `little-jukebox:local` image with `JUKEBOX_PULL_POLICY=never`. Build and reuse that exact local image tag for all development and staging tests. Do not create per-task, per-agent, branch-specific, commit-specific, or timestamped local image tags unless the user explicitly requests isolated images.

Production and staging must use distinct `COMPOSE_PROJECT_NAME`, ingress alias, and application base path. Do not set `container_name` or bypass Compose with `docker run`.
