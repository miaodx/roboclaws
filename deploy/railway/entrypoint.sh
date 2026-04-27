#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/roboclaws}"
DATA_DIR="${DATA_DIR:-/data}"
ROBOCLAWS_HOME="${ROBOCLAWS_HOME:-${DATA_DIR}}"
PORT="${PORT:-8080}"
APPLIANCE_ENV_FILE="${APPLIANCE_ENV_FILE:-${DATA_DIR}/appliance/runtime.env}"

if [[ -z "${DEMO_PASSWORD:-}" && -z "${OPENCLAW_TOKEN:-}" ]]; then
  echo "ERROR: set DEMO_PASSWORD or OPENCLAW_TOKEN" >&2
  exit 1
fi

export APP_ROOT DATA_DIR ROBOCLAWS_HOME PORT APPLIANCE_ENV_FILE
export HOME="$ROBOCLAWS_HOME"
export ROBOCLAWS_AI2THOR_DIR="${ROBOCLAWS_AI2THOR_DIR:-${HOME}/.ai2thor}"
export OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-${DEMO_PASSWORD}}"
export DEMO_PASSWORD="${DEMO_PASSWORD:-${OPENCLAW_TOKEN}}"
export PROVIDER="${PROVIDER:-mimo}"
export ROBOCLAWS_RUN_DIR="${ROBOCLAWS_RUN_DIR:-${DATA_DIR}/runs/current}"
export ROBOCLAWS_SNAPSHOTS_DIR="${ROBOCLAWS_SNAPSHOTS_DIR:-${ROBOCLAWS_RUN_DIR}/snapshots}"
export ROBOCLAWS_MCP_URL="${ROBOCLAWS_MCP_URL:-http://127.0.0.1:18788/mcp}"
export ROBOCLAWS_TOOL_PROFILE="${ROBOCLAWS_TOOL_PROFILE:-minimal}"
export DISPLAY="${DISPLAY:-:99}"

if [[ -z "${ROBOCLAWS_PUBLIC_URL:-}" ]]; then
  if [[ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]]; then
    export ROBOCLAWS_PUBLIC_URL="https://${RAILWAY_PUBLIC_DOMAIN}"
  else
    export ROBOCLAWS_PUBLIC_URL="http://127.0.0.1:${PORT}"
  fi
fi
export ROBOCLAWS_VIEWER_HINT="${ROBOCLAWS_VIEWER_HINT:-${ROBOCLAWS_PUBLIC_URL%/}/views/}"
if [[ -z "${ROBOCLAWS_TAIL_HINT:-}" ]]; then
  if [[ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]]; then
    export ROBOCLAWS_TAIL_HINT="Railway deployment logs"
  else
    export ROBOCLAWS_TAIL_HINT="just appliance::tail"
  fi
fi

mkdir -p "$DATA_DIR" "$ROBOCLAWS_HOME" "$ROBOCLAWS_AI2THOR_DIR" \
  "$ROBOCLAWS_RUN_DIR" "$ROBOCLAWS_SNAPSHOTS_DIR" \
  "$DATA_DIR/appliance" /run/nginx /var/log/nginx

cd "$APP_ROOT"
"$APP_ROOT/.venv/bin/python" scripts/appliance_seed_openclaw.py
# shellcheck disable=SC1090
. "$APPLIANCE_ENV_FILE"

sed "s/__PORT__/${PORT}/g" \
  "$APP_ROOT/deploy/railway/nginx.conf.template" \
  > /etc/nginx/conf.d/default.conf
rm -f /etc/nginx/sites-enabled/default

exec /usr/bin/supervisord -c "$APP_ROOT/deploy/railway/supervisord.conf"
