#!/usr/bin/env bash
# One iteration of the navigator self-improvement loop.
#
# Usage:
#   harness/run.sh <run_id> <task_file> [time_cap_seconds]
#
# What it does:
#   1. Starts a tmux session running `just code::cc` (Claude Code wired to MCP).
#   2. Sends a kickoff message: read SKILL.md + preflight + the task body.
#   3. Polls .tmp/roboclaws-mcp/server.log for tool calls until either the
#      `roboclaws__done` tool fires OR the time cap elapses.
#   4. Captures transcript, log, snapshot count, and a metrics file under
#      harness/runs/<run_id>/.
#   5. Tears down via tmux kill-session (which fires `just code::cc`'s EXIT
#      trap → `just mcp::down`).
#
# Attach live with: tmux attach -t roboclaws-harness-<run_id>

set -euo pipefail

RUN_ID="${1:?usage: run.sh <run_id> <task_file> [time_cap_seconds]}"
TASK_FILE="${2:?missing task_file}"
TIME_CAP="${3:-600}"

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="$REPO/harness/runs/$RUN_ID"
SESSION="roboclaws-harness-$RUN_ID"
MCP_LOG="$REPO/.tmp/roboclaws-mcp/server.log"

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
KICKOFF=$'Read ../skills/ai2thor-navigator/SKILL.md, then call roboclaws__observe(label="preflight"). Then complete this task:\n\n'"$TASK_BODY"$'\n\nWhen finished, call roboclaws__done with a reason listing all snapshot labels you produced.'

echo "==> harness run_id=$RUN_ID time_cap=${TIME_CAP}s"
echo "==> tmux session: $SESSION"
echo "==> attach with: tmux attach -t $SESSION"
echo "==> artifacts:   $RUN_DIR"

# Pre-truncate the MCP log so our tool-call count starts at zero.
mkdir -p "$(dirname "$MCP_LOG")"
: > "$MCP_LOG"

# Start tmux. Pipe the pane to a file so we keep the transcript even if the
# session is killed before we capture it.
TRANSCRIPT="$RUN_DIR/transcript.txt"
tmux new-session -d -s "$SESSION" -x 200 -y 50 "cd $REPO && just code::cc"
tmux pipe-pane -t "$SESSION" "cat > $TRANSCRIPT"

# Wait for `claude` to be ready. The clearest signal is the MCP log printing
# "Application startup complete" + the kickoff banner being emitted.
echo "==> waiting for MCP + claude to be ready..."
for _ in $(seq 1 60); do
  if grep -q "Application startup complete" "$MCP_LOG" 2>/dev/null; then
    break
  fi
  sleep 1
done

# Give claude another few seconds to draw its prompt before we send keys.
sleep 8

echo "==> sending kickoff message"
# Send the kickoff message as a single string, then press Enter.
# tmux send-keys -l literalises the string (no escape interpretation).
tmux send-keys -t "$SESSION" -l "$KICKOFF"
tmux send-keys -t "$SESSION" Enter

START_TS=$(date +%s)
DEADLINE=$((START_TS + TIME_CAP))
LAST_REPORT=$START_TS

echo "==> monitoring (cap ${TIME_CAP}s)..."
while true; do
  NOW=$(date +%s)
  ELAPSED=$((NOW - START_TS))

  TOOL_CALLS=$(grep -c "Processing request of type CallToolRequest" "$MCP_LOG" 2>/dev/null || echo 0)

  # Done if the agent called roboclaws__done. The MCP server prints a
  # session-end shutdown notice; simplest signal is the agent's own banner
  # "exits when the agent calls roboclaws__done" → log shows the tool body.
  # Detect via the snapshot dir touch + a "done" marker we grep for in the log.
  if grep -qE '"name":\s*"roboclaws__done"' "$MCP_LOG" 2>/dev/null \
     || grep -q "Run completed" "$MCP_LOG" 2>/dev/null; then
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

# Final metrics
TOOL_CALLS=$(grep -c "Processing request of type CallToolRequest" "$MCP_LOG" 2>/dev/null || echo 0)
BLOCKED=$(grep -c '"result": "blocked"' "$MCP_LOG" 2>/dev/null || echo 0)
RUNS_DIR=$(ls -td "$REPO"/output/runs/* 2>/dev/null | head -1 || true)
SNAPSHOT_COUNT=0
if [[ -n "$RUNS_DIR" && -d "$RUNS_DIR/snapshots/agent-0" ]]; then
  SNAPSHOT_COUNT=$(find "$RUNS_DIR/snapshots/agent-0" -name '*.fpv.png' | wc -l)
fi
END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))

cat > "$RUN_DIR/metrics.txt" <<EOF
run_id: $RUN_ID
outcome: $OUTCOME
elapsed_seconds: $ELAPSED
tool_calls: $TOOL_CALLS
blocked_moves: $BLOCKED
fpv_snapshots: $SNAPSHOT_COUNT
snapshot_dir: $RUNS_DIR
EOF

# Copy MCP log and tear down.
cp "$MCP_LOG" "$RUN_DIR/server.log" 2>/dev/null || true
echo "==> tearing down tmux session (will trigger mcp::down via cc trap)"
tmux send-keys -t "$SESSION" 'q' 2>/dev/null || true
sleep 2
tmux kill-session -t "$SESSION" 2>/dev/null || true

echo "==> metrics:"
cat "$RUN_DIR/metrics.txt"
echo "==> done. transcript: $TRANSCRIPT"
