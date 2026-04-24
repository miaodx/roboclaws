#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/roboclaws}"
RUN_DIR="${ROBOCLAWS_RUN_DIR:-/data/runs/current}"
AGENT_ID="${ROBOCLAWS_AGENT_ID:-0}"

cd "$APP_ROOT"

args=(
  examples/openclaw_interactive.py
  --skip-bootstrap
  --keep-gateway
  --output-dir "$RUN_DIR"
  --agent-id "$AGENT_ID"
)

if [[ -n "${PROVIDER:-}" ]]; then
  args+=(--provider "$PROVIDER")
fi
if [[ -n "${MODEL:-}" ]]; then
  args+=(--model "$MODEL")
fi
if [[ -n "${IMAGE_MODEL:-}" ]]; then
  args+=(--image-model "$IMAGE_MODEL")
fi
if [[ -n "${ROBOCLAWS_OBSERVE_MODE:-}" ]]; then
  args+=(--observe-mode "$ROBOCLAWS_OBSERVE_MODE")
fi

exec "$APP_ROOT/.venv/bin/python" "${args[@]}"
