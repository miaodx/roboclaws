#!/usr/bin/env bash
# Auto-numbering wrapper around harness/run.sh.
#
# Reads the highest existing run_id under harness/runs/ + the highest
# `## Run NNN` header in harness/PLAN.md, picks the next, then forwards to
# run.sh.
#
# Usage:
#   harness/run-next.sh <task_basename> [time_cap_seconds]
#
# `task_basename` is REQUIRED (no default). The harness loop is for curated
# experiments — silently re-running yesterday's task by accident hides
# regressions. Pass an explicit task each time. List available tasks with:
#   just harness::list-tasks
#
# Examples:
#   harness/run-next.sh photo-living-room
#   harness/run-next.sh photo-living-room 600

set -euo pipefail

TASK="${1:-}"
TIME_CAP="${2:-900}"

if [[ -z "$TASK" ]]; then
  echo "error: task is required. Usage: $0 <task_basename> [cap_seconds]" >&2
  echo "       Available tasks:" >&2
  ls harness/tasks/*.txt 2>/dev/null | sed 's|harness/tasks/|         - |;s|\.txt$||' >&2
  exit 1
fi

TASK_FILE="harness/tasks/${TASK}.txt"
if [[ ! -f "$TASK_FILE" ]]; then
  echo "error: task file not found: $TASK_FILE" >&2
  echo "       Available tasks:" >&2
  ls harness/tasks/*.txt 2>/dev/null | sed 's|harness/tasks/|         - |;s|\.txt$||' >&2
  exit 1
fi

# Find the next run_id by taking max(harness/runs/<NNN>/, harness/runs-log/<NNNN>-<slug>.md) + 1.
# Two sources because they capture different things:
#   - harness/runs/   per-run raw artifacts (gitignored, cleaned periodically)
#   - harness/runs-log/  curated per-run markdown (committed)
# Either may be missing for a given run_id (artifacts pruned, or curated log
# not written yet); take the max so we don't collide with either.
last_from_runs=$(ls -1 harness/runs 2>/dev/null | grep -E '^[0-9]+$' | sort -n | tail -1 || echo 0)
last_from_log=$(ls -1 harness/runs-log 2>/dev/null \
  | sed -nE 's|^([0-9]+)-.*\.md$|\1|p' | sort -n | tail -1 || echo 0)
last_from_runs="${last_from_runs:-0}"
last_from_log="${last_from_log:-0}"
last_runs_dec=$((10#$last_from_runs))
last_log_dec=$((10#$last_from_log))
last=$(( last_runs_dec > last_log_dec ? last_runs_dec : last_log_dec ))
next=$(printf "%03d" $((last + 1)))

echo "==> next run_id: $next  (last: $last)"
exec bash harness/run.sh "$next" "$TASK_FILE" "$TIME_CAP"
