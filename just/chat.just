# Interactive chat — operator drives the agent from the Gateway Control UI.
#
# `just chat::run` is the canonical entrypoint (provider/model/image-model/flags
# all controlled by arguments). Use the arguments directly or override defaults.
#
# Companion observers (run in a second terminal while chat is live):
#   `just chat::tail`  — pretty-tail Gateway session JSONL
#   `just chat::view`  — live snapshot viewer at http://127.0.0.1:8787
#
# Custom flags: `python examples/openclaw_interactive.py --help`.
#
# Chat recipes deliberately do NOT use xvfb by default — the whole point is to
# watch the robot move on the operator's actual X display. If "Unable to open
# display" trips you up, fix $DISPLAY rather than reaching for xvfb. The
# `xvfb=true` option is the explicit remote/headless exception.

set working-directory := '..'

strip_ros_env := "env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION"
chat_xvfb_python := env_var_or_default("CHAT_XVFB_PYTHON", ".venv/bin/python")
chat_xvfb_screen := env_var_or_default("CHAT_XVFB_SCREEN", "1280x1024x24")

# Default: list module recipes.
default:
    @just --list chat

run provider="mimo" model="" image_model="" observe_mode="" plugin="false" clean="false" reuse="false" xvfb="false" xvfb_args="":
    #!/usr/bin/env bash
    set -euo pipefail

    bash scripts/network_status.sh --assert-off-work "OpenClaw chat run"

    run_args=("--provider" "{{provider}}")
    if [[ -n "{{model}}" ]]; then
      run_args+=("--model" "{{model}}")
    fi
    if [[ -n "{{image_model}}" ]]; then
      run_args+=("--image-model" "{{image_model}}")
    fi
    if [[ -n "{{observe_mode}}" ]]; then
      run_args+=("--observe-mode" "{{observe_mode}}")
    fi
    if [[ "{{plugin}}" == "true" ]]; then
      run_args+=("--plugin")
    fi
    if [[ "{{clean}}" == "true" ]]; then
      run_args+=("--clean")
    fi
    if [[ "{{reuse}}" == "true" ]]; then
      run_args+=("--skip-bootstrap" "--keep-gateway")
    fi

    if [[ "{{xvfb}}" == "true" ]]; then
      xvfb_args="{{xvfb_args}}"
      xvfb-run -a -s "-screen 0 {{chat_xvfb_screen}} -nolisten tcp" \
        {{chat_xvfb_python}} examples/openclaw_interactive.py \
        "${run_args[@]}" $xvfb_args
    else
      {{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
        {{chat_xvfb_python}} examples/openclaw_interactive.py "${run_args[@]}"

    fi

# ---------------------------------------------------------------------------
# Session control + observers (kept as sidecars)
# ---------------------------------------------------------------------------

# Pretty-tail Gateway session JSONL (run in a second terminal).
[group('observer')]
tail:
    @{{strip_ros_env}} .venv/bin/python scripts/tail-openclaw-chat.py

# Live snapshot viewer at http://127.0.0.1:8787 (run in a second terminal).
[group('observer')]
view:
    -@fuser -k 8787/tcp 2>/dev/null
    @{{strip_ros_env}} .venv/bin/python scripts/view-snapshots.py
