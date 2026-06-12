# Human-facing surface grammar.
#
# Canonical form:
#   just run::surface surface=<surface> driver=<driver> [intent=<intent>] [key=value ...]
#
# Surfaces:
#   household-world | ai2thor-world | ai2thor-games | planner-proof
#
# Intents:
#   cleanup | open-ended | map-build | navigate | photo-capture |
#   territory | coverage | planner-proof

set working-directory := '..'
set positional-arguments

[private]
default:
    @just --list run

# Run a canonical surface/intent route through a driver.
surface *overrides:
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
    exec "$python_bin" -m roboclaws.cli.main run surface "$@"
