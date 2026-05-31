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
        agent_souls|agents|agibot_map_artifact_dir|backend|baseline|candidate|cap|context_json|\
        generated_mess_count|\
        cleanup_routine|record_robot_views|robot_views|\
        host|image_model|max_moves|max_wall_seconds|min_generated_mess_count|\
        map_bundle|map_mode|mode|model|observe_mode|output_dir|personality_probe|photo_max_moves|\
        photo_output_dir|photo_scene|photo_wall_budget|policy|port|prompt|provider|\
        profile|real_movement_enabled|run_dir|runner_python|runner_script|runtime_map_prior|\
        scene|scenes|seed|seeds|semantic_sweep|souls|steps|task|timeout_s|\
        visual_grounding|visual_grounding_timeout|visual_grounding_timeout_s|wall_budget|waypoint_id)
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

    semantic_map_prompt() {
      local default_prompt="帮我建立这个房间的语义地图"
      if [[ -v "kv[prompt]" && -n "${kv[prompt]}" ]]; then
        printf '%s\n' "${kv[prompt]}"
      elif [[ -v "kv[task]" && -n "${kv[task]}" ]]; then
        printf '%s\n' "${kv[task]}"
      else
        printf '%s\n' "$default_prompt"
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

    shell_join() {
      local first=1
      local quoted
      for arg in "$@"; do
        printf -v quoted '%q' "$arg"
        if [[ "$first" == "1" ]]; then
          printf '%s' "$quoted"
          first=0
        else
          printf ' %s' "$quoted"
        fi
      done
    }

    if [[ "$task" == "molmo-cleanup" ]]; then
      task="household-cleanup"
    fi

    if [[ "$task" == "household-cleanup" || "$task" == "semantic-map-build" ]]; then
      profile="${mode:-$(get profile world-labels)}"
      case "$profile" in
        smoke|world-labels|camera-raw|camera-labels)
          ;;
        *)
          echo "error: unsupported household cleanup lane '$profile' (expected smoke|world-labels|camera-raw|camera-labels)" >&2
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

    report_rerun_parts=("just" "task::run" "$task" "$driver")
    if [[ "$task" == "household-cleanup" || "$task" == "semantic-map-build" ]]; then
      report_rerun_parts+=("$profile")
    else
      report_rerun_parts+=("$report")
    fi
    for override in "${raw_overrides[@]}"; do
      [[ -n "$override" ]] && report_rerun_parts+=("$override")
    done
    export ROBOCLAWS_REPORT_RERUN_COMMAND="$(shell_join "${report_rerun_parts[@]}")"

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

      photo-chairs:codex|photo-chairs:claude)
        scene="$(get scene "$(get photo_scene FloorPlan201)")"
        host="$(get host 127.0.0.1)"
        port="$(get port 18788)"
        case "$driver" in
          codex)
            run_just code::codex "$scene" "$host" "$port" photo-chairs capture-object-photo 1
            ;;
          claude)
            run_just code::cc "$scene" "$host" "$port" photo-chairs capture-object-photo 1
            ;;
        esac
        ;;

      semantic-map-build:direct|semantic-map-build:codex|household-cleanup:direct|household-cleanup:mcp-smoke|\
      household-cleanup:codex|household-cleanup:claude|household-cleanup:openclaw)
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
        if [[ "$task" == "semantic-map-build" && "$driver" != "direct" && "$driver" != "codex" ]]; then
          echo "error: semantic-map-build currently supports direct or codex driver only" >&2
          exit 1
        fi

        case "$profile" in
          world-labels)
            default_output_dir="output/household/${task}/${driver}-report"
            ;;
          smoke)
            default_output_dir="output/household/${task}/${driver}-smoke"
            ;;
          *)
            default_output_dir="output/household/${task}/${driver}-${profile}"
            ;;
        esac
        if [[ "$task" == "household-cleanup" && "$driver" == "direct" && "$profile" == "world-labels" ]]; then
          default_seeds="1 2 3"
        else
          default_seeds="7"
        fi
        seeds="$(get seeds "$(get seed "$default_seeds")")"
        output_dir="$(get output_dir "$default_output_dir")"
        if [[ "$task" == "semantic-map-build" ]]; then
          prompt="$(semantic_map_prompt)"
        else
          prompt="$(cleanup_prompt)"
        fi
        generated_mess_count="$(get generated_mess_count 10)"
        host="$(get host 127.0.0.1)"
        port="$(get port 18788)"
        map_bundle="$(get map_bundle auto)"
        cleanup_routine="$(get cleanup_routine skill)"
        case "$cleanup_routine" in
          auto|skill)
            ;;
          *)
            echo "error: unsupported cleanup_routine '$cleanup_routine' (expected auto|skill)" >&2
            exit 1
            ;;
        esac
        robot_views="$(get robot_views "$(get record_robot_views auto)")"
        visual_grounding="$(get visual_grounding sim)"
        visual_grounding_timeout_s="$(get visual_grounding_timeout_s "$(get visual_grounding_timeout auto)")"
        semantic_sweep="$(get semantic_sweep off)"
        if [[ "$task" == "semantic-map-build" ]]; then
          semantic_sweep="on"
        fi
        map_mode="$(get map_mode rich)"
        runtime_map_prior="$(get runtime_map_prior "")"
        backend="$(get backend auto)"
        if [[ "$task" == "semantic-map-build" && "$driver" == "codex" && "$backend" != "agibot_gdk" ]]; then
          echo "error: semantic-map-build codex currently requires backend=agibot_gdk" >&2
          exit 1
        fi
        if [[ "$backend" == "agibot_gdk" ]]; then
          context_json="$(get context_json "")"
          if [[ -z "$context_json" ]]; then
            echo "error: backend=agibot_gdk requires context_json=<agibot map context JSON>" >&2
            exit 1
          fi
          if [[ "$task" == "semantic-map-build" && "$driver" == "codex" ]]; then
            seed_count="$(wc -w <<<"$seeds" | tr -d ' ')"
            if [[ "$seed_count" != "1" ]]; then
              echo "error: Agibot semantic-map-build Codex accepts exactly one seed per live run" >&2
              exit 1
            fi
            seed="$seeds"
            stamp="$(TZ=Asia/Shanghai date +%m%d_%H%M)"
            run_dir="$(get run_dir "")"
            if [[ -z "$run_dir" ]]; then
              run_dir="${output_dir}/${stamp}/seed-${seed}"
            fi
            policy="$(get policy codex_agent)"
            server_startup_timeout_s="${ROBOCLAWS_AGIBOT_MAP_BUILD_LIVE_SERVER_STARTUP_TIMEOUT_S:-600}"
            client_url="http://${host}:${port}/mcp"

            server_host="$host"
            server_args=(
              --host "$server_host"
              --port "$port"
              --output-dir "$run_dir"
              --context-json "$context_json"
              --policy "$policy"
              --task "$prompt"
              --evidence-lane "$profile"
              --visual-grounding "$visual_grounding"
            )
            if [[ "$visual_grounding_timeout_s" != "auto" && -n "$visual_grounding_timeout_s" ]]; then
              server_args+=(--visual-grounding-timeout-s "$visual_grounding_timeout_s")
            fi
            runner_python="$(get runner_python "")"
            if [[ -n "$runner_python" ]]; then
              server_args+=(--runner-python "$runner_python")
            fi
            runner_script="$(get runner_script "")"
            if [[ -n "$runner_script" ]]; then
              server_args+=(--runner-script "$runner_script")
            fi
            agibot_map_artifact_dir="$(get agibot_map_artifact_dir "")"
            if [[ -n "$agibot_map_artifact_dir" ]]; then
              server_args+=(--agibot-map-artifact-dir "$agibot_map_artifact_dir")
            fi
            real_movement_enabled="$(get real_movement_enabled false)"
            case "$real_movement_enabled" in
              true|1|yes|on)
                server_args+=(--real-movement-enabled)
                ;;
              false|0|no|off|"")
                ;;
              *)
                echo "error: unsupported real_movement_enabled '$real_movement_enabled' (expected true|false)" >&2
                exit 1
                ;;
            esac

            if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
              runner_args=(
                .venv/bin/python
                scripts/molmo_cleanup/run_live_codex_agibot_map_build.py
                --repo-root "$PWD"
                --run-dir "$run_dir"
                --status-path "${run_dir}/live_status.json"
                --client-url "$client_url"
                --host "$host"
                --port "$port"
                --codex-bin ".tmp/coding-agent-bin/codex"
                --codex-model ""
                --codex-provider-summary "system defaults"
                --server-startup-timeout-s "$server_startup_timeout_s"
                --kickoff-prompt "$prompt"
                --backend "$backend"
                --policy "$policy"
                --task "$task"
              )
              for arg in "${server_args[@]}"; do
                runner_args+=("--server-arg=$arg")
              done
              run_cmd "${runner_args[@]}"
            fi

            mkdir -p "$run_dir"
            source scripts/dev/coding_agent_env.sh
            roboclaws_load_dotenv .env
            roboclaws_assert_codex_network_allowed "Codex Agibot semantic-map-build live report"

            codex_model="$(roboclaws_code_agent_model ROBOCLAWS_CODEX_MODEL ROBOCLAWS_CODEX_PROVIDER)"
            codex_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL)"
            codex_model_args=()
            roboclaws_codex_provider_args codex_model_args

            scripts/dev/coding_agent_docker.sh ensure
            docker_shim_dir=".tmp/coding-agent-bin"
            scripts/dev/coding_agent_docker.sh install-wrappers "$docker_shim_dir" >/dev/null
            codex_bin="$PWD/${docker_shim_dir}/codex"
            export ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE:-1}"
            export ROBOCLAWS_CODE_AGENT_DOCKER_TASK="${ROBOCLAWS_CODE_AGENT_DOCKER_TASK:-semantic-map-build}"
            export ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS="${ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-molmo-realworld-cleanup}"
            export ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE:-${run_dir}/agent-docker-workspace}"

            probe_host="$host"
            if [[ "$probe_host" == "0.0.0.0" || "$probe_host" == "::" ]]; then
              probe_host="127.0.0.1"
            fi
            if (echo > /dev/tcp/"$probe_host"/"$port") >/dev/null 2>&1; then
              echo "error: requested MCP port ${host}:${port} is already accepting connections" >&2
              exit 1
            fi

            runner="${run_dir}/run_live_codex_agibot_map_build.sh"
            status_path="${run_dir}/live_status.json"
            runner_args=(
              .venv/bin/python
              scripts/molmo_cleanup/run_live_codex_agibot_map_build.py
              --repo-root "$PWD"
              --run-dir "$run_dir"
              --status-path "$status_path"
              --client-url "$client_url"
              --host "$host"
              --port "$port"
              --codex-bin "$codex_bin"
              --codex-model "$codex_model"
              --codex-provider-summary "$codex_profile_summary"
              --server-startup-timeout-s "$server_startup_timeout_s"
              --kickoff-prompt "$prompt"
              --backend "$backend"
              --policy "$policy"
              --task "$task"
            )
            for arg in "${server_args[@]}"; do
              runner_args+=("--server-arg=$arg")
            done
            for arg in "${codex_model_args[@]}"; do
              runner_args+=("--codex-model-arg=$arg")
            done

            {
              printf '#!/usr/bin/env bash\n'
              printf 'set -Eeuo pipefail\n'
              printf 'cd %q\n' "$PWD"
              printf 'if [[ -f .env ]]; then set -a; source .env; set +a; fi\n'
              printf 'exec > >(tee -a %q) 2>&1\n' "${run_dir}/driver.log"
              printf 'exec'
              for arg in "${runner_args[@]}"; do
                printf ' %q' "$arg"
              done
              printf '\n'
            } > "$runner"
            chmod +x "$runner"
            printf '{"phase":"queued","started_at_epoch":%s}\n' "$(date +%s)" > "$status_path"

            if command -v tmux >/dev/null 2>&1; then
              session_name="roboclaws-agibot-map-codex-${stamp}-seed-${seed}"
              session_name="${session_name//[^A-Za-z0-9_.-]/-}"
              if tmux has-session -t "$session_name" >/dev/null 2>&1; then
                echo "error: tmux session already exists: ${session_name}" >&2
                exit 1
              fi
              printf '%s\n' "$session_name" > "${run_dir}/tmux_session.txt"
              tmux_env_args=()
              for env_name in \
                OPENAI_API_KEY CODEX_API_KEY CODEX_BASE_URL KIMI_API_KEY MIMO_TP_KEY \
                XM_LLM_API_KEY XM_LLM_BASE_URL \
                HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY \
                http_proxy https_proxy all_proxy no_proxy \
                ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL \
                ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS \
                ROBOCLAWS_REPORT_RERUN_COMMAND
              do
                if [[ -n "${!env_name:-}" ]]; then
                  tmux_env_args+=(-e "${env_name}=${!env_name}")
                fi
              done
              tmux new-session -d -s "$session_name" "${tmux_env_args[@]}" "bash $(printf '%q' "$runner")"
              echo "==> launched detached Codex Agibot semantic-map-build"
              echo "    tmux session : ${session_name}"
              echo "    run dir      : ${run_dir}"
              echo "    attach       : tmux attach -t ${session_name}"
              echo "    tail         : tail -f ${run_dir}/driver.log"
              exit 0
            fi

            exec "${runner_args[@]}"
          fi
          agibot_args=(.venv/bin/python scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py
            --context-json "$context_json"
            --output-dir "$output_dir")
          waypoint_id="$(get waypoint_id "")"
          if [[ -n "$waypoint_id" ]]; then
            agibot_args+=(--waypoint-id "$waypoint_id")
          fi
          run_dir="$(get run_dir "")"
          if [[ -n "$run_dir" ]]; then
            agibot_args+=(--run-dir "$run_dir")
          fi
          runner_python="$(get runner_python "")"
          if [[ -n "$runner_python" ]]; then
            agibot_args+=(--runner-python "$runner_python")
          fi
          runner_script="$(get runner_script "")"
          if [[ -n "$runner_script" ]]; then
            agibot_args+=(--runner-script "$runner_script")
          fi
          agibot_map_artifact_dir="$(get agibot_map_artifact_dir "")"
          if [[ -n "$agibot_map_artifact_dir" ]]; then
            agibot_args+=(--agibot-map-artifact-dir "$agibot_map_artifact_dir")
          fi
          real_movement_enabled="$(get real_movement_enabled false)"
          case "$real_movement_enabled" in
            true|1|yes|on)
              agibot_args+=(--real-movement-enabled)
              ;;
            false|0|no|off|"")
              ;;
            *)
              echo "error: unsupported real_movement_enabled '$real_movement_enabled' (expected true|false)" >&2
              exit 1
              ;;
          esac
          run_cmd "${agibot_args[@]}"
        fi
        run_just molmo::cleanup "$impl_driver" "$profile" "$seeds" \
          "$output_dir" "$prompt" "$generated_mess_count" "$host" "$port" \
          "$map_bundle" "$cleanup_routine" "$robot_views" "$visual_grounding" \
          "$visual_grounding_timeout_s" "$semantic_sweep" "$runtime_map_prior" "$backend" \
          "$map_mode"
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
      molmo-realworld-cleanup|molmo-realworld-agent-mcp|molmo-realworld-agent-dogfood-kit|\
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
      run|navigator|regression|sim|openclaw|molmo-realworld-cleanup|\
      molmo-cleanup-codex-perf|\
      molmo-realworld-agent-mcp|molmo-realworld-agent-dogfood-kit|\
      molmo-realworld-openclaw-dogfood-kit|\
      molmo-realworld-openclaw-visual-dogfood-kit|molmo-realworld-raw-fpv|\
      molmo-planner-proof-bundle-runner|molmo-planner-proof-bundle-execute-rerun|\
      molmo-planner-manipulation-probe|molmo-visual-grounding-benchmark|\
      molmo-isaac-runtime-preflight|molmo-isaac-usd-references|\
      molmo-isaac-runtime-smoke|molmo-isaac-cleanup-smoke|\
      list-tasks|history)
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
