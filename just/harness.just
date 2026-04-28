# Self-improvement loop runner for the AI2-THOR navigator skill.
#
# Each run spawns a fresh `just code::cc` agent in a tmux session, sends the
# task, monitors via the MCP trace.jsonl, captures metrics, and tears down.
# Curated logbook lives in harness/PLAN.md.
#
# Preferred entrypoints:
# - just harness::run <task>          run one iteration on a task
# - just harness::list-tasks          show available task definitions
# - just harness::history             show the cross-run summary from PLAN.md

set working-directory := '..'

default:
    @just --list harness

# Run one iteration of the harness on a named task.
# `task` is REQUIRED (no default — see PLAN.md for why curated experiments
# beat default-task convenience). `cap` is the wall-clock cap in seconds.
#
# Examples:
#   just harness::run photo-living-room
#   just harness::run photo-living-room 600
run task cap="900":
    bash harness/run-next.sh "{{task}}" "{{cap}}"

# List task files available under harness/tasks/.
list-tasks:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! ls harness/tasks/*.txt >/dev/null 2>&1; then
      echo "no tasks yet — drop one at harness/tasks/<name>.txt"
      exit 0
    fi
    echo "Available tasks (harness/tasks/):"
    for f in harness/tasks/*.txt; do
      base=$(basename "$f" .txt)
      first_line=$(head -1 "$f")
      printf "  %-30s %s\n" "$base" "${first_line:0:80}"
    done

# Show the cross-run summary table from PLAN.md, if present.
# Falls back to listing run_ids when no table is found.
history:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "## Logged runs (harness/PLAN.md):"
    echo
    grep -E '^## Run [0-9]+' harness/PLAN.md 2>/dev/null || echo "  (none yet)"
    # If a markdown table exists in any run entry, print the most recent one.
    # If a markdown table exists in any run entry, print the most recent one.
    last_header=$(grep -nE '^\| Run ' harness/PLAN.md 2>/dev/null | tail -1 | cut -d: -f1)
    if [[ -n "$last_header" ]]; then
      echo
      echo "## Most recent cross-run summary table:"
      # Print from the header through the contiguous table block.
      tail -n +"$last_header" harness/PLAN.md | awk '
        /^\|/ { print; next }
        { exit }
      '
    fi
