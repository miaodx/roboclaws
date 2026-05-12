# Human-facing task grammar.
#
# Canonical form:
#   just task::run <task> <driver> [report] [key=value ...]
#
# Tasks:
#   ai2thor-nav | territory | coverage | photo-chairs | molmo-cleanup |
#   molmo-planner-proof
#
# Drivers:
#   openclaw | vlm | codex | claude | script | direct | mcp-smoke
#
# Reports:
#   visual  - default, reviewable artifacts for humans
#   minimal - cheaper semantic evidence for agent iteration

set working-directory := '..'
set positional-arguments

[private]
default:
    @just --list task

# Run a human-facing task through a driver.
run task driver report="visual" *overrides:
    #!/usr/bin/env bash
    set -euo pipefail

    args=("$@")
    task="${args[0]}"
    driver="${args[1]}"
    report="${args[2]}"
    overrides=("${args[@]:3}")

    task="${task#task=}"
    driver="${driver#driver=}"

    case "$report" in
      report=*)
        report="${report#report=}"
        ;;
      *=*)
        overrides=("$report" "${overrides[@]}")
        report="visual"
        ;;
    esac

    normalize_task() {
      case "$1" in
        ai2thor-nav|nav|navigate|navigation|ai2thor-navigation)
          printf '%s\n' "ai2thor-nav"
          ;;
        territory|territory-game)
          printf '%s\n' "territory"
          ;;
        coverage|coverage-game)
          printf '%s\n' "coverage"
          ;;
        photo-chairs|photo|photo-task|chairs|chairs-photo)
          printf '%s\n' "photo-chairs"
          ;;
        molmo-cleanup|molmospaces-cleanup|molmospace-cleanup|cleanup|cleanup-report)
          printf '%s\n' "molmo-cleanup"
          ;;
        molmo-planner-proof|planner-proof|proof-bundle)
          printf '%s\n' "molmo-planner-proof"
          ;;
        *)
          return 1
          ;;
      esac
    }

    normalize_driver() {
      case "$1" in
        openclaw|openclaw-live)
          printf '%s\n' "openclaw"
          ;;
        vlm|direct-vlm)
          printf '%s\n' "vlm"
          ;;
        codex|codex-live)
          printf '%s\n' "codex"
          ;;
        claude|claudecode|cc|claude-live)
          printf '%s\n' "claude"
          ;;
        script|mock)
          printf '%s\n' "script"
          ;;
        direct)
          printf '%s\n' "direct"
          ;;
        mcp-smoke|mcp_smoke|mcp)
          printf '%s\n' "mcp-smoke"
          ;;
        *)
          return 1
          ;;
      esac
    }

    if ! task="$(normalize_task "$task")"; then
      echo "error: unsupported task '$task'" >&2
      echo "       expected ai2thor-nav|territory|coverage|photo-chairs|molmo-cleanup|molmo-planner-proof" >&2
      exit 1
    fi

    if ! driver="$(normalize_driver "$driver")"; then
      echo "error: unsupported driver '$driver'" >&2
      echo "       expected openclaw|vlm|codex|claude|script|direct|mcp-smoke" >&2
      exit 1
    fi

    case "$report" in
      visual|minimal)
        ;;
      *)
        echo "error: unsupported report '$report' (expected visual|minimal)" >&2
        exit 1
        ;;
    esac

    case "$task:$driver" in
      ai2thor-nav:openclaw|ai2thor-nav:codex|ai2thor-nav:claude|\
      territory:openclaw|territory:vlm|territory:script|\
      coverage:openclaw|coverage:vlm|coverage:script|\
      photo-chairs:openclaw|\
      molmo-cleanup:direct|molmo-cleanup:mcp-smoke|molmo-cleanup:codex|\
      molmo-cleanup:claude|molmo-cleanup:openclaw|\
      molmo-planner-proof:direct|molmo-planner-proof:script|molmo-planner-proof:mcp-smoke)
        ;;
      *)
        echo "error: driver '$driver' cannot run task '$task'" >&2
        exit 1
        ;;
    esac

    exec just agent::run "$task" "$driver" "$report" "${overrides[@]}"

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
territory driver="vlm" model="kimi-coding" agents="2" steps="20" provider="kimi" output_dir="":
    just task::run territory "{{driver}}" visual model="{{model}}" agents="{{agents}}" steps="{{steps}}" provider="{{provider}}" output_dir="{{output_dir}}"

[private]
coverage driver="vlm" model="kimi-coding" agents="2" steps="20" provider="kimi" output_dir="":
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
cleanup-quick-check driver="mcp-smoke" runtime="synthetic" evidence="semantic" seed="7" output_dir="output/molmo/quick-check" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::quick-check "{{driver}}" "{{runtime}}" "{{evidence}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

[private]
cleanup-report driver="direct" seeds="1 2 3" output_dir="output/molmo/review-report" task="帮我收拾这个房间" generated_mess_count="10" runtime="molmospaces" evidence="visual":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    case "$driver" in
      openclaw-smoke)
        just molmo::cleanup "openclaw-smoke" "{{runtime}}" "{{evidence}}" "{{seeds}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"
        ;;
      codex-live)
        just task::run molmo-cleanup codex visual seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}" runtime="{{runtime}}" evidence="{{evidence}}"
        ;;
      claude-live)
        just task::run molmo-cleanup claude visual seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}" runtime="{{runtime}}" evidence="{{evidence}}"
        ;;
      openclaw-live)
        just task::run molmo-cleanup openclaw visual seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}" runtime="{{runtime}}" evidence="{{evidence}}"
        ;;
      direct|mcp-smoke)
        just task::run molmo-cleanup "$driver" visual seeds="{{seeds}}" output_dir="{{output_dir}}" task="{{task}}" generated_mess_count="{{generated_mess_count}}" runtime="{{runtime}}" evidence="{{evidence}}"
        ;;
      *)
        echo "error: unsupported cleanup-report driver '$driver'" >&2
        exit 1
        ;;
    esac

[private]
cleanup-raw-fpv seed="7" output_dir="output/molmo/raw-fpv-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::raw-fpv-report "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

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
