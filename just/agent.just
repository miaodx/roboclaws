# Agent-maintainer dispatchers.
#
# This namespace is intentionally compact. It exposes a small set of axes and
# delegates to private implementation modules.

set working-directory := '..'
set positional-arguments

[private]
default:
    @just --list agent

# Run a normalized task/driver/report-or-profile tuple.
run task driver mode="" *overrides:
    #!/usr/bin/env bash
    set -euo pipefail

    args=("$@")
    task="${args[0]}"
    driver="${args[1]}"
    mode="${args[2]}"
    raw_overrides=("${args[@]:3}")

    task="${task#task=}"
    driver="${driver#driver=}"
    case "$mode" in
      report=*)
        mode="${mode#report=}"
        ;;
      profile=*)
        mode="${mode#profile=}"
        ;;
      *=*)
        raw_overrides=("$mode" "${raw_overrides[@]}")
        mode=""
        ;;
    esac

    run_just() {
      if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
        printf 'just'
        for arg in "$@"; do
          printf '\t%s' "$arg"
        done
        printf '\n'
        exit 0
      fi
      exec just "$@"
    }

    run_cmd() {
      if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
        printf 'cmd'
        for arg in "$@"; do
          printf '\t%s' "$arg"
        done
        printf '\n'
        exit 0
      fi
      exec "$@"
    }

    declare -A kv=()
    for override in "${raw_overrides[@]}"; do
      [[ -z "$override" ]] && continue
      if [[ "$override" != *=* ]]; then
        echo "error: override '$override' is not key=value" >&2
        exit 1
      fi
      key="${override%%=*}"
      value="${override#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        agent_souls|agents|baseline|candidate|cap|generated_mess_count|\
        host|image_model|max_moves|max_wall_seconds|min_generated_mess_count|\
        mode|model|observe_mode|output_dir|personality_probe|photo_max_moves|\
        photo_output_dir|photo_scene|photo_wall_budget|port|prompt|provider|\
        profile|scene|scenes|seed|seeds|souls|steps|task|timeout_s|wall_budget)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      kv["$key"]="$value"
    done

    get() {
      local key="$1"
      local default="$2"
      if [[ -v "kv[$key]" && -n "${kv[$key]}" ]]; then
        printf '%s\n' "${kv[$key]}"
      else
        printf '%s\n' "$default"
      fi
    }

    cleanup_prompt() {
      local default_prompt="帮我收拾这个房间"
      if [[ -v "kv[prompt]" && -n "${kv[prompt]}" ]]; then
        printf '%s\n' "${kv[prompt]}"
      elif [[ -v "kv[task]" && -n "${kv[task]}" ]]; then
        printf '%s\n' "${kv[task]}"
      else
        printf '%s\n' "$default_prompt"
      fi
    }

    if [[ "$task" == "molmo-cleanup" ]]; then
      profile="${mode:-$(get profile world-labels)}"
      case "$profile" in
        smoke|world-labels|camera-raw|camera-labels)
          ;;
        *)
          echo "error: unsupported molmo-cleanup profile '$profile' (expected smoke|world-labels|camera-raw|camera-labels)" >&2
          exit 1
          ;;
      esac
    else
      report="${mode:-visual}"
      case "$report" in
        visual|minimal)
          ;;
        *)
          echo "error: unsupported report '$report' (expected visual|minimal)" >&2
          exit 1
          ;;
      esac
    fi

    case "$task:$driver" in
      ai2thor-nav:codex)
        scene="$(get scene FloorPlan201)"
        host="$(get host 127.0.0.1)"
        port="$(get port 18788)"
        run_just code::codex "$scene" "$host" "$port"
        ;;

      ai2thor-nav:claude)
        scene="$(get scene FloorPlan201)"
        host="$(get host 127.0.0.1)"
        port="$(get port 18788)"
        run_just code::cc "$scene" "$host" "$port"
        ;;

      ai2thor-nav:openclaw)
        agents="$(get agents 2)"
        steps="$(get steps 10)"
        provider="$(get provider kimi)"
        output_dir="$(get output_dir output/openclaw/nav)"
        run_just openclaw::run nav "$agents" "$steps" "$provider" "$output_dir"
        ;;

      territory:vlm|coverage:vlm)
        model="$(get model kimi-k2.6)"
        agents="$(get agents 2)"
        steps="$(get steps 20)"
        souls="$(get souls "")"
        output_dir="$(get output_dir "output/kimi/$task")"
        run_just vlm::run "$task" "$model" "$agents" "$steps" "$souls" "$output_dir"
        ;;

      territory:openclaw|coverage:openclaw)
        agents="$(get agents 2)"
        steps="$(get steps 20)"
        provider="$(get provider kimi)"
        output_dir="$(get output_dir "output/openclaw/$task")"
        souls="$(get souls "$(get agent_souls "")")"
        run_just openclaw::run "$task" "$agents" "$steps" "$provider" "$output_dir" "$souls"
        ;;

      territory:script)
        agents="$(get agents 2)"
        steps="$(get steps 20)"
        output_dir="$(get output_dir output/script/territory)"
        run_cmd xvfb-run -a .venv/bin/python -u examples/games/territory_game.py \
          --backend vlm --model mock --agents "$agents" --steps "$steps" \
          --output-dir "$output_dir"
        ;;

      coverage:script)
        agents="$(get agents 2)"
        steps="$(get steps 20)"
        output_dir="$(get output_dir output/script/coverage)"
        run_cmd xvfb-run -a .venv/bin/python -u examples/games/coverage_game.py \
          --backend vlm --model mock --agents "$agents" --steps "$steps" \
          --output-dir "$output_dir"
        ;;

      photo-chairs:openclaw)
        provider="$(get provider kimi)"
        output_dir="$(get output_dir output/openclaw-photo-task)"
        max_moves="$(get max_moves "$(get photo_max_moves 200)")"
        wall_budget="$(get wall_budget "$(get photo_wall_budget 900)")"
        scene="$(get scene "$(get photo_scene FloorPlan201)")"
        run_just openclaw::run photo 1 10 "$provider" output/openclaw/photo "" 0 "" \
          "$output_dir" "$max_moves" "$wall_budget" "$scene"
        ;;

      molmo-cleanup:direct|molmo-cleanup:mcp-smoke|molmo-cleanup:codex|\
      molmo-cleanup:claude|molmo-cleanup:openclaw)
        case "$driver" in
          direct|mcp-smoke)
            impl_driver="$driver"
            ;;
          codex)
            impl_driver="codex-live"
            ;;
          claude)
            impl_driver="claude-live"
            ;;
          openclaw)
            impl_driver="openclaw-live"
            ;;
        esac

        case "$profile" in
          world-labels)
            default_output_dir="output/molmo/${driver}-report"
            ;;
          smoke)
            default_output_dir="output/molmo/${driver}-smoke"
            ;;
          *)
            default_output_dir="output/molmo/${driver}-${profile}"
            ;;
        esac
        if [[ "$driver" == "direct" && "$profile" == "world-labels" ]]; then
          default_seeds="1 2 3"
        else
          default_seeds="7"
        fi
        seeds="$(get seeds "$(get seed "$default_seeds")")"
        output_dir="$(get output_dir "$default_output_dir")"
        prompt="$(cleanup_prompt)"
        generated_mess_count="$(get generated_mess_count 10)"
        host="$(get host 127.0.0.1)"
        port="$(get port 18788)"
        run_just molmo::cleanup "$impl_driver" "$profile" "$seeds" \
          "$output_dir" "$prompt" "$generated_mess_count" "$host" "$port"
        ;;

      molmo-planner-proof:direct|molmo-planner-proof:script|molmo-planner-proof:mcp-smoke)
        mode="$(get mode dry-run)"
        mode="${mode//_/-}"
        output_dir="$(get output_dir "")"
        seed="$(get seed 7)"
        prompt="$(cleanup_prompt)"
        generated_mess_count="$(get generated_mess_count 10)"
        case "$mode" in
          dry-run|dry)
            if [[ -n "$output_dir" ]]; then
              run_just harness::molmo-planner-proof-bundle-runner \
                "$output_dir" "$seed" "$prompt" "$generated_mess_count"
            fi
            run_just harness::molmo-planner-proof-bundle-runner
            ;;
          execute-rerun|execute|local)
            min_generated_mess_count="$(get min_generated_mess_count 5)"
            steps="$(get steps 2)"
            timeout_s="$(get timeout_s 600)"
            if [[ -z "$output_dir" ]]; then
              output_dir="output/molmo-planner-proof-bundle-execute-rerun"
            fi
            run_just harness::molmo-planner-proof-bundle-execute-rerun \
              "$output_dir" "$seed" "$prompt" "$generated_mess_count" \
              "$min_generated_mess_count" "$steps" "$timeout_s"
            ;;
          *)
            echo "error: unsupported molmo-planner-proof mode '$mode' (expected dry-run|execute-rerun)" >&2
            exit 1
            ;;
        esac
        ;;

      *)
        echo "error: unsupported task/driver route '$task:$driver'" >&2
        exit 1
        ;;
    esac

# Dispatch to a private verification gate.
verify target="mock" *args:
    #!/usr/bin/env bash
    set -euo pipefail

    args=("$@")
    target="${args[0]}"
    target="${target#target=}"
    rest=("${args[@]:1}")

    trace_or_exec() {
      if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
        printf 'just'
        for arg in "$@"; do printf '\t%s' "$arg"; done
        printf '\n'
        exit 0
      fi
      exec just "$@"
    }

    case "$target" in
      static|mock|contract|regression-mock|local-sim|local-openclaw|navigator|\
      molmo-cleanup|molmo-prompt-cleanup|molmo-real-cleanup|molmo-robot-visual|\
      molmo-agent-bridge|molmo-agent-bridge-visual|molmo-realworld-cleanup|\
      molmo-realworld-agent-mcp|molmo-realworld-agent-dogfood-kit|\
      molmo-realworld-openclaw-dogfood-kit|\
      molmo-realworld-openclaw-visual-dogfood-kit|molmo-realworld-raw-fpv|\
      molmo-planner-proof-bundle-runner|molmo-planner-proof-bundle-execute-rerun|\
      molmo-planner-manipulation-probe|full-local)
        trace_or_exec verify::"$target" "${rest[@]}"
        ;;
      *)
        echo "error: unsupported verify target '$target'" >&2
        exit 1
        ;;
    esac

# Dispatch to a private harness recipe.
harness target *args:
    #!/usr/bin/env bash
    set -euo pipefail

    args=("$@")
    target="${args[0]}"
    target="${target#target=}"
    rest=("${args[@]:1}")

    trace_or_exec() {
      if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
        printf 'just'
        for arg in "$@"; do printf '\t%s' "$arg"; done
        printf '\n'
        exit 0
      fi
      exec just "$@"
    }

    case "$target" in
      run|navigator|regression|sim|openclaw|molmo-cleanup|molmo-prompt-cleanup|\
      molmo-real-cleanup|molmo-robot-visual|molmo-agent-bridge|\
      molmo-agent-bridge-visual|molmo-realworld-cleanup|\
      molmo-realworld-agent-mcp|molmo-realworld-agent-dogfood-kit|\
      molmo-realworld-openclaw-dogfood-kit|\
      molmo-realworld-openclaw-visual-dogfood-kit|molmo-realworld-raw-fpv|\
      molmo-planner-proof-bundle-runner|molmo-planner-proof-bundle-execute-rerun|\
      molmo-planner-manipulation-probe|list-tasks|history)
        trace_or_exec harness::"$target" "${rest[@]}"
        ;;
      *)
        echo "error: unsupported harness target '$target'" >&2
        exit 1
        ;;
    esac

# Manage the direct navigation MCP server.
mcp action="up" scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    action="$1"
    action="${action#action=}"

    trace_or_exec() {
      if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
        printf 'just'
        for arg in "$@"; do printf '\t%s' "$arg"; done
        printf '\n'
        exit 0
      fi
      exec just "$@"
    }

    case "$action" in
      up)
        trace_or_exec mcp::up "$2" "$3" "$4"
        ;;
      down)
        trace_or_exec mcp::down
        ;;
      *)
        echo "error: unsupported mcp action '$action' (expected up|down)" >&2
        exit 1
        ;;
    esac

# Manage the OpenClaw Gateway lifecycle.
gateway action="up" token_file=".openclaw-token" provider="kimi" agents="2":
    #!/usr/bin/env bash
    set -euo pipefail

    action="$1"
    action="${action#action=}"

    trace_or_exec() {
      if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
        printf 'just'
        for arg in "$@"; do printf '\t%s' "$arg"; done
        printf '\n'
        exit 0
      fi
      exec just "$@"
    }

    case "$action" in
      up|down)
        trace_or_exec openclaw::gateway "$action" "$2" "$3" "$4"
        ;;
      pull-image|pull)
        trace_or_exec openclaw::pull-image
        ;;
      *)
        echo "error: unsupported gateway action '$action' (expected up|down|pull-image)" >&2
        exit 1
        ;;
    esac
