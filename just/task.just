# Human-facing task grammar.
#
# Canonical form:
#   just task::run <task> <driver> [report|profile] [key=value ...]
#
# Tasks:
#   ai2thor-nav | territory | coverage | photo-chairs | semantic-map-build |
#   household-cleanup | molmo-planner-proof
#
# Drivers:
#   openclaw | vlm | codex | claude | script | direct | mcp-smoke
#
# Reports:
#   visual  - default for non-Molmo tasks, reviewable artifacts for humans
#   minimal - cheaper semantic evidence for non-Molmo agent iteration
#
# Household task profiles:
#   smoke | world-labels | camera-raw | camera-labels

set working-directory := '..'
set positional-arguments

[private]
default:
    @just --list task

# Run a human-facing task through a driver.
run task driver mode="" *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    python_bin="${ROBOCLAWS_DEVTOOLS_PYTHON:-}"
    if [[ -z "$python_bin" ]]; then
      if [[ -x .venv/bin/python ]]; then
        python_bin=".venv/bin/python"
      elif command -v python3 >/dev/null 2>&1; then
        python_bin="python3"
      else
        python_bin="python"
      fi
    fi
    exec "$python_bin" -m roboclaws.devtools.commands task run "$@"
