#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/roboclaws}"
RUN_DIR="${ROBOCLAWS_RUN_DIR:-/data/runs/current}"
AGENT_ID="${ROBOCLAWS_AGENT_ID:-0}"
PORT="${PORT:-8080}"

if [[ -z "${ROBOCLAWS_PUBLIC_URL:-}" ]]; then
  if [[ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]]; then
    export ROBOCLAWS_PUBLIC_URL="https://${RAILWAY_PUBLIC_DOMAIN}"
  else
    export ROBOCLAWS_PUBLIC_URL="http://127.0.0.1:${PORT}"
  fi
fi
export ROBOCLAWS_VIEWER_HINT="${ROBOCLAWS_VIEWER_HINT:-${ROBOCLAWS_PUBLIC_URL%/}/views/}"
export ROBOCLAWS_TAIL_HINT="${ROBOCLAWS_TAIL_HINT:-just appliance::tail}"
export OPENCLAW_GATEWAY_CONTAINER="${OPENCLAW_GATEWAY_CONTAINER:-roboclaws-appliance}"

cd "$APP_ROOT"

args=(
  examples/openclaw/openclaw_interactive.py
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
