# Standalone Codex operator console.

set working-directory := '..'

[private]
default:
    @just --list console

# Run the standalone local operator console.
run host="0.0.0.0" port="8765":
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
    exec "$python_bin" -m roboclaws.operator_console --host "{{host}}" --port "{{port}}" --repo-root "$PWD"
