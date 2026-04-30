#!/usr/bin/env bash
# One iteration of the navigator self-improvement loop.
#
# Usage:
#   harness/run.sh <run_id> <task_file> [time_cap_seconds] [agent]
#
# What it does:
#   1. Starts a tmux session running `just code::cc` or `just code::codex`.
#   2. Delivers a kickoff message: read SKILL.md + preflight + the task body.
#   3. Polls .tmp/roboclaws-mcp/server.log for tool calls until either the
#      `roboclaws__done` tool fires OR the time cap elapses.
#   4. Captures log, trace, snapshot count, and a metrics file under
#      harness/runs/<run_id>/.
#   5. Tears down via tmux kill-session (which fires the launcher recipe's EXIT
#      trap → `just mcp::down`).
#
# Attach live with: tmux attach -t roboclaws-harness-<run_id>-<agent>

set -euo pipefail

RUN_ID="${1:?usage: run.sh <run_id> <task_file> [time_cap_seconds] [agent]}"
TASK_FILE="${2:?missing task_file}"
TIME_CAP="${3:-900}"
AGENT="${4:-claude}"

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="$REPO/harness/runs/$RUN_ID"
PROMPT_FILE="$RUN_DIR/kickoff.txt"
TASK_NAME="$(basename "$TASK_FILE" .txt)"
SESSION="roboclaws-harness-$RUN_ID-$AGENT"
MCP_LOG="$REPO/.tmp/roboclaws-mcp/server.log"

CODEX_MODEL="${CODEX_MODEL:-gpt-5.5}"
CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-medium}"
MODEL_LABEL=""
printf -v REPO_Q "%q" "$REPO"
printf -v PROMPT_FILE_Q "%q" "$PROMPT_FILE"
printf -v CODEX_MODEL_Q "%q" "$CODEX_MODEL"
printf -v CODEX_REASONING_Q "%q" "$CODEX_REASONING_EFFORT"

case "$AGENT" in
  claude)
    LAUNCH_CMD="cd $REPO_Q && just code::cc"
    MODEL_LABEL="${CLAUDE_MODEL_LABEL:-claude-default}"
    ;;
  codex)
    LAUNCH_CMD="cd $REPO_Q && CODEX_MODEL=$CODEX_MODEL_Q CODEX_REASONING_EFFORT=$CODEX_REASONING_Q CODEX_INITIAL_PROMPT_FILE=$PROMPT_FILE_Q just code::codex"
    MODEL_LABEL="$CODEX_MODEL/$CODEX_REASONING_EFFORT"
    ;;
  *)
    echo "error: unsupported agent '$AGENT' (expected 'claude' or 'codex')" >&2
    exit 1
    ;;
esac

mkdir -p "$RUN_DIR"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "error: tmux session $SESSION already exists. Kill it first: tmux kill-session -t $SESSION" >&2
  exit 1
fi

if [[ ! -f "$TASK_FILE" ]]; then
  echo "error: task_file $TASK_FILE not found" >&2
  exit 1
fi

TASK_BODY="$(cat "$TASK_FILE")"
KICKOFF=$'Read ../skills/ai2thor-navigator/SKILL.md, then call roboclaws__observe(label="preflight"). Then complete this task:\n\n'"$TASK_BODY"$'\n\nWhen finished, call roboclaws__done with a reason listing all snapshot labels you produced.\n\nExecutor scope: this robot-control session must use the roboclaws MCP tools only. Do not edit files, stage changes, or run git commands.'
printf '%s\n' "$KICKOFF" > "$PROMPT_FILE"

echo "==> harness run_id=$RUN_ID time_cap=${TIME_CAP}s"
echo "==> task: $TASK_NAME"
echo "==> agent: $AGENT"
echo "==> model: $MODEL_LABEL"
echo "==> tmux session: $SESSION"
echo "==> attach with: tmux attach -t $SESSION"
echo "==> artifacts:   $RUN_DIR"

# Pre-truncate the MCP log so our readiness check starts clean. We don't
# parse it for metrics any more — trace.jsonl in the run output dir is the
# authoritative source for tool calls, blocked moves, and done detection.
mkdir -p "$(dirname "$MCP_LOG")"
: > "$MCP_LOG"

# Start tmux. Don't pipe-pane — interactive TUIs emit unusable escape-code
# soup and we have a clean signal source (trace.jsonl).
tmux new-session -d -s "$SESSION" -x 200 -y 50 "$LAUNCH_CMD"

# Wait for the agent to be ready. The clearest signal is the MCP log printing
# "Application startup complete" + the kickoff banner being emitted.
echo "==> waiting for MCP + $AGENT to be ready..."
for _ in $(seq 1 60); do
  if grep -q "Application startup complete" "$MCP_LOG" 2>/dev/null; then
    break
  fi
  sleep 1
done

# Give the TUI another few seconds to draw before sending or monitoring.
sleep 8

if [[ "$AGENT" == "codex" ]]; then
  echo "==> kickoff prompt passed to Codex at launch"
else
  echo "==> sending kickoff message"
  # Send the kickoff message as a single string, then press Enter.
  # tmux send-keys -l literalises the string (no escape interpretation).
  tmux send-keys -t "$SESSION" -l "$KICKOFF"
  tmux send-keys -t "$SESSION" Enter
fi

START_TS=$(date +%s)
DEADLINE=$((START_TS + TIME_CAP))
LAST_REPORT=$START_TS

# Find the run output dir (trace.jsonl + snapshots) — created by the server
# at startup, named output/runs/YYYYMMDDHHMM. It may not exist yet on the
# first poll because the server is still booting; we re-resolve each tick.
resolve_runs_dir() {
  ls -td "$REPO"/output/runs/* 2>/dev/null | head -1 || true
}

# grep -c on a missing pattern exits 1 with stdout "0", so `|| echo 0` would
# double-print. Capture and ignore exit code instead, defaulting to 0 on any
# error (file missing, etc).
_grep_count() {
  local pattern="$1" path="$2" n
  [[ -f "$path" ]] || { echo 0; return; }
  n=$(grep -c "$pattern" "$path" 2>/dev/null) || n=0
  echo "${n:-0}"
}

trace_count_request_tool() {
  _grep_count "\"tool\": \"$2\", \"event\": \"request\"" "$1"
}

trace_count_request_any() {
  _grep_count '"event": "request"' "$1"
}

trace_count_blocked() {
  _grep_count '"result": "blocked"' "$1"
}

echo "==> monitoring (cap ${TIME_CAP}s)..."
while true; do
  NOW=$(date +%s)
  ELAPSED=$((NOW - START_TS))

  RUNS_DIR=$(resolve_runs_dir)
  TRACE=""
  [[ -n "$RUNS_DIR" ]] && TRACE="$RUNS_DIR/trace.jsonl"
  TOOL_CALLS=$(trace_count_request_any "$TRACE")
  DONE_CALLS=$(trace_count_request_tool "$TRACE" done)

  if (( DONE_CALLS > 0 )); then
    echo "==> agent called done at t=${ELAPSED}s, tool_calls=$TOOL_CALLS"
    OUTCOME=done
    break
  fi

  if (( NOW >= DEADLINE )); then
    echo "==> TIMEOUT at t=${ELAPSED}s, tool_calls=$TOOL_CALLS"
    OUTCOME=timeout
    break
  fi

  # Heartbeat every 30s
  if (( NOW - LAST_REPORT >= 30 )); then
    echo "    t=${ELAPSED}s tool_calls=$TOOL_CALLS"
    LAST_REPORT=$NOW
  fi

  sleep 3
done

# Final metrics — read everything from trace.jsonl which is authoritative.
RUNS_DIR=$(resolve_runs_dir)
TRACE=""
SNAPSHOT_DIR=""
if [[ -n "$RUNS_DIR" ]]; then
  TRACE="$RUNS_DIR/trace.jsonl"
  SNAPSHOT_DIR="$RUNS_DIR/snapshots/agent-0"
fi
TOOL_CALLS=$(trace_count_request_any "$TRACE")
BLOCKED=$(trace_count_blocked "$TRACE")
N_OBSERVE=$(trace_count_request_tool "$TRACE" observe)
N_OBSERVE_ARCHIVED=$(trace_count_request_tool "$TRACE" observe_archived)
N_MOVE=$(trace_count_request_tool "$TRACE" move)
N_SCENE_OBJECTS=$(trace_count_request_tool "$TRACE" scene_objects)
N_GOTO=$(trace_count_request_tool "$TRACE" goto)
N_DONE=$(trace_count_request_tool "$TRACE" done)
SNAPSHOT_COUNT=0
if [[ -n "$SNAPSHOT_DIR" && -d "$SNAPSHOT_DIR" ]]; then
  SNAPSHOT_COUNT=$(find "$SNAPSHOT_DIR" -name '*.fpv.png' | wc -l)
fi
END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))

cat > "$RUN_DIR/metrics.txt" <<EOF
run_id: $RUN_ID
task: $TASK_NAME
agent: $AGENT
model_label: $MODEL_LABEL
outcome: $OUTCOME
elapsed_seconds: $ELAPSED
tool_calls: $TOOL_CALLS
total_tool_calls: $TOOL_CALLS
  observe: $N_OBSERVE
  observe_archived: $N_OBSERVE_ARCHIVED
  move: $N_MOVE
  scene_objects: $N_SCENE_OBJECTS
  goto: $N_GOTO
  done: $N_DONE
blocked_moves: $BLOCKED
fpv_snapshots: $SNAPSHOT_COUNT
trace: $TRACE
snapshot_dir: $SNAPSHOT_DIR
EOF

# Copy server log + trace into the harness run dir for archival.
cp "$MCP_LOG" "$RUN_DIR/server.log" 2>/dev/null || true
[[ -n "$TRACE" && -f "$TRACE" ]] && cp "$TRACE" "$RUN_DIR/trace.jsonl" 2>/dev/null || true

echo "==> tearing down tmux session (will trigger mcp::down via launcher trap)"
tmux send-keys -t "$SESSION" 'q' 2>/dev/null || true
sleep 2
tmux kill-session -t "$SESSION" 2>/dev/null || true

echo "==> metrics:"
cat "$RUN_DIR/metrics.txt"
echo "==> post-run bookkeeping:"
echo "    Analyze trace + metrics, update harness/runs-log and harness/PLAN.md,"
echo "    apply at most one bounded improvement if justified, then make exactly"
echo "    one atomic git commit for run_id=$RUN_ID."
