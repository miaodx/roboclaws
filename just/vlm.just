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

run game="territory" model="kimi-coding" agents="2" steps="20" souls="" output_dir="output/kimi/{{game}}":
    #!/usr/bin/env bash
    set -euo pipefail

    souls="{{souls}}"
    case "{{game}}" in
      territory)
        if [[ -z "$souls" ]]; then
          souls=aggressive,defensive
        fi
        echo "==> Running territory game (model {{model}}, direct VLM, aggressive vs defensive) …"
        AGENT_SOULS="$souls" PYTHONUNBUFFERED=1 \
          xvfb-run -a python -u examples/territory_game.py \
          --backend vlm --model "{{model}}" --agents "{{agents}}" --steps "{{steps}}" \
          --output-dir "{{output_dir}}"
        ;;

      coverage)
        if [[ -z "$souls" ]]; then
          souls=cooperative,cooperative
        fi
        echo "==> Running coverage game (model {{model}}, direct VLM, cooperative) …"
        AGENT_SOULS="$souls" PYTHONUNBUFFERED=1 \
          xvfb-run -a python -u examples/coverage_game.py \
          --backend vlm --model "{{model}}" --agents "{{agents}}" --steps "{{steps}}" \
          --output-dir "{{output_dir}}"
        ;;

      *)
        echo "error: unsupported direct-VLM game '{{game}}' (expected territory|coverage)" >&2
        exit 1
        ;;
    esac

    echo "==> done. report: {{output_dir}}/report.html"
