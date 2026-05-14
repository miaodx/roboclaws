# Human-facing task grammar.
#
# Canonical form:
#   just task::run <task> <driver> [report|profile] [key=value ...]
#
# Tasks:
#   ai2thor-nav | territory | coverage | photo-chairs | molmo-cleanup |
#   molmo-planner-proof
#
# Drivers:
#   openclaw | vlm | codex | claude | script | direct | mcp-smoke
#
# Reports:
#   visual  - default for non-Molmo tasks, reviewable artifacts for humans
#   minimal - cheaper semantic evidence for non-Molmo agent iteration
#
# Molmo cleanup profiles:
#   smoke | world-labels | camera-raw | camera-labels
#   compatibility aliases: visual -> world-labels, minimal -> smoke

set working-directory := '..'
set positional-arguments

[private]
default:
    @just --list task

# Run a human-facing task through a driver.
run task driver mode="" *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    python_bin="${ROBOCLAWS_DEVTOOLS_PYTHON:-}"
    if [[ -z "$python_bin" ]]; then
      if [[ -x .venv/bin/python ]]; then
        python_bin=".venv/bin/python"
      elif command -v python3 >/dev/null 2>&1; then
        python_bin="python3"
      else
        python_bin="python"
      fi
    fi
    exec "$python_bin" -m roboclaws.devtools.commands task run "$@"

# ---------------------------------------------------------------------------
# Private compatibility wrappers for older docs/scripts.
# ---------------------------------------------------------------------------

[private]
navigate driver="openclaw" scene="FloorPlan201" agents="2" steps="10" provider="kimi" output_dir="output/openclaw/nav" host="127.0.0.1" port="18788":
    just task::run ai2thor-nav "{{driver}}" visual scene="{{scene}}" agents="{{agents}}" steps="{{steps}}" provider="{{provider}}" output_dir="{{output_dir}}" host="{{host}}" port="{{port}}"

[private]
photo-chairs driver="openclaw" provider="kimi" output_dir="output/openclaw-photo-task" max_moves="200" wall_budget="900" scene="FloorPlan201":
    just task::run photo-chairs "{{driver}}" visual provider="{{provider}}" output_dir="{{output_dir}}" max_moves="{{max_moves}}" wall_budget="{{wall_budget}}" scene="{{scene}}"

[private]
territory driver="vlm" model="kimi-k2.6" agents="2" steps="20" provider="kimi" output_dir="":
    just task::run territory "{{driver}}" visual model="{{model}}" agents="{{agents}}" steps="{{steps}}" provider="{{provider}}" output_dir="{{output_dir}}"

[private]
coverage driver="vlm" model="kimi-k2.6" agents="2" steps="20" provider="kimi" output_dir="":
    just task::run coverage "{{driver}}" visual model="{{model}}" agents="{{agents}}" steps="{{steps}}" provider="{{provider}}" output_dir="{{output_dir}}"

[private]
control-ui driver="openclaw" provider="mimo" model="" image_model="" observe_mode="" plugin="false" clean="false" reuse="false" xvfb="false" xvfb_args="":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    case "$driver" in
      openclaw)
        just chat::run "{{provider}}" "{{model}}" "{{image_model}}" "{{observe_mode}}" "{{plugin}}" "{{clean}}" "{{reuse}}" "{{xvfb}}" "{{xvfb_args}}"
        ;;
      *)
        echo "error: unsupported control-ui driver '$driver' (expected openclaw)" >&2
        exit 1
        ;;
    esac

[private]
cleanup-quick-check driver="mcp-smoke" profile="smoke" seed="7" output_dir="output/molmo/quick-check" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::quick-check "{{driver}}" "{{profile}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

[private]
cleanup-report driver="direct" seeds="1 2 3" output_dir="output/molmo/review-report" task="帮我收拾这个房间" generated_mess_count="10" profile="world-labels":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    case "$driver" in
      openclaw-smoke)
        just molmo::cleanup "openclaw-smoke" "{{profile}}" "{{seeds}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"
        ;;
      codex-live)
        just task::run molmo-cleanup codex "{{profile}}" seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}"
        ;;
      claude-live)
        just task::run molmo-cleanup claude "{{profile}}" seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}"
        ;;
      openclaw-live)
        just task::run molmo-cleanup openclaw "{{profile}}" seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}"
        ;;
      direct|mcp-smoke)
        just task::run molmo-cleanup "$driver" "{{profile}}" seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}"
        ;;
      *)
        echo "error: unsupported cleanup-report driver '$driver'" >&2
        exit 1
        ;;
    esac

[private]
cleanup-camera-raw seed="7" output_dir="output/molmo/camera-raw-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::camera-raw-report "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

[private]
planner-proof mode="dry-run":
    #!/usr/bin/env bash
    set -euo pipefail
    mode="$1"
    mode="${mode#mode=}"
    exec just task::run molmo-planner-proof direct visual mode="$mode"

[private]
check what="mock" *args:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    what="${args[0]}"
    rest=("${args[@]:1}")
    exec just agent::verify "$what" "${rest[@]}"
