# Self-improvement loop runner for the AI2-THOR navigator skill.
#
# Each run spawns a fresh `just code::cc` agent in a tmux session, sends the
# task, monitors via the MCP trace.jsonl, captures metrics, and tears down.
# Curated logbook lives in harness/PLAN.md.
#
# Preferred entrypoints:
# - just harness::run <task>          run one iteration on a task
# - just harness::navigator <task>    explicit navigator-harness alias
# - just harness::regression          capture/analyze baseline vs candidate
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
    just harness::navigator "{{task}}" "{{cap}}"

# Explicit name for the coding-agent / AI2-THOR navigator harness.
navigator task cap="900":
    bash harness/run-next.sh "{{task}}" "{{cap}}"

# Capture and compare refactor-regression suites.
#
# mode:
#   mock           direct VLM suites with mock provider
#   local-openclaw local-only OpenClaw/Gateway suites; requires local preflight
#
# If baseline and candidate are both provided, they must be results.jsonl paths
# and only analysis runs. If both are empty, this captures a fresh baseline and
# candidate on the current checkout to smoke the harness plumbing.
regression mode="mock" baseline="" candidate="" scenes="FloorPlan201" seeds="1,2" steps="20" agents="2" model="mock":
    #!/usr/bin/env bash
    set -euo pipefail

    case "{{mode}}" in
      mock)
        suites="explore-vlm,territory-vlm,coverage-vlm"
        allow_args=()
        ;;
      local-openclaw|openclaw)
        suites="openclaw-demo,territory-openclaw,coverage-openclaw,openclaw-autonomous"
        allow_args=(--allow-local)
        ;;
      *)
        echo "error: unsupported regression mode '{{mode}}' (expected mock|local-openclaw)" >&2
        exit 1
        ;;
    esac

    if [[ -n "{{baseline}}" || -n "{{candidate}}" ]]; then
      if [[ -z "{{baseline}}" || -z "{{candidate}}" ]]; then
        echo "error: provide both baseline and candidate results.jsonl paths, or neither" >&2
        exit 1
      fi
      .venv/bin/python scripts/analyze_refactor_regression.py \
        --baseline "{{baseline}}" \
        --candidate "{{candidate}}"
      exit 0
    fi

    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    short_sha="$(git rev-parse --short HEAD)"
    baseline_label="baseline-${stamp}"
    candidate_label="candidate-${short_sha}-${stamp}"

    .venv/bin/python scripts/capture_refactor_regression.py \
      --suite "$suites" \
      --label "$baseline_label" \
      --scenes "{{scenes}}" \
      --seeds "{{seeds}}" \
      --agents "{{agents}}" \
      --steps "{{steps}}" \
      --model "{{model}}" \
      "${allow_args[@]}"

    .venv/bin/python scripts/capture_refactor_regression.py \
      --suite "$suites" \
      --label "$candidate_label" \
      --scenes "{{scenes}}" \
      --seeds "{{seeds}}" \
      --agents "{{agents}}" \
      --steps "{{steps}}" \
      --model "{{model}}" \
      "${allow_args[@]}"

    .venv/bin/python scripts/analyze_refactor_regression.py \
      --baseline "output/refactor-regression/${baseline_label}/results.jsonl" \
      --candidate "output/refactor-regression/${candidate_label}/results.jsonl"

# Real simulator regression harness with mock provider. This may download or
# launch AI2-THOR locally; use verify::mock for pure unit/mock tests.
sim scenes="FloorPlan201" seeds="1,2" steps="20" agents="2" model="mock":
    just harness::regression mock "" "" "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# Local OpenClaw/Gateway regression harness. Requires local preflight and keys.
openclaw scenes="FloorPlan201" seeds="1" steps="20" agents="2" model="mock":
    just harness::regression local-openclaw "" "" "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

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

# Show the run index table from PLAN.md plus per-run files in runs-log/.
# The PLAN.md index is the canonical "H: predicted | A: actual" view;
# runs-log/ files carry the full per-run analysis.
history:
    #!/usr/bin/env bash
    set -euo pipefail
    last_header=$(grep -nE '^\| Run ' harness/PLAN.md 2>/dev/null | head -1 | cut -d: -f1)
    if [[ -n "$last_header" ]]; then
      echo "## Run index (from harness/PLAN.md):"
      echo
      tail -n +"$last_header" harness/PLAN.md | awk '
        /^\|/ { print; next }
        { exit }
      '
    fi
    if ls harness/runs-log/*.md >/dev/null 2>&1; then
      echo
      echo "## Per-run files (harness/runs-log/):"
      ls -1 harness/runs-log/*.md | sed 's|^|  |'
    fi
