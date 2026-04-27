# Direct-VLM recipes — bypass the OpenClaw Gateway and talk straight to the
# provider's anthropic-messages / openai-completions endpoint via the SDK.
# Per-agent SOULs are injected into the system prompt from AGENT_SOULS env +
# skills/ai2thor-navigator/souls/.
#
# Use these when the Gateway image is unavailable, or to isolate VLM behavior
# from the Gateway's image-routing layer (e.g. Kimi anthropic path drops
# images when routed through the Gateway — direct works around it).

set working-directory := '..'

# Default: list module recipes.
default:
    @just --list vlm

# Territory game (direct Kimi, aggressive vs defensive, 20 steps).
[group('kimi')]
territory:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Running territory game (direct Kimi, aggressive vs defensive) …"
    AGENT_SOULS=aggressive,defensive PYTHONUNBUFFERED=1 \
      xvfb-run -a python -u examples/territory_game.py \
      --backend vlm --model kimi-coding --agents 2 --steps 20 \
      --output-dir output/kimi/territory
    echo "==> Done. Report: output/kimi/territory/report.html"

# Coverage game (direct Kimi, cooperative, 20 steps).
[group('kimi')]
coverage:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Running coverage game (direct Kimi, cooperative) …"
    AGENT_SOULS=cooperative,cooperative PYTHONUNBUFFERED=1 \
      xvfb-run -a python -u examples/coverage_game.py \
      --backend vlm --model kimi-coding --agents 2 --steps 20 \
      --output-dir output/kimi/coverage
    echo "==> Done. Report: output/kimi/coverage/report.html"
