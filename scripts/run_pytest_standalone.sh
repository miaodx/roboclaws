#!/usr/bin/env bash
# Run pytest inside a minimal environment to avoid host-global Python contamination
# (e.g., ROS workspaces in PYTHONPATH on systems with ROS jazzy installed).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTEST_BIN="${PYTEST_BIN:-$REPO_ROOT/.venv/bin/pytest}"

if [[ ! -x "$PYTEST_BIN" ]]; then
    if ! command -v pytest >/dev/null 2>&1; then
        echo "run_pytest_standalone: pytest not found; install deps with uv pip install -e '.[dev]'" >&2
        exit 1
    fi
    PYTEST_BIN="$(command -v pytest)"
fi

env -i \
  PATH="$REPO_ROOT/.venv/bin:/usr/bin:/bin" \
  HOME="${HOME:-$REPO_ROOT}" \
  KIMI_API_KEY="${KIMI_API_KEY-}" \
  OPENAI_API_KEY="${OPENAI_API_KEY-}" \
  ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY-}" \
  NV_API_KEY="${NV_API_KEY-}" \
  NVIDIA_API_KEY="${NVIDIA_API_KEY-}" \
  MIMO_TP_KEY="${MIMO_TP_KEY-}" \
  CI="${CI:-}" \
  GITHUB_ACTIONS="${GITHUB_ACTIONS:-}" \
  "$PYTEST_BIN" "$@"
