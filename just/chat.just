# Interactive chat — operator drives the agent from the Gateway Control UI.
#
# `just chat::default` (or just `just chat`) bootstraps a fresh Gateway, holds
# AI2-THOR + the Roboclaws MCP server open, prints the Control UI URL +
# bearer token, and tears down on Ctrl-C.
#
# Image-mode taxonomy:
#   Direct vision   — main model handles images:
#     default | kimi | nvidia
#   Split-model bridge — text main + omni vision bridge:
#     mimo | mimo-pro
#   Anthropic plugin path:
#     plugin | plugin-kimi | plugin-mimo-pro
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
# `xvfb` recipe is the explicit remote/headless exception.

set working-directory := '..'

strip_ros_env := "env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION"
chat_xvfb_python := env_var_or_default("CHAT_XVFB_PYTHON", ".venv/bin/python")
chat_xvfb_screen := env_var_or_default("CHAT_XVFB_SCREEN", "1280x1024x24")

# ---------------------------------------------------------------------------
# Direct-vision providers (main model handles images)
# ---------------------------------------------------------------------------

# Default chat (MiMo V2 Omni, direct vision).
[group('direct')]
default:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py

# Kimi custom (anthropic-messages, direct vision).
[group('direct')]
kimi:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py --provider kimi

# NVIDIA NIM (nemotron-nano, direct vision).
[group('direct')]
nvidia:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py --provider nvidia

# ---------------------------------------------------------------------------
# Split-model bridge (text main + omni vision bridge)
# ---------------------------------------------------------------------------

# MiMo V2.5 Pro main + V2 Omni image bridge.
[group('bridge')]
mimo-pro:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py \
        --model mimo_openai/mimo-v2.5-pro \
        --image-model mimo_openai/mimo-v2-omni \
        --observe-mode text-bridge

# MiMo V2.5 main + V2 Omni image bridge.
[group('bridge')]
mimo:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py \
        --model mimo_openai/mimo-v2.5 \
        --image-model mimo_openai/mimo-v2-omni \
        --observe-mode text-bridge

# ---------------------------------------------------------------------------
# Anthropic plugin path
# ---------------------------------------------------------------------------

# Default model via the Anthropic plugin path.
[group('plugin')]
plugin:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py --plugin

# Kimi stock plugin (anthropic-messages).
[group('plugin')]
plugin-kimi:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py --provider kimi --plugin

# MiMo V2.5 Pro through the Anthropic path + V2 Omni image bridge.
[group('plugin')]
plugin-mimo-pro:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py \
        --model mimo_anthropic/mimo-v2.5-pro \
        --image-model mimo_openai/mimo-v2-omni \
        --observe-mode text-bridge --plugin

# ---------------------------------------------------------------------------
# Session control + observers
# ---------------------------------------------------------------------------

# Wipe Gateway session history before starting.
[group('session')]
clean:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py --clean

# Attach to an already-running Gateway (no rebuild, no teardown on exit).
[group('session')]
reuse:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      python examples/openclaw_interactive.py --skip-bootstrap --keep-gateway

# Remote/headless chat using Xvfb. Pass extra flags via $JUST_CHAT_XVFB_ARGS.
[group('session')]
xvfb:
    @{{strip_ros_env}} OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-demo}" PYTHONUNBUFFERED=1 \
      xvfb-run -a -s "-screen 0 {{chat_xvfb_screen}} -nolisten tcp" \
      {{chat_xvfb_python}} examples/openclaw_interactive.py ${JUST_CHAT_XVFB_ARGS:-}

# Pretty-tail Gateway session JSONL (run in a second terminal).
[group('observer')]
tail:
    @{{strip_ros_env}} python scripts/tail-openclaw-chat.py

# Live snapshot viewer at http://127.0.0.1:8787 (run in a second terminal).
[group('observer')]
view:
    -@fuser -k 8787/tcp 2>/dev/null
    @{{strip_ros_env}} python scripts/view-snapshots.py
