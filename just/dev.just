# Dev workflow — git hooks, pytest split, repo-wide self-check.
#
# Test split invariant:
#   - test-fast        : what the pre-commit hook runs (no Docker, no real provider).
#   - test-integration : what the post-merge hook runs in background
#                        (Docker-gated tests + anything touching a real
#                        model provider).
# Integration tests should never fire on every `git commit`. They live behind
# `@pytest.mark.integration`.

set working-directory := '..'

strip_ros_env := "env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION"

# Default: list module recipes (avoids accidentally rewiring git hooks).
default:
    @just --list dev

# Point core.hooksPath at .githooks/.
install-hooks:
    @git config core.hooksPath .githooks
    @echo "==> git hooks installed (core.hooksPath = .githooks)"
    @echo "    pre-commit : ruff + fast pytest"
    @echo "    post-merge : integration tests, backgrounded, log in .git/integration-last.log"
    @echo "    bypass     : git commit --no-verify   or   SKIP_TESTS=1 git commit"

# Reset core.hooksPath.
uninstall-hooks:
    -@git config --unset core.hooksPath
    @echo "==> git hooks uninstalled (core.hooksPath reset)"

# Fast tests: what pre-commit runs (no Docker, no real provider API calls).
test-fast:
    @{{strip_ros_env}} .venv/bin/pytest -m "not integration" -q --durations=5

# Integration tests: Docker-gated + real provider, what post-merge runs.
test-integration:
    @{{strip_ros_env}} .venv/bin/pytest -m integration -q --durations=10

# Pulls the pinned Gateway image (so live catalog tests don't silently skip),
# then runs the full pytest suite. ~2-3 min; if anything fails, the repo's
# contract with the new image is broken and CI/Railway will too.
# Self-check — one command that proves the repo still works end-to-end.
selfcheck:
    #!/usr/bin/env bash
    set -euo pipefail
    OPENCLAW_IMG="ghcr.io/openclaw/openclaw:2026.4.24"
    if ! command -v docker >/dev/null 2>&1; then
      echo "warning: docker not on PATH — live OpenClaw tests will skip"
    elif ! docker image inspect "$OPENCLAW_IMG" >/dev/null 2>&1; then
      echo "==> pulling $OPENCLAW_IMG (one-time, ~700MB)"
      docker pull "$OPENCLAW_IMG" >/dev/null \
        || echo "warning: docker pull failed — live OpenClaw tests will skip"
    else
      echo "==> $OPENCLAW_IMG already cached"
    fi
    echo "==> running full pytest (mocks + live image probes)"
    {{strip_ros_env}} .venv/bin/pytest -q --durations=5
