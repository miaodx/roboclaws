# Agent-maintainer dispatchers.
#
# This namespace is intentionally compact. It exposes a small set of axes and
# delegates to private implementation modules.

set working-directory := '..'
set positional-arguments

[private]
default:
    @just --list agent

# Run a normalized private dispatch target / agent-engine tuple.
run dispatch_target agent_engine mode="" *overrides:
    #!/usr/bin/env bash
    set -euo pipefail

    args=("$@")
    dispatch_target="${args[0]}"
    agent_engine="${args[1]}"
    mode="${args[2]}"
    raw_overrides=("${args[@]:3}")

    dispatch_target="${dispatch_target#dispatch_target=}"
    dispatch_target="${dispatch_target#task=}"
    agent_engine="${agent_engine#agent_engine=}"
    agent_engine="${agent_engine#driver=}"

    has_raw_override_key() {
      local wanted="$1"
      local override
      for override in "${raw_overrides[@]}"; do
        if [[ "$override" == "$wanted="* || "$override" == "--$wanted="* ]]; then
          return 0
        fi
      done
      return 1
    }

    dispatch_intent="${dispatch_target##*.}"
    case "$dispatch_target" in
      household-world.cleanup)
        implementation_task_name="household-cleanup"
        ;;
      household-world.map-build)
        implementation_task_name="semantic-map-build"
        ;;
      household-world.open-ended)
        implementation_task_name="household-cleanup"
        if ! has_raw_override_key task_intent; then
          raw_overrides+=("task_intent=open-ended")
        fi
        ;;
      planner-proof.planner-proof)
        implementation_task_name="molmo-planner-proof"
        ;;
      household-cleanup|semantic-map-build|molmo-cleanup)
        echo "error: unsupported dispatch target '$dispatch_target' (expected household-world.cleanup|household-world.map-build|household-world.open-ended|planner-proof.planner-proof)" >&2
        exit 1
        ;;
      *)
        implementation_task_name="$dispatch_target"
        ;;
    esac

    case "$agent_engine" in
      codex-cli)
        driver="codex"
        ;;
      claude-code)
        driver="claude"
        ;;
      openai-agents-sdk)
        driver="openai-agents-live"
        ;;
      direct-runner)
        driver="direct"
        if [[ "$mode" == "smoke" && ( "$dispatch_intent" == "cleanup" || "$dispatch_intent" == "open-ended" ) ]]; then
          driver="mcp-smoke"
        fi
        ;;
      openclaw-gateway)
        driver="openclaw"
        ;;
      *)
        driver="$agent_engine"
        ;;
    esac
    case "$mode" in
      report=*)
        mode="${mode#report=}"
        ;;
      profile=*)
        mode="${mode#profile=}"
        ;;
      evidence_lane=*)
        mode="${mode#evidence_lane=}"
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
      if [[ "$key" == "map_mode" ]]; then
        echo "error: map_mode is no longer a public agent::run override; Base Navigation Map is the start-of-run map contract" >&2
        exit 1
      fi
      case "$key" in
        agibot_map_artifact_dir|backend|baseline|candidate|cap|context_json|\
        generated_mess_count|\
        cleanup_object_count|\
        cleanup_routine|record_robot_views|robot_views|\
        host|max_wall_seconds|min_generated_mess_count|\
        map_bundle|mode|output_dir|policy|port|prompt|provider|\
        camera_labeler|evidence_lane|profile|real_movement_enabled|rehearsal_mode|robot_name|run_dir|runner_python|runner_script|\
        runtime|runtime_map_prior|molmospaces_python|generated_mess_object_ids|\
        operator_messages_path|skill_name|task_intent|task_intent_mode|task_preset|task_surface|goal_contract_json|goal_contract_path|\
        scene_index|scene_source|seed|seeds|semantic_sweep|task|timeout_s|\
        isaac_scene_usd_path|\
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

    if [[ "$implementation_task_name" == "household-cleanup" || "$implementation_task_name" == "semantic-map-build" ]]; then
      profile="${mode:-$(get profile "$(get evidence_lane world-oracle-labels)")}"
      case "$profile" in
        smoke|world-oracle-labels|world-public-labels|camera-raw-fpv|camera-grounded-labels)
          ;;
        *)
          echo "error: unsupported household-world evidence_lane '$profile' (expected smoke|world-oracle-labels|world-public-labels|camera-grounded-labels|camera-raw-fpv)" >&2
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

    report_rerun_parts=("just" "run::surface")
    case "$implementation_task_name" in
      semantic-map-build)
        report_rerun_parts+=("surface=household-world" "preset=map-build")
        ;;
      household-cleanup)
        if [[ "${kv[task_preset]:-}" == "cleanup" ]]; then
          report_rerun_parts+=("surface=household-world" "preset=cleanup")
        elif [[ "${kv[task_intent]:-cleanup}" == "open-ended" ]]; then
          report_rerun_parts+=("surface=household-world")
        else
          report_rerun_parts+=("surface=household-world" "preset=${kv[task_intent]:-cleanup}")
        fi
        ;;
      molmo-planner-proof)
        report_rerun_parts+=("surface=planner-proof" "intent=planner-proof")
        ;;
    esac
    case "$driver" in
      codex)
        report_rerun_parts+=("agent_engine=codex-cli")
        ;;
      claude)
        report_rerun_parts+=("agent_engine=claude-code")
        ;;
      openai-agents-live)
        report_rerun_parts+=("agent_engine=openai-agents-sdk")
        ;;
      direct)
        report_rerun_parts+=("agent_engine=direct-runner")
        ;;
      mcp-smoke)
        report_rerun_parts+=("agent_engine=direct-runner")
        ;;
      openclaw)
        report_rerun_parts+=("agent_engine=openclaw-gateway")
        ;;
    esac
    if [[ "$implementation_task_name" == "household-cleanup" || "$implementation_task_name" == "semantic-map-build" ]]; then
      if [[ "$profile" == "smoke" ]]; then
        report_rerun_parts+=("run_preset=smoke" "evidence_lane=world-oracle-labels")
      else
        report_rerun_parts+=("evidence_lane=$profile")
      fi
    else
      report_rerun_parts+=("$report")
    fi
    for override in "${raw_overrides[@]}"; do
      [[ -n "$override" ]] && report_rerun_parts+=("$override")
    done
    export ROBOCLAWS_REPORT_RERUN_COMMAND="$(shell_join "${report_rerun_parts[@]}")"

    case "$implementation_task_name:$driver" in
      semantic-map-build:direct|semantic-map-build:codex|household-cleanup:direct|household-cleanup:mcp-smoke|household-cleanup:openclaw-smoke|\
      household-cleanup:codex|household-cleanup:claude|household-cleanup:openai-agents-live|household-cleanup:openclaw)
        case "$driver" in
          direct|mcp-smoke|openclaw-smoke)
            impl_driver="$driver"
            ;;
          codex)
            impl_driver="codex-live"
            ;;
          claude)
            impl_driver="claude-live"
            ;;
          openai-agents-live)
            impl_driver="openai-agents-live"
            ;;
          openclaw)
            impl_driver="openclaw-live"
            ;;
        esac
        if [[ "$implementation_task_name" == "semantic-map-build" && "$driver" != "direct" && "$driver" != "codex" ]]; then
          echo "error: household-world.map-build currently supports direct-runner or codex-cli only" >&2
          exit 1
        fi

        case "$profile" in
          world-oracle-labels)
            default_output_dir="output/household/${implementation_task_name}/${driver}-report"
            ;;
          smoke)
            default_output_dir="output/household/${implementation_task_name}/${driver}-smoke"
            ;;
          *)
            default_output_dir="output/household/${implementation_task_name}/${driver}-${profile}"
            ;;
        esac
        if [[ "$implementation_task_name" == "household-cleanup" && "$driver" == "direct" && "$profile" == "world-oracle-labels" ]]; then
          default_seeds="1 2 3"
        else
          default_seeds="7"
        fi
        seeds="$(get seeds "$(get seed "$default_seeds")")"
        output_dir="$(get output_dir "$default_output_dir")"
        if [[ "$implementation_task_name" == "semantic-map-build" ]]; then
          prompt="$(semantic_map_prompt)"
        else
          prompt="$(cleanup_prompt)"
        fi
        skill_name="$(get skill_name "${ROBOCLAWS_TASK_SKILL:-}")"
        task_intent_mode="$(get task_intent_mode "${ROBOCLAWS_TASK_INTENT_MODE:-}")"
        resolved_task_intent="$(get task_intent "${ROBOCLAWS_TASK_INTENT:-}")"
        if [[ -z "$resolved_task_intent" ]]; then
          if [[ "$implementation_task_name" == "semantic-map-build" ]]; then
            resolved_task_intent="map-build"
          else
            resolved_task_intent="cleanup"
          fi
        fi
        if [[ -z "$skill_name" ]]; then
          if [[ "$implementation_task_name" == "semantic-map-build" || "$resolved_task_intent" == "open-ended" ]]; then
            skill_name="household-open-task"
          else
            skill_name="molmo-realworld-cleanup"
          fi
        fi
        if [[ -z "$task_intent_mode" ]]; then
          task_intent_mode="default_cleanup"
        fi
        goal_contract_json="$(get goal_contract_json "${ROBOCLAWS_GOAL_CONTRACT_JSON:-}")"
        goal_contract_path="$(get goal_contract_path "${ROBOCLAWS_GOAL_CONTRACT_PATH:-}")"
        goal_contract_args=()
        if [[ -n "$goal_contract_json" ]]; then
          goal_contract_args+=(--goal-contract-json "$goal_contract_json")
        fi
        if [[ -n "$goal_contract_path" ]]; then
          goal_contract_args+=(--goal-contract "$goal_contract_path")
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
        camera_labeler="$(get camera_labeler "")"
        visual_grounding="$(get visual_grounding "")"
        if [[ -n "$visual_grounding" ]]; then
          echo "error: visual_grounding is no longer a public task axis; use camera_labeler=<labeler> with evidence_lane=camera-grounded-labels" >&2
          exit 1
        fi
        case "$profile" in
          camera-grounded-labels)
            if [[ -z "$camera_labeler" ]]; then
              echo "error: evidence_lane=camera-grounded-labels requires camera_labeler" >&2
              exit 1
            fi
            case "$camera_labeler" in
              sim-projected-labels)
                visual_grounding="sim"
                ;;
              grounding-dino|yoloe|omdet-turbo|yolo-world|fake-http|contract-fake)
                visual_grounding="$camera_labeler"
                ;;
              *)
                echo "error: unsupported camera_labeler '$camera_labeler'" >&2
                exit 1
                ;;
            esac
            ;;
          *)
            if [[ -n "$camera_labeler" ]]; then
              echo "error: camera_labeler is only valid for evidence_lane=camera-grounded-labels" >&2
              exit 1
            fi
            visual_grounding="sim"
            ;;
        esac
        visual_grounding_timeout_s="$(get visual_grounding_timeout_s "$(get visual_grounding_timeout auto)")"
        semantic_sweep="$(get semantic_sweep off)"
        if [[ "$implementation_task_name" == "semantic-map-build" ]]; then
          semantic_sweep="on"
        fi
        map_mode="$(get map_mode minimal)"
        runtime_map_prior="$(get runtime_map_prior "")"
        operator_messages_path="$(get operator_messages_path "")"
        backend="$(get backend auto)"
        min_generated_mess_count="$(get min_generated_mess_count auto)"
        generated_mess_object_ids="$(get generated_mess_object_ids "")"
        scene_source="$(get scene_source procthor-10k-val)"
        scene_index="$(get scene_index 0)"
        isaac_scene_usd_path="$(get isaac_scene_usd_path "")"
        if [[ "$backend" == "agibot_molmospaces_sim" && ! -v "kv[seeds]" && ! -v "kv[seed]" ]]; then
          seeds="7"
        fi
        if [[ "$implementation_task_name" == "semantic-map-build" && "$driver" == "codex" ]]; then
          backend="$(.venv/bin/python -m roboclaws.launch.backends map-build-codex-implementation-backend "$backend" --context "household-world.map-build codex-cli")"
        fi
        if [[ "$backend" == "agibot_molmospaces_sim" ]]; then
          if [[ "$driver" != "direct" ]]; then
            echo "error: backend=agibot_molmospaces_sim currently supports direct driver only" >&2
            exit 1
          fi
          default_rehearsal_mode="contract"
          if [[ "$implementation_task_name" == "household-cleanup" ]]; then
            default_rehearsal_mode="cleanup-actions"
          fi
          rehearsal_mode="$(get rehearsal_mode "$default_rehearsal_mode")"
          case "$rehearsal_mode" in
            contract|cleanup-actions)
              ;;
            *)
              echo "error: unsupported rehearsal_mode '$rehearsal_mode' (expected contract|cleanup-actions)" >&2
              exit 1
              ;;
          esac
          runtime="$(get runtime fixture)"
          case "$runtime" in
            fixture|molmospaces-subprocess)
              ;;
            *)
              echo "error: unsupported runtime '$runtime' (expected fixture|molmospaces-subprocess)" >&2
              exit 1
              ;;
          esac
          seed_count="$(wc -w <<<"$seeds" | tr -d ' ')"
          if [[ "$seed_count" != "1" ]]; then
            echo "error: backend=agibot_molmospaces_sim accepts exactly one seed per run" >&2
            exit 1
          fi
          cleanup_object_count="$(get cleanup_object_count 2)"
          sim_args=(.venv/bin/python scripts/molmo_cleanup/run_molmospaces_agibot_contract_rehearsal.py
            --output-dir "$output_dir"
            --seed "$seeds"
            --generated-mess-count "$generated_mess_count"
            --runtime "$runtime"
            --flow prehardware
            --task-name "$implementation_task_name"
            --profile "$profile"
            --task-prompt "$prompt"
            --rehearsal-mode "$rehearsal_mode"
            --cleanup-object-count "$cleanup_object_count")
          if [[ "$profile" == "camera-grounded-labels" ]]; then
            sim_args+=(--camera-labeler "$camera_labeler")
            if [[ "$visual_grounding_timeout_s" != "auto" && -n "$visual_grounding_timeout_s" ]]; then
              sim_args+=(--visual-grounding-timeout-s "$visual_grounding_timeout_s")
            fi
          fi
          molmospaces_python="$(get molmospaces_python "")"
          if [[ -n "$molmospaces_python" ]]; then
            sim_args+=(--molmospaces-python "$molmospaces_python")
          fi
          robot_name="$(get robot_name "")"
          if [[ -n "$robot_name" ]]; then
            sim_args+=(--robot-name "$robot_name")
          fi
          waypoint_id="$(get waypoint_id "")"
          if [[ -n "$waypoint_id" ]]; then
            sim_args+=(--waypoint-id "$waypoint_id")
          fi
          run_dir="$(get run_dir "")"
          if [[ -n "$run_dir" ]]; then
            sim_args+=(--run-dir "$run_dir")
          fi
          context_json="$(get context_json "")"
          if [[ -n "$context_json" ]]; then
            sim_args+=(--context-json "$context_json")
          fi
          agibot_map_artifact_dir="$(get agibot_map_artifact_dir "")"
          if [[ -n "$agibot_map_artifact_dir" ]]; then
            sim_args+=(--agibot-map-artifact-dir "$agibot_map_artifact_dir")
          fi
          case "$robot_views" in
            on|true|1|yes)
              sim_args+=(--include-robot --record-robot-views)
              ;;
            auto|"")
              if [[ "$runtime" == "molmospaces-subprocess" && "$profile" != "world-oracle-labels" ]]; then
                sim_args+=(--include-robot --record-robot-views)
              fi
              ;;
            off|false|0|no)
              ;;
            *)
              echo "error: unsupported robot_views '$robot_views' (expected auto|on|off)" >&2
              exit 1
              ;;
          esac
          run_cmd "${sim_args[@]}"
        fi
        if [[ "$backend" == "agibot_gdk" ]]; then
          context_json="$(get context_json "")"
          if [[ "$implementation_task_name" == "semantic-map-build" && "$driver" == "codex" ]]; then
            if [[ -z "$context_json" ]]; then
              echo "error: backend=agibot_gdk household-world.map-build codex-cli requires context_json=<agibot map context JSON>" >&2
              exit 1
            fi
            seed_count="$(wc -w <<<"$seeds" | tr -d ' ')"
            if [[ "$seed_count" != "1" ]]; then
              echo "error: Agibot household-world.map-build codex-cli accepts exactly one seed per live run" >&2
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
            )
            if [[ "$profile" == "camera-grounded-labels" ]]; then
              server_args+=(--camera-labeler "$camera_labeler")
            fi
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
                --task "$implementation_task_name"
              )
              for arg in "${server_args[@]}"; do
                runner_args+=("--server-arg=$arg")
              done
              run_cmd "${runner_args[@]}"
            fi

            mkdir -p "$run_dir"
            source scripts/dev/coding_agent_env.sh
            roboclaws_load_dotenv .env
            roboclaws_assert_codex_network_allowed "Codex Agibot household-world.map-build live report"

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
              --task "$implementation_task_name"
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
                XM_LLM_API_KEY XM_LLM_BASE_URL MM_API_KEY MM_BASE_URL \
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
              echo "==> launched detached Codex Agibot household-world.map-build"
              echo "    tmux session : ${session_name}"
              echo "    run dir      : ${run_dir}"
              echo "    attach       : tmux attach -t ${session_name}"
              echo "    tail         : tail -f ${run_dir}/driver.log"
              exit 0
            fi

            exec "${runner_args[@]}"
          fi
          agibot_args=(.venv/bin/python scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py
            --output-dir "$output_dir")
          if [[ -n "$context_json" ]]; then
            agibot_args+=(--context-json "$context_json")
          fi
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
        molmo_args=(
          "$impl_driver" "$profile" "$seeds"
          "$output_dir" "$prompt" "$generated_mess_count" "$host" "$port"
          "$map_bundle" "$cleanup_routine" "$robot_views" "$camera_labeler"
          "$visual_grounding_timeout_s" "$semantic_sweep" "$runtime_map_prior" "$backend"
          "$map_mode" "$scene_source" "$scene_index" "$isaac_scene_usd_path"
          "$min_generated_mess_count" "$generated_mess_object_ids" "$implementation_task_name"
          "$operator_messages_path"
        )
        task_intent_mode_was_appended=0
        if [[ "$implementation_task_name" == "household-cleanup" || "$resolved_task_intent" == "open-ended" ]]; then
          molmo_args+=("$task_intent_mode")
          task_intent_mode_was_appended=1
        fi
        run_dir_override="$(get run_dir "")"
        if [[ -n "$run_dir_override" ]]; then
          if [[ "$task_intent_mode_was_appended" != "1" ]]; then
            molmo_args+=("")
          fi
          molmo_args+=("" "" "" "$run_dir_override")
        fi
        ROBOCLAWS_GOAL_CONTRACT_JSON="$goal_contract_json" \
          ROBOCLAWS_GOAL_CONTRACT_PATH="$goal_contract_path" \
          ROBOCLAWS_MOLMO_RUN_DIR_OVERRIDE="$run_dir_override" \
          ROBOCLAWS_TASK_INTENT="$resolved_task_intent" \
          ROBOCLAWS_TASK_PRESET="${kv[task_preset]:-}" \
          ROBOCLAWS_TASK_SKILL="$skill_name" \
          run_just molmo::household-cleanup-impl "${molmo_args[@]}"
        ;;

      molmo-planner-proof:direct|molmo-planner-proof:mcp-smoke)
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
        echo "error: unsupported task/driver route '$implementation_task_name:$driver'" >&2
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
      static|mock|ci-required|contract|\
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
      molmo-realworld-cleanup|\
      agent-validation|\
      molmo-cleanup-codex-perf|\
      molmo-realworld-agent-mcp|molmo-realworld-agent-dogfood-kit|\
      molmo-realworld-openclaw-dogfood-kit|\
      molmo-realworld-openclaw-visual-dogfood-kit|molmo-realworld-raw-fpv|\
      molmo-planner-proof-bundle-runner|molmo-planner-proof-bundle-execute-rerun|\
      molmo-planner-manipulation-probe|molmo-visual-grounding-benchmark|\
      molmo-isaac-runtime-preflight|molmo-isaac-usd-references|\
      molmo-isaac-runtime-smoke|molmo-isaac-cleanup-smoke|\
      molmo-isaac-prepared-cleanup-smoke|\
      b1-map12-navigation-smoke)
        trace_or_exec harness::"$target" "${rest[@]}"
        ;;
      *)
        echo "error: unsupported harness target '$target'" >&2
        exit 1
        ;;
    esac

# Manage a household MCP server.
mcp action="up" server="household-world.cleanup" host="127.0.0.1" port="18788" output_dir=".tmp/roboclaws-mcp/run":
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
        server="$2"
        case "$server" in
          household-world.cleanup|cleanup)
            server="household-world.cleanup"
            ;;
          household-world.map-build|map-build)
            server="household-world.map-build"
            ;;
          *)
            echo "error: unsupported MCP dispatch target '$server' (expected household-world.cleanup|household-world.map-build)" >&2
            exit 1
            ;;
        esac
        trace_or_exec mcp::up "$server" "$3" "$4" "$5"
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

# Run a repo-native eval suite.
eval *overrides:
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
    if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
      printf 'cmd\t%s\t-m\troboclaws.cli.main\teval' "$python_bin"
      for arg in "$@"; do
        printf '\t%s' "$arg"
      done
      printf '\n'
      exit 0
    fi
    exec "$python_bin" -m roboclaws.cli.main eval "$@"
