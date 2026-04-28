# Railway-style appliance — one container with Gateway + Xvfb + Roboclaws MCP
# + three-view viewer + nginx. Mirrors the hosted Railway shape; doesn't
# replace the faster local `just chat::run` workflow.

set working-directory := '..'

strip_ros_env := "env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION"
default_container := env_var_or_default("APPLIANCE_CONTAINER", "roboclaws-appliance")
default_local_data_volume := env_var_or_default("APPLIANCE_LOCAL_DATA_VOLUME", "roboclaws-appliance-data")
default_railway_data_dir := env_var_or_default("APPLIANCE_RAILWAY_DATA_DIR", "/data")
smoke_url := env_var_or_default("APPLIANCE_SMOKE_URL", "http://127.0.0.1:8080")

# Default: list module recipes (avoids accidentally building the image).
default:
    @just --list appliance

# Build the Railway image.
[group('build')]
build:
    docker build -f Dockerfile.railway -t roboclaws-appliance .

# Canonical appliance entrypoint.
run mode="local" container="" local_data_volume="" railway_data_dir="":
    #!/usr/bin/env bash
    set -euo pipefail

    container="{{default_container}}"
    local_data_volume="{{default_local_data_volume}}"
    railway_data_dir="{{default_railway_data_dir}}"
    if [[ -n "{{container}}" ]]; then
      container="{{container}}"
    fi
    if [[ -n "{{local_data_volume}}" ]]; then
      local_data_volume="{{local_data_volume}}"
    fi
    if [[ -n "{{railway_data_dir}}" ]]; then
      railway_data_dir="{{railway_data_dir}}"
    fi

    volume_args=()
    case "{{mode}}" in
      local)
        mkdir -p "$HOME/.ai2thor"
        volume_args=(-v "$local_data_volume:/data" -v "$HOME/.ai2thor:/data/.ai2thor")
        ;;
      railway)
        DATA_DIR="$railway_data_dir"
        mkdir -p "$DATA_DIR/.ai2thor" "$DATA_DIR/runs"
        volume_args=(-v "$DATA_DIR:/data")
        ;;
      *)
        echo "error: unknown appliance mode '{{mode}}' (expected local|railway)" >&2
        exit 1
        ;;
    esac

    ENV_FILE_ARG=""
    [ -f .env ] && ENV_FILE_ARG="--env-file .env"
    docker rm -f "$container" >/dev/null 2>&1 || true
    # --network host: container shares host's network namespace.
    # Why not bridge: host runs Tailscale (MTU 1280) but docker0 default is
    # 1500 — TLS handshakes to upstream LLM providers (e.g. mimo) silently
    # PMTU-blackhole on bridge. Host network puts the container on the same
    # stack the host already uses successfully. See docs/troubleshooting/
    # docker-tailscale-mtu.md. Side-effect bonus: every internal port
    # (8080, 18789 gateway, 18788 MCP, 18787 snapshot viewer) is reachable
    # at 127.0.0.1:<port> from the host without -p forwarding.
    docker run --rm --network host $ENV_FILE_ARG \
      --name "$container" \
      -e PORT=8080 \
      -e HOME=/data \
      -e ROBOCLAWS_HOME=/data \
      -e DEMO_PASSWORD="${DEMO_PASSWORD:-demo}" \
      -e PROVIDER -e MODEL -e IMAGE_MODEL \
      -e KIMI_PROVIDER_MODE -e MIMO_PROVIDER_MODE \
      --add-host openrouter.ai:0.0.0.0 \
      --add-host raw.githubusercontent.com:0.0.0.0 \
      "${volume_args[@]}" \
      roboclaws-appliance

# Verify Control UI proxy + Gateway token websocket against a running appliance.
[group('check')]
smoke:
    @{{strip_ros_env}} .venv/bin/python scripts/appliance_control_ui_smoke.py \
      --url "{{smoke_url}}" \
      --token "${OPENCLAW_TOKEN:-${DEMO_PASSWORD:-demo}}"

# Pretty-tail the appliance Gateway session JSONL.
[group('observer')]
tail:
    @{{strip_ros_env}} .venv/bin/python scripts/tail-openclaw-chat.py --container "{{default_container}}"
