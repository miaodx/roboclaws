# Railway-style appliance — one container with Gateway + Xvfb + Roboclaws MCP
# + three-view viewer + nginx. Mirrors the hosted Railway shape; doesn't
# replace the faster local `just chat` workflow.

set working-directory := '..'

strip_ros_env := "env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION"
container := env_var_or_default("APPLIANCE_CONTAINER", "roboclaws-appliance")
local_data_volume := env_var_or_default("APPLIANCE_LOCAL_DATA_VOLUME", "roboclaws-appliance-data")
railway_data_dir := env_var_or_default("APPLIANCE_RAILWAY_DATA_DIR", "/data")
smoke_url := env_var_or_default("APPLIANCE_SMOKE_URL", "http://127.0.0.1:8080")

# Default: list module recipes (avoids accidentally building the image).
default:
    @just --list appliance

# Build the Railway image.
build:
    docker build -f Dockerfile.railway -t roboclaws-appliance .

# Run locally, reusing host ~/.ai2thor (no Railway /data mount).
run-local:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "$HOME/.ai2thor"
    ENV_FILE_ARG=""
    [ -f .env ] && ENV_FILE_ARG="--env-file .env"
    docker rm -f "{{container}}" >/dev/null 2>&1 || true
    docker run --rm $ENV_FILE_ARG \
      --name "{{container}}" \
      -e PORT=8080 \
      -e HOME=/data \
      -e ROBOCLAWS_HOME=/data \
      -e DEMO_PASSWORD="${DEMO_PASSWORD:-demo}" \
      -e PROVIDER -e MODEL -e IMAGE_MODEL \
      -e KIMI_PROVIDER_MODE -e MIMO_PROVIDER_MODE \
      -p 8080:8080 \
      -v "{{local_data_volume}}:/data" \
      -v "$HOME/.ai2thor:/data/.ai2thor" \
      roboclaws-appliance

# Run locally with host /data mounted as Railway parity.
run-railway:
    #!/usr/bin/env bash
    set -euo pipefail
    DATA_DIR="{{railway_data_dir}}"
    mkdir -p "$DATA_DIR/.ai2thor" "$DATA_DIR/runs"
    ENV_FILE_ARG=""
    [ -f .env ] && ENV_FILE_ARG="--env-file .env"
    docker rm -f "{{container}}" >/dev/null 2>&1 || true
    docker run --rm $ENV_FILE_ARG \
      --name "{{container}}" \
      -e PORT=8080 \
      -e HOME=/data \
      -e ROBOCLAWS_HOME=/data \
      -e DEMO_PASSWORD="${DEMO_PASSWORD:-demo}" \
      -e PROVIDER -e MODEL -e IMAGE_MODEL \
      -e KIMI_PROVIDER_MODE -e MIMO_PROVIDER_MODE \
      -p 8080:8080 \
      -v "$DATA_DIR:/data" \
      roboclaws-appliance

# Verify Control UI proxy + Gateway token websocket against a running appliance.
smoke:
    @{{strip_ros_env}} .venv/bin/python scripts/appliance_control_ui_smoke.py \
      --url "{{smoke_url}}" \
      --token "${OPENCLAW_TOKEN:-${DEMO_PASSWORD:-demo}}"

# Pretty-tail the appliance Gateway session JSONL.
tail:
    @{{strip_ros_env}} python scripts/tail-openclaw-chat.py --container "{{container}}"
