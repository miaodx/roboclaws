# OpenClaw Gateway recipes — canonical dispatchers.
#
# Canonical entrypoints:
# - `run`: one-shot smoke command set (nav/territory/coverage/photo)
# - `probe`: long-running artifact command set (200-step default)
# - `gateway`: lifecycle helper for long-lived gateway reuse (`action=up|down`)

set working-directory := '..'

strip_ros_env := "env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION"

# Default: list module recipes (avoids accidentally booting a Gateway).
default:
    @just --list openclaw

# Ensure the configured OpenClaw Gateway image is present in local Docker cache.
# Useful if you want a fast first bootstrap in a tight loop.
[group('gateway')]
pull-image:
    #!/usr/bin/env bash
    set -euo pipefail

    bash scripts/dev/network_status.sh --assert-off-work "OpenClaw image pull"

    OPENCLAW_DEFAULT_IMAGE="$(awk -F= '$1=="OPENCLAW_IMAGE_DEFAULT"{print $2}' scripts/openclaw/openclaw-defaults.env | tr -d '"')"
    if [[ -z "$OPENCLAW_DEFAULT_IMAGE" ]]; then
      echo "error: missing OPENCLAW_IMAGE_DEFAULT in scripts/openclaw/openclaw-defaults.env" >&2
      exit 1
    fi

    OPENCLAW_IMG="${OPENCLAW_IMG:-${IMAGE:-${OPENCLAW_IMAGE:-$OPENCLAW_DEFAULT_IMAGE}}}"

    if ! command -v docker >/dev/null 2>&1; then
      echo "error: docker not found in PATH" >&2
      exit 1
    fi

    if ! docker image inspect "$OPENCLAW_IMG" >/dev/null 2>&1; then
      echo "==> pulling $OPENCLAW_IMG"
      docker pull "$OPENCLAW_IMG"
    else
      echo "==> already cached: $OPENCLAW_IMG"
    fi

# ---------------------------------------------------------------------------
# Canonical smoke command
# ---------------------------------------------------------------------------

# OpenClaw run dispatcher.
#
# game: nav | territory | coverage | photo
#
# Defaults preserve existing run shapes:
# - nav: 10 steps, output/openclaw/nav
# - territory/coverage: 60 steps (callers should override output-dir if needed)
# - photo: single-agent photo-task smoke
run game="nav" agents="2" steps="10" provider="kimi" output_dir="output/openclaw/{{game}}" agent_souls="" max_wall_seconds="0" personality_probe="" photo_output_dir="output/openclaw-photo-task" photo_max_moves="200" photo_wall_budget="900" photo_scene="FloorPlan201":
    #!/usr/bin/env bash
    set -euo pipefail

    bash scripts/dev/network_status.sh --assert-off-work "OpenClaw Gateway run"

    bootstrap_cmd=(env PROVIDER="{{provider}}" AGENTS="{{agents}}")
    if [[ "{{game}}" != "photo" ]]; then
      bootstrap_cmd+=(ROBOCLAWS_MCP_ENABLED=0)
    fi
    if [[ -n "{{agent_souls}}" ]]; then
      bootstrap_cmd+=(AGENT_SOULS="{{agent_souls}}")
    fi
    if [[ -n "{{personality_probe}}" ]]; then
      bootstrap_cmd+=(PERSONALITY_PROBE="{{personality_probe}}")
    fi

    TOKEN=$("${bootstrap_cmd[@]}" ./scripts/openclaw/openclaw-bootstrap.sh)
    [ -n "$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }

    wall_args=()
    if [[ "{{max_wall_seconds}}" != "0" ]]; then
      wall_args=(--max-wall-seconds "{{max_wall_seconds}}")
    fi

    case "{{game}}" in
      nav)
        echo "==> Running navigation demo …"
        OPENCLAW_GATEWAY_TOKEN="$TOKEN" xvfb-run -a .venv/bin/python examples/openclaw/openclaw_demo.py \
          --agents "{{agents}}" \
          --steps "{{steps}}" \
          --output-dir "{{output_dir}}"
        ;;

      territory)
        echo "==> Running territory game …"
        if [[ -n "{{agent_souls}}" ]]; then
          AGENT_SOULS="{{agent_souls}}" \
          {{strip_ros_env}} OPENCLAW_GATEWAY_TOKEN="$TOKEN" PYTHONUNBUFFERED=1 \
            xvfb-run -a .venv/bin/python examples/games/territory_game.py \
            --backend openclaw --agents "{{agents}}" --steps "{{steps}}" \
            "${wall_args[@]}" --output-dir "{{output_dir}}"
        else
          {{strip_ros_env}} OPENCLAW_GATEWAY_TOKEN="$TOKEN" PYTHONUNBUFFERED=1 \
            xvfb-run -a .venv/bin/python examples/games/territory_game.py \
            --backend openclaw --agents "{{agents}}" --steps "{{steps}}" \
            "${wall_args[@]}" --output-dir "{{output_dir}}"
        fi
        ;;

      coverage)
        echo "==> Running coverage game …"
        if [[ -n "{{agent_souls}}" ]]; then
          AGENT_SOULS="{{agent_souls}}" \
          {{strip_ros_env}} OPENCLAW_GATEWAY_TOKEN="$TOKEN" PYTHONUNBUFFERED=1 \
            xvfb-run -a .venv/bin/python examples/games/coverage_game.py \
            --backend openclaw --agents "{{agents}}" --steps "{{steps}}" \
            "${wall_args[@]}" --output-dir "{{output_dir}}"
        else
          {{strip_ros_env}} OPENCLAW_GATEWAY_TOKEN="$TOKEN" PYTHONUNBUFFERED=1 \
            xvfb-run -a .venv/bin/python examples/games/coverage_game.py \
            --backend openclaw --agents "{{agents}}" --steps "{{steps}}" \
            "${wall_args[@]}" --output-dir "{{output_dir}}"
        fi
        ;;

      photo)
        echo "==> Photo-task smoke (single agent, {{photo_scene}}, wall budget {{photo_wall_budget}}s)"
        {{strip_ros_env}} PROVIDER="{{provider}}" PYTHONUNBUFFERED=1 \
          xvfb-run -a .venv/bin/python examples/openclaw/openclaw_photo_task.py \
          --output-dir "{{photo_output_dir}}" \
          --max-moves "{{photo_max_moves}}" --wall-budget "{{photo_wall_budget}}"
        ;;

      *)
        echo "error: unsupported openclaw game '{{game}}' (expected nav|territory|coverage|photo)" >&2
        exit 1
        ;;
    esac

    echo "==> stopping Gateway …"
    docker rm -f openclaw-gateway || true
    if [[ "{{game}}" == "coverage" ]]; then
      docker volume rm openclaw-gateway-config || true
    fi

# Probe command set (longer artifacts): defaults: 200 steps, 1h wall budget.
probe game="territory" agents="2" steps="200" provider="kimi" output_dir="output/openclaw-probe/{{game}}" agent_souls="" max_wall_seconds="3600" personality_probe="" photo_output_dir="output/openclaw-photo-task" photo_max_moves="200" photo_wall_budget="900" photo_scene="FloorPlan201":
    #!/usr/bin/env bash
    set -euo pipefail

    case "{{game}}" in
      nav)
        just openclaw::run \
          game="nav" \
          agents="{{agents}}" steps="{{steps}}" \
          provider="{{provider}}" output_dir="{{output_dir}}" \
          agent_souls="{{agent_souls}}" max_wall_seconds="{{max_wall_seconds}}" \
          personality_probe="{{personality_probe}}" \
          photo_output_dir="{{photo_output_dir}}" \
          photo_max_moves="{{photo_max_moves}}" \
          photo_wall_budget="{{photo_wall_budget}}" \
          photo_scene="{{photo_scene}}"
        ;;

      territory)
        souls="{{agent_souls}}"
        if [[ -z "$souls" ]]; then
          souls=aggressive,defensive
        fi
        just openclaw::run \
          game="territory" \
          agents="{{agents}}" steps="{{steps}}" \
          provider="{{provider}}" output_dir="{{output_dir}}" \
          agent_souls="$souls" max_wall_seconds="{{max_wall_seconds}}" \
          personality_probe="" \
          photo_output_dir="{{photo_output_dir}}" \
          photo_max_moves="{{photo_max_moves}}" \
          photo_wall_budget="{{photo_wall_budget}}" \
          photo_scene="{{photo_scene}}"
        ;;

      coverage)
        souls="{{agent_souls}}"
        if [[ -z "$souls" ]]; then
          souls=cooperative,cooperative
        fi
        probe_personality="{{personality_probe}}"
        if [[ -z "$probe_personality" ]]; then
          probe_personality=0
        fi
        just openclaw::run \
          game="coverage" \
          agents="{{agents}}" steps="{{steps}}" \
          provider="{{provider}}" output_dir="{{output_dir}}" \
          agent_souls="$souls" max_wall_seconds="{{max_wall_seconds}}" \
          personality_probe="$probe_personality" \
          photo_output_dir="{{photo_output_dir}}" \
          photo_max_moves="{{photo_max_moves}}" \
          photo_wall_budget="{{photo_wall_budget}}" \
          photo_scene="{{photo_scene}}"
        ;;

      *)
        echo "error: unsupported probe game '{{game}}' (expected nav|territory|coverage)" >&2
        exit 1
        ;;
    esac

    echo "==> probe complete, stopping runtime …"
    docker rm -f openclaw-gateway || true
    docker volume rm openclaw-gateway-config || true


# ---------------------------------------------------------------------------
# Gateway lifecycle (use to run several runs against one long-lived gateway)
# ---------------------------------------------------------------------------

# Bootstrap a gateway and write the token to a file.
[group('gateway')]
gateway action="up" token_file=".openclaw-token" provider="kimi" agents="2":
    #!/usr/bin/env bash
    set -euo pipefail

    case "{{action}}" in
      up)
        bash scripts/dev/network_status.sh --assert-off-work "OpenClaw Gateway"
        TOKEN=$(
          env \
            PROVIDER="{{provider}}" \
            AGENTS="{{agents}}" \
            ./scripts/openclaw/openclaw-bootstrap.sh
        )
        [ -n "$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }
        printf '%s\n' "$TOKEN" > "{{token_file}}"
        echo "==> gateway-up done. Token saved to {{token_file}}"
        ;;

      down)
        docker rm -f openclaw-gateway
        docker volume rm openclaw-gateway-config
        rm -f "{{token_file}}"
        echo "==> gateway-down done"
        ;;

      *)
        echo "error: unknown openclaw gateway action '{{action}}' (expected up|down)" >&2
        exit 1
        ;;
    esac
