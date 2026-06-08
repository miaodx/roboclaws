# MolmoSpaces cleanup operator commands.
#
# This module is the human-facing facade for the ADR-0003 cleanup matrix.
# Use `driver` and cleanup input/evidence lane to make the public run shape explicit.
#
# Drivers:
# - direct          deterministic Python cleanup loop; no MCP server
# - mcp-smoke       deterministic ADR-0003 MCP tool smoke; no live LLM agent
# - openclaw-smoke  OpenClaw-labeled MCP smoke; no live Gateway
# - codex-live      live Codex CLI connected to the cleanup MCP server
# - claude-live     live Claude Code connected to the cleanup MCP server
# - openclaw-live   live OpenClaw Gateway connected to the cleanup MCP server
#
# Cleanup evidence lanes:
# - smoke                  cheap verification preset; uses world-oracle labels
# - world-oracle-labels    privileged world labels; cleanup upper bound
# - world-public-labels    public/sanitized world labels without oracle hints
# - camera-raw-fpv         raw camera artifacts to the agent
# - camera-grounded-labels camera-derived labels; requires camera_labeler
#
# Preferred entrypoints:
# - just molmo::quick-check
# - just molmo::review-report
# - just molmo::mcp-smoke-report
# - just molmo::openclaw-smoke-report
# - just molmo::camera-raw-fpv-report
# - just molmo::codex-report
# - just molmo::claude-report
# - just molmo::openclaw-report

set working-directory := '..'

timestamp_cmd := "TZ=Asia/Shanghai date +%m%d_%H%M"
codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"
claude_full_permission_args := "--dangerously-skip-permissions --permission-mode bypassPermissions"

default:
    @just --list molmo

# Explicit cleanup evidence-lane runner. The recipe parameter remains named
# `profile` for positional Just compatibility; public callers should pass the
# new evidence lane names.
cleanup driver="mcp-smoke" profile="smoke" seeds="7" output_dir="output/molmo/cleanup" task="帮我收拾这个房间" generated_mess_count="10" host="127.0.0.1" port="18788" map_bundle="auto" cleanup_routine="auto" robot_views="auto" camera_labeler="" visual_grounding_timeout_s="auto" semantic_sweep="off" runtime_map_prior="" backend_override="auto" map_mode="minimal" scene_source="procthor-10k-val" scene_index="0" isaac_scene_usd_path="" min_generated_mess_count_override="auto" generated_mess_object_ids="" task_name="household-cleanup":
    #!/usr/bin/env bash
    set -euo pipefail

    driver="{{driver}}"
    profile="{{profile}}"
    seeds="{{seeds}}"
    output_dir="{{output_dir}}"
    task="{{task}}"
    generated_mess_count="{{generated_mess_count}}"
    host="{{host}}"
    port="{{port}}"
    map_bundle="{{map_bundle}}"
    cleanup_routine="{{cleanup_routine}}"
    robot_views="{{robot_views}}"
    camera_labeler="{{camera_labeler}}"
    visual_grounding=""
    visual_grounding_timeout_s="{{visual_grounding_timeout_s}}"
    semantic_sweep="{{semantic_sweep}}"
    runtime_map_prior="{{runtime_map_prior}}"
    backend_override="{{backend_override}}"
    map_mode="{{map_mode}}"
    scene_source="{{scene_source}}"
    scene_index="{{scene_index}}"
    isaac_scene_usd_path="{{isaac_scene_usd_path}}"
    min_generated_mess_count_override="{{min_generated_mess_count_override}}"
    generated_mess_object_ids="{{generated_mess_object_ids}}"
    task_name="{{task_name}}"

    # Just recipe parameters are positional. Strip optional key= prefixes for
    # the first axes so `just molmo::cleanup driver=direct profile=smoke`
    # stays usable for operators.
    driver="${driver#driver=}"
    profile="${profile#profile=}"
    seeds="${seeds#seeds=}"
    output_dir="${output_dir#output_dir=}"
    task="${task#task=}"
    generated_mess_count="${generated_mess_count#generated_mess_count=}"
    host="${host#host=}"
    port="${port#port=}"
    map_bundle="${map_bundle#map_bundle=}"
    cleanup_routine="${cleanup_routine#cleanup_routine=}"
    robot_views="${robot_views#robot_views=}"
    robot_views="${robot_views#record_robot_views=}"
    profile="${profile#evidence_lane=}"
    camera_labeler="${camera_labeler#camera_labeler=}"
    camera_labeler="${camera_labeler#camera-labeler=}"
    visual_grounding_timeout_s="${visual_grounding_timeout_s#visual_grounding_timeout_s=}"
    visual_grounding_timeout_s="${visual_grounding_timeout_s#visual_grounding_timeout=}"
    semantic_sweep="${semantic_sweep#semantic_sweep=}"
    runtime_map_prior="${runtime_map_prior#runtime_map_prior=}"
    backend_override="${backend_override#backend=}"
    backend_override="${backend_override#backend_override=}"
    map_mode="${map_mode#map_mode=}"
    scene_source="${scene_source#scene_source=}"
    scene_index="${scene_index#scene_index=}"
    isaac_scene_usd_path="${isaac_scene_usd_path#isaac_scene_usd_path=}"
    min_generated_mess_count_override="${min_generated_mess_count_override#min_generated_mess_count=}"
    min_generated_mess_count_override="${min_generated_mess_count_override#min_generated_mess_count_override=}"
    generated_mess_object_ids="${generated_mess_object_ids#generated_mess_object_ids=}"
    task_name="${task_name#task_name=}"
    task_name="${task_name#task-name=}"
    generated_mess_success_threshold=$(( (generated_mess_count * 7 + 9) / 10 ))

    if [[ "$camera_labeler" == visual_grounding=* ]]; then
      echo "error: visual_grounding is no longer a public task axis; use camera_labeler=<labeler> with evidence_lane=camera-grounded-labels" >&2
      exit 1
    fi
    if [[ "$profile" == "camera-grounded-labels" ]]; then
      if [[ -z "$camera_labeler" ]]; then
        echo "error: evidence_lane=camera-grounded-labels requires camera_labeler" >&2
        exit 1
      fi
      case "$camera_labeler" in
        sim-projected-labels)
          visual_grounding="sim"
          ;;
        grounding-dino|yoloe|omdet-turbo|yolo-world|fake-http|contract-fake|grounding-dino+mimo-v2.5|yoloe+mimo-v2.5|grounding-dino+qwen3-vl|mimo-v2.5-direct|qwen3-vl-direct)
          visual_grounding="$camera_labeler"
          ;;
        *)
          echo "error: unsupported camera_labeler '$camera_labeler'" >&2
          exit 1
          ;;
      esac
    else
      if [[ -n "$camera_labeler" ]]; then
        echo "error: camera_labeler is only valid for evidence_lane=camera-grounded-labels" >&2
        exit 1
      fi
      visual_grounding="sim"
    fi

    case "$driver" in
      direct|mcp-smoke|openclaw-smoke|codex-live|claude-live|openclaw-live)
        ;;
      *)
        echo "error: unsupported driver '$driver'" >&2
        echo "       expected direct|mcp-smoke|openclaw-smoke|codex-live|claude-live|openclaw-live" >&2
        echo "       use mcp-smoke/openclaw-smoke for deterministic substitutes; live agent names are explicit" >&2
        exit 1
        ;;
    esac

    case "$cleanup_routine" in
      auto|skill)
        ;;
      *)
        echo "error: unsupported cleanup_routine '$cleanup_routine' (expected auto|skill)" >&2
        exit 1
        ;;
    esac

    case "$robot_views" in
      auto|on|off|true|false|1|0)
        ;;
      *)
        echo "error: unsupported robot_views '$robot_views' (expected auto|on|off)" >&2
        exit 1
        ;;
    esac

    semantic_sweep_enabled="false"
    case "$semantic_sweep" in
      on|true|1|yes|semantic-sweep)
        semantic_sweep_enabled="true"
        ;;
      off|false|0|no|"")
        ;;
      *)
        echo "error: unsupported semantic_sweep '$semantic_sweep' (expected on|off)" >&2
        exit 1
        ;;
    esac
    if [[ "$semantic_sweep_enabled" == "true" && "$driver" != "direct" && "$driver" != "codex-live" ]]; then
      echo "error: semantic sweep mode currently supports direct or codex-live driver only" >&2
      exit 1
    fi
    case "$map_mode" in
      rich|minimal)
        ;;
      *)
        echo "error: unsupported map_mode '$map_mode' (expected rich|minimal)" >&2
        exit 1
        ;;
    esac

    perception_mode="visible_object_detections"
    visual_args=()
    checker_visual_args=()
    profile_requires_clean_success="true"
    visual_grounding_args=()
    runtime_map_prior_args=()
    if [[ "$visual_grounding" != "sim" ]]; then
      visual_grounding_args=(--visual-grounding "$visual_grounding")
      if [[ "$visual_grounding_timeout_s" != "auto" && -n "$visual_grounding_timeout_s" ]]; then
        visual_grounding_args+=(--visual-grounding-timeout-s "$visual_grounding_timeout_s")
      fi
    fi
    if [[ -n "$runtime_map_prior" ]]; then
      runtime_map_prior_args=(--runtime-map-prior "$runtime_map_prior")
    fi
    case "$profile" in
      smoke)
        backend="api_semantic_synthetic"
        min_generated_mess_count="5"
        ;;
      world-oracle-labels)
        backend="molmospaces_subprocess"
        min_generated_mess_count="$generated_mess_count"
        visual_args=(--include-robot --robot-name rby1m)
        checker_visual_args=(
          --require-waypoint-honesty
          --require-real-robot-alignment
          --min-semantic-accepted-count 5
          --min-sweep-coverage 1.0
        )
        if [[ "$robot_views" != "off" && "$robot_views" != "false" && "$robot_views" != "0" ]]; then
          visual_args+=(--record-robot-views)
          checker_visual_args=(--require-robot-views "${checker_visual_args[@]}")
        fi
        ;;
      world-public-labels)
        backend="molmospaces_subprocess"
        min_generated_mess_count="$generated_mess_count"
        visual_args=(--include-robot --robot-name rby1m)
        checker_visual_args=(
          --require-waypoint-honesty
          --require-real-robot-alignment
          --min-semantic-accepted-count 5
          --min-sweep-coverage 1.0
        )
        if [[ "$robot_views" != "off" && "$robot_views" != "false" && "$robot_views" != "0" ]]; then
          visual_args+=(--record-robot-views)
          checker_visual_args=(--require-robot-views "${checker_visual_args[@]}")
        fi
        ;;
      camera-raw-fpv)
        backend="molmospaces_subprocess"
        min_generated_mess_count="$generated_mess_count"
        perception_mode="raw_fpv_only"
        raw_fpv_required_cleanup_count="$generated_mess_success_threshold"
        visual_args=(--include-robot --robot-name rby1m --record-robot-views)
        checker_visual_args=(
          --require-robot-views
          --require-raw-fpv-observations
          --require-model-declared-observations
          --min-model-declared-observations "$raw_fpv_required_cleanup_count"
          --min-model-declared-actions "$raw_fpv_required_cleanup_count"
          --min-semantic-accepted-count "$raw_fpv_required_cleanup_count"
          --min-sweep-coverage 1.0
        )
        ;;
      camera-grounded-labels)
        backend="molmospaces_subprocess"
        min_generated_mess_count="$generated_mess_count"
        perception_mode="camera_model_policy"
        visual_args=(--include-robot --robot-name rby1m --record-robot-views)
        checker_visual_args=(--require-robot-views --require-camera-model-policy)
        if [[ "$visual_grounding" != "sim" ]]; then
          checker_visual_args+=(
            --expect-visual-grounding-pipeline "$visual_grounding"
            --allow-partial-cleanup
            --min-sweep-coverage 1.0
          )
        fi
        ;;
      *)
        echo "error: unsupported cleanup lane '$profile' (expected smoke|world-oracle-labels|world-public-labels|camera-grounded-labels|camera-raw-fpv)" >&2
        exit 1
        ;;
    esac
    case "$backend_override" in
      auto|"")
        ;;
      api_semantic_synthetic|molmospaces_subprocess|isaaclab_subprocess)
        backend="$backend_override"
        ;;
      *)
        echo "error: unsupported backend '$backend_override' (expected api_semantic_synthetic|molmospaces_subprocess|isaaclab_subprocess)" >&2
        exit 1
        ;;
    esac
    if [[ "$profile" == "world-oracle-labels" && "$backend" == "isaaclab_subprocess" ]]; then
      isaac_min_semantic_accepted_count="$generated_mess_count"
      if [[ "$min_generated_mess_count_override" != "auto" && -n "$min_generated_mess_count_override" ]]; then
        isaac_min_semantic_accepted_count="$min_generated_mess_count_override"
      fi
      checker_visual_args=(
        --require-waypoint-honesty
        --require-real-robot-alignment
        --min-semantic-accepted-count "$isaac_min_semantic_accepted_count"
        --min-sweep-coverage 1.0
      )
      if [[ "$robot_views" != "off" && "$robot_views" != "false" && "$robot_views" != "0" ]]; then
        checker_visual_args=(--require-robot-views "${checker_visual_args[@]}")
      fi
    fi
    if [[ "$cleanup_routine" == "auto" ]]; then
      cleanup_routine="skill"
    fi
    if [[ "$min_generated_mess_count_override" != "auto" && -n "$min_generated_mess_count_override" ]]; then
      min_generated_mess_count="$min_generated_mess_count_override"
    fi
    semantic_sweep_args=()
    checker_semantic_args=()
    if [[ "$semantic_sweep_enabled" == "true" && "$driver" == "codex-live" ]]; then
      checker_semantic_args=(--require-runtime-metric-map)
      profile_requires_clean_success="false"
      filtered_checker_visual_args=()
      skip_checker_arg_value="false"
      for checker_arg in "${checker_visual_args[@]}"; do
        if [[ "$skip_checker_arg_value" == "true" ]]; then
          skip_checker_arg_value="false"
          continue
        fi
        case "$checker_arg" in
          --min-semantic-accepted-count|--min-model-declared-actions)
            skip_checker_arg_value="true"
            ;;
          *)
            filtered_checker_visual_args+=("$checker_arg")
            ;;
        esac
      done
      checker_visual_args=("${filtered_checker_visual_args[@]}")
    elif [[ "$semantic_sweep_enabled" == "true" ]]; then
      semantic_sweep_args=(--semantic-sweep)
      checker_semantic_args=(--require-semantic-sweep)
      profile_requires_clean_success="false"
      filtered_checker_visual_args=()
      skip_checker_arg_value="false"
      for checker_arg in "${checker_visual_args[@]}"; do
        if [[ "$skip_checker_arg_value" == "true" ]]; then
          skip_checker_arg_value="false"
          continue
        fi
        case "$checker_arg" in
          --min-semantic-accepted-count|--min-model-declared-actions)
            skip_checker_arg_value="true"
            ;;
          *)
            filtered_checker_visual_args+=("$checker_arg")
            ;;
        esac
      done
      checker_visual_args=("${filtered_checker_visual_args[@]}")
    fi
    semantic_sweep_args+=(--map-mode "$map_mode")
    if [[ "$map_mode" == "minimal" ]]; then
      checker_semantic_args+=(--require-minimal-map)
    fi

    map_bundle_dir="$map_bundle"
    case "$map_bundle_dir" in
      auto)
        if [[ "$profile" == "smoke" ]]; then
          map_bundle_dir=""
        else
          map_bundle_dir="assets/maps/molmospaces-procthor-val-0-7"
        fi
        ;;
      none|false|off)
        map_bundle_dir=""
        ;;
    esac
    if [[ -n "$map_bundle_dir" && "$map_bundle_dir" != */* && -d "assets/maps/${map_bundle_dir}" ]]; then
      map_bundle_dir="assets/maps/${map_bundle_dir}"
    fi
    map_bundle_args=()
    if [[ -n "$map_bundle_dir" ]]; then
      .venv/bin/python scripts/maps/check_bundle.py "$map_bundle_dir" >/dev/null
      map_bundle_args=(--map-bundle-dir "$map_bundle_dir")
    fi
    isaac_scene_args=()
    if [[ -n "$isaac_scene_usd_path" ]]; then
      isaac_scene_args=(--isaac-scene-usd-path "$isaac_scene_usd_path")
    fi
    generated_mess_object_args=()
    if [[ -n "$generated_mess_object_ids" ]]; then
      IFS=',' read -r -a generated_mess_object_id_items <<< "$generated_mess_object_ids"
      for generated_mess_object_id in "${generated_mess_object_id_items[@]}"; do
        generated_mess_object_id="${generated_mess_object_id#"${generated_mess_object_id%%[![:space:]]*}"}"
        generated_mess_object_id="${generated_mess_object_id%"${generated_mess_object_id##*[![:space:]]}"}"
        if [[ -n "$generated_mess_object_id" ]]; then
          generated_mess_object_args+=(--generated-mess-object-id "$generated_mess_object_id")
        fi
      done
    fi
    if [[ "$profile" != "smoke" ]]; then
      if [[ -z "$map_bundle_dir" ]]; then
        if [[ "$backend" != "molmospaces_subprocess" && "$backend" != "isaaclab_subprocess" ]]; then
          echo "error: profile '$profile' requires a selected prebuilt Nav2 map bundle" >&2
          exit 1
        fi
        echo "==> no map bundle selected; using backend-derived public metric map"
      else
        map_bundle_args+=(--require-map-bundle)
      fi
    fi

    stamp="$({{timestamp_cmd}})"
    run_root="${output_dir}/${stamp}"
    mkdir -p "$run_root"

    echo "==> Molmo cleanup matrix"
    echo "    driver   : ${driver}"
    echo "    lane     : ${profile}"
    echo "    backend  : ${backend}"
    echo "    input    : ${perception_mode}"
    echo "    map      : ${map_bundle_dir:-not required}"
    echo "    map mode : ${map_mode}"
    echo "    routine  : ${cleanup_routine}"
    echo "    sweep    : ${semantic_sweep_enabled}"
    echo "    views    : ${robot_views}"
    echo "    seeds    : ${seeds}"
    echo "    run root : ${run_root}"

    live_drivers=(codex-live claude-live openclaw-live)
    for live_driver in "${live_drivers[@]}"; do
      if [[ "$driver" == "$live_driver" ]]; then
        seed_count="$(wc -w <<<"$seeds" | tr -d ' ')"
        if [[ "$seed_count" != "1" ]]; then
          echo "error: live agent drivers accept exactly one seed per interactive run" >&2
          exit 1
        fi
        seed="$seeds"
        run_dir="${run_root}/seed-${seed}"
        mkdir -p "$run_dir"
        policy="${driver%-live}_agent"
        server_host="$host"
        client_url="http://${host}:${port}/mcp"
        server_startup_timeout_s="${ROBOCLAWS_MOLMO_LIVE_SERVER_STARTUP_TIMEOUT_S:-600}"
        source scripts/dev/coding_agent_env.sh
        roboclaws_load_dotenv .env
        if [[ "$driver" == "openclaw-live" ]]; then
          bash scripts/dev/network_status.sh --assert-off-work "OpenClaw Molmo cleanup live report"
          server_host="0.0.0.0"
          client_url="http://host.docker.internal:${port}/mcp"
        elif [[ "$driver" == "claude-live" ]]; then
          roboclaws_assert_claude_code_network_allowed "Claude Code Molmo cleanup live report"
        elif [[ "$driver" == "codex-live" ]]; then
          roboclaws_assert_codex_network_allowed "Codex Molmo cleanup live report"
        fi
        codex_model=""
        codex_profile_summary="system defaults"
        claude_profile_summary="system defaults"
        codex_model_args=()
        claude_model_args=()
        claude_env_args=()
        if [[ "$driver" == "codex-live" ]]; then
          codex_model="$(roboclaws_code_agent_model ROBOCLAWS_CODEX_MODEL ROBOCLAWS_CODEX_PROVIDER)"
          codex_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL)"
          roboclaws_codex_provider_args codex_model_args
        elif [[ "$driver" == "claude-live" ]]; then
          claude_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CLAUDE_PROVIDER ROBOCLAWS_CLAUDE_MODEL)"
          roboclaws_claude_provider_args claude_model_args claude_env_args
        fi
        codex_bin=""
        claude_bin=""
        if [[ "$driver" == "codex-live" || "$driver" == "claude-live" ]]; then
          scripts/dev/coding_agent_docker.sh ensure
          docker_shim_dir=".tmp/coding-agent-bin"
          scripts/dev/coding_agent_docker.sh install-wrappers "$docker_shim_dir" >/dev/null
          codex_bin="$PWD/${docker_shim_dir}/codex"
          claude_bin="$PWD/${docker_shim_dir}/claude"
          export ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE:-1}"
          export ROBOCLAWS_CODE_AGENT_DOCKER_TASK="${ROBOCLAWS_CODE_AGENT_DOCKER_TASK:-${task_name}}"
          export ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS="${ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-molmo-realworld-cleanup}"
          export ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE:-${run_dir}/agent-docker-workspace}"
        fi
        prompt_cleanup_count="$generated_mess_count"
        if [[ "$profile" == "camera-raw-fpv" ]]; then
          prompt_cleanup_count="$generated_mess_success_threshold"
        fi
        kickoff_prompt="$(.venv/bin/python -m roboclaws.agents.prompts.household_cleanup --profile "$profile" --task-name "$task_name" --task "$task" --target-cleanup-count "$prompt_cleanup_count")"

        server_args=(
          --host "$server_host"
          --port "$port"
          --output-dir "$run_dir"
          --seed "$seed"
          --policy "$policy"
          --task-name "$task_name"
          --backend "$backend"
          --task "$task"
          --generated-mess-count "$generated_mess_count"
          "${generated_mess_object_args[@]}"
          --perception-mode "$perception_mode"
          --cleanup-profile "$profile"
          --scene-source "$scene_source"
          --scene-index "$scene_index"
          "${map_bundle_args[@]}"
          "${visual_args[@]}"
          "${visual_grounding_args[@]}"
          "${runtime_map_prior_args[@]}"
          --map-mode "$map_mode"
        )
        if [[ -n "$isaac_scene_usd_path" ]]; then
          server_args+=(--isaac-scene-usd-path "$isaac_scene_usd_path")
        fi

        if [[ "$driver" == "codex-live" ]]; then
          if ! command -v tmux >/dev/null 2>&1; then
            echo "error: tmux command not found; install tmux before running detached Codex cleanup" >&2
            exit 1
          fi

          active_runner="$(pgrep -af 'scripts/molmo_cleanup/run_live_codex_cleanup[.]py' || true)"
          active_server="$(pgrep -af 'roboclaws[.]cli[.]agent_server household-cleanup' || true)"
          active_sessions="$(tmux list-sessions -F '#S' 2>/dev/null | grep '^roboclaws-molmo-codex-' || true)"
          if [[ -n "$active_runner$active_server$active_sessions" ]]; then
            echo "error: another live Molmo cleanup run appears to be active" >&2
            [[ -n "$active_sessions" ]] && echo "active tmux sessions:" >&2 && echo "$active_sessions" >&2
            [[ -n "$active_runner" ]] && echo "active runners:" >&2 && echo "$active_runner" >&2
            [[ -n "$active_server" ]] && echo "active MCP servers:" >&2 && echo "$active_server" >&2
            echo "probe latest: just molmo::status" >&2
            echo "stop the active run before launching another; visual Molmo cleanup owns a MuJoCo-backed backend" >&2
            exit 1
          fi

          probe_host="$host"
          if [[ "$probe_host" == "0.0.0.0" || "$probe_host" == "::" ]]; then
            probe_host="127.0.0.1"
          fi
          if (echo > /dev/tcp/"$probe_host"/"$port") >/dev/null 2>&1; then
            echo "error: requested MCP port ${host}:${port} is already accepting connections" >&2
            echo "       refusing to choose another port because each live visual cleanup run owns a MuJoCo-backed backend" >&2
            exit 1
          fi

          session_name="roboclaws-molmo-codex-${stamp}-seed-${seed}"
          session_name="${session_name//[^A-Za-z0-9_.-]/-}"
          if tmux has-session -t "$session_name" >/dev/null 2>&1; then
            echo "error: tmux session already exists: ${session_name}" >&2
            echo "       attach with: tmux attach -t ${session_name}" >&2
            exit 1
          fi

          runner="${run_dir}/run_live_codex.sh"
          status_path="${run_dir}/live_status.json"
          printf '%s\n' "$session_name" > "${run_dir}/tmux_session.txt"

          runner_args=(
            .venv/bin/python
            scripts/molmo_cleanup/run_live_codex_cleanup.py
            --repo-root "$PWD"
            --run-dir "$run_dir"
            --status-path "$status_path"
            --client-url "$client_url"
            --host "$host"
            --port "$port"
            --lock-path output/molmo/.live-codex.lock
            --tmux-session "$session_name"
            --codex-bin "$codex_bin"
            --codex-model "$codex_model"
            --codex-provider-summary "$codex_profile_summary"
            --server-startup-timeout-s "$server_startup_timeout_s"
            --kickoff-prompt "$kickoff_prompt"
            --backend "$backend"
            --task-name "$task_name"
            --policy "$policy"
            --task "$task"
            --min-generated-mess-count "$min_generated_mess_count"
            --profile "$profile"
          )
          for arg in "${server_args[@]}"; do
            runner_args+=("--server-arg=$arg")
          done
          for arg in "${codex_model_args[@]}"; do
            runner_args+=("--codex-model-arg=$arg")
          done
          for arg in "${checker_visual_args[@]}"; do
            runner_args+=("--checker-visual-arg=$arg")
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

          tmux_env_args=()
          for env_name in \
            OPENAI_API_KEY CODEX_API_KEY CODEX_BASE_URL KIMI_API_KEY MIMO_TP_KEY \
            XM_LLM_API_KEY XM_LLM_BASE_URL \
            HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY \
            http_proxy https_proxy all_proxy no_proxy \
            DISPLAY XAUTHORITY MUJOCO_GL PYOPENGL_PLATFORM LIBGL_ALWAYS_SOFTWARE \
            ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL \
            ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS \
            ROBOCLAWS_CODEX_TURN_IDLE_TIMEOUT_S \
            ROBOCLAWS_ISAACLAB_PYTHON ROBOCLAWS_ISAACLAB_RUNTIME_MODE \
            ROBOCLAWS_REPORT_RERUN_COMMAND
          do
            if [[ -n "${!env_name:-}" ]]; then
              tmux_env_args+=(-e "${env_name}=${!env_name}")
            fi
          done
          tmux new-session -d -s "$session_name" "${tmux_env_args[@]}" "bash $(printf '%q' "$runner")"
          echo "==> launched detached Codex Molmo cleanup"
          echo "    tmux session : ${session_name}"
          echo "    run dir      : ${run_dir}"
          echo "    status       : just molmo::status ${run_dir}"
          echo "    attach       : tmux attach -t ${session_name}"
          echo "    tail         : tail -f ${run_dir}/driver.log"
          exit 0
        fi

        if [[ "$driver" == "claude-live" ]]; then
          active_runner="$(pgrep -af 'scripts/molmo_cleanup/run_live_claude_cleanup[.]py' || true)"
          active_server="$(pgrep -af 'roboclaws[.]cli[.]agent_server household-cleanup' || true)"
          if [[ -n "$active_runner$active_server" ]]; then
            echo "error: another live Molmo cleanup run appears to be active" >&2
            [[ -n "$active_runner" ]] && echo "active runners:" >&2 && echo "$active_runner" >&2
            [[ -n "$active_server" ]] && echo "active MCP servers:" >&2 && echo "$active_server" >&2
            echo "probe latest: just molmo::status" >&2
            echo "stop the active run before launching another; visual Molmo cleanup owns a MuJoCo-backed backend" >&2
            exit 1
          fi

          probe_host="$host"
          if [[ "$probe_host" == "0.0.0.0" || "$probe_host" == "::" ]]; then
            probe_host="127.0.0.1"
          fi
          if (echo > /dev/tcp/"$probe_host"/"$port") >/dev/null 2>&1; then
            echo "error: requested MCP port ${host}:${port} is already accepting connections" >&2
            echo "       refusing to choose another port because each live visual cleanup run owns a MuJoCo-backed backend" >&2
            exit 1
          fi

          status_path="${run_dir}/live_status.json"
          runner_args=(
            .venv/bin/python
            scripts/molmo_cleanup/run_live_claude_cleanup.py
            --repo-root "$PWD"
            --run-dir "$run_dir"
            --status-path "$status_path"
            --client-url "$client_url"
            --host "$host"
            --port "$port"
            --lock-path output/molmo/.live-claude.lock
            --claude-bin "$claude_bin"
            --claude-provider-summary "$claude_profile_summary"
            --server-startup-timeout-s "$server_startup_timeout_s"
            --kickoff-prompt "$kickoff_prompt"
            --backend "$backend"
            --policy "$policy"
            --task "$task"
            --min-generated-mess-count "$min_generated_mess_count"
            --profile "$profile"
          )
          for arg in "${server_args[@]}"; do
            runner_args+=("--server-arg=$arg")
          done
          for arg in "${claude_model_args[@]}"; do
            runner_args+=("--claude-model-arg=$arg")
          done
          for entry in "${claude_env_args[@]}"; do
            export "$entry"
          done
          for arg in "${checker_visual_args[@]}"; do
            runner_args+=("--checker-visual-arg=$arg")
          done

          exec "${runner_args[@]}"
        fi

        .venv/bin/python -m roboclaws.cli.agent_server household-cleanup "${server_args[@]}" &
        server_pid="$!"
        cleanup_server() {
          set +e
          if kill -0 "$server_pid" >/dev/null 2>&1; then
            kill "$server_pid" >/dev/null 2>&1 || true
            wait "$server_pid" >/dev/null 2>&1 || true
          fi
        }
        trap cleanup_server EXIT INT TERM
        wait_for_mcp_ready() {
          local wait_host="$1"
          local wait_port="$2"
          for _ in {1..240}; do
            if (echo > /dev/tcp/"$wait_host"/"$wait_port") >/dev/null 2>&1; then
              return 0
            fi
            if ! kill -0 "$server_pid" >/dev/null 2>&1; then
              wait "$server_pid" >/dev/null 2>&1 || true
              return 1
            fi
            sleep 0.5
          done
          return 1
        }
        if ! wait_for_mcp_ready "$host" "$port"; then
          echo "error: cleanup MCP server did not become ready at ${host}:${port}" >&2
          exit 1
        fi

        echo "==> launching OpenClaw Gateway chat with cleanup skill"
        echo "==> MCP URL from Gateway container: ${client_url}"
        SKILLS_DIR="$PWD/skills/molmo-realworld-cleanup" \
          ROBOCLAWS_MCP_URL="$client_url" \
          just chat::run

        echo "==> waiting for cleanup MCP server to finish after agent done"
        wait "$server_pid"
        trap - EXIT INT TERM

        if [[ -f "${run_dir}/run_result.json" ]]; then
          checker_args=(
            --expect-task "$task"
            --expect-backend "$backend"
            --expect-policy "$policy"
            --expect-profile "$profile"
            --expect-mcp-server molmo_cleanup_realworld
            --min-generated-mess-count "$min_generated_mess_count"
            --require-agent-driven
            --require-advisory-scoring
            "${checker_visual_args[@]}"
          )
          if [[ "$driver" == "openclaw-live" ]]; then
            checker_args+=(--require-openclaw-minimum)
          fi
          if [[ "$profile_requires_clean_success" == "true" && "$driver" != "openclaw-live" ]]; then
            checker_args+=(--require-clean-agent-run)
          fi
          .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
            "${checker_args[@]}" \
            "${run_dir}/run_result.json"
          echo "==> report: ${run_dir}/report.html"
        else
          echo "error: live run finished without ${run_dir}/run_result.json" >&2
          exit 1
        fi
        exit 0
      fi
    done

    for seed in $seeds; do
      run_dir="${run_root}/seed-${seed}"
      mkdir -p "$run_dir"
      case "$driver" in
        direct)
          .venv/bin/python -m roboclaws.household.realworld_cleanup \
            --seed "$seed" \
            --backend "$backend" \
            --task "$task" \
            --fixture-hint-mode room_only \
            --perception-mode "$perception_mode" \
            --cleanup-profile "$profile" \
            "${map_bundle_args[@]}" \
            --generated-mess-count "$generated_mess_count" \
            "${generated_mess_object_args[@]}" \
            --scene-source "$scene_source" \
            --scene-index "$scene_index" \
            "${visual_args[@]}" \
            "${visual_grounding_args[@]}" \
            "${runtime_map_prior_args[@]}" \
            "${semantic_sweep_args[@]}" \
            "${isaac_scene_args[@]}" \
            --output-dir "$run_dir"
          ;;
        mcp-smoke|openclaw-smoke)
          policy="realworld_contract_smoke_agent"
          if [[ "$driver" == "openclaw-smoke" ]]; then
            policy="openclaw_agent"
          fi
          .venv/bin/python scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py \
            --seed "$seed" \
            --backend "$backend" \
            --task "$task" \
            --policy "$policy" \
            --generated-mess-count "$generated_mess_count" \
            "${generated_mess_object_args[@]}" \
            --perception-mode "$perception_mode" \
            --cleanup-profile "$profile" \
            "${map_bundle_args[@]}" \
            "${visual_args[@]}" \
            "${visual_grounding_args[@]}" \
            "${runtime_map_prior_args[@]}" \
            --output-dir "$run_dir"
          ;;
      esac
    done

    seed_csv="$(printf '%s' "$seeds" | tr ' ' ',')"
    checker_args=(
      --expect-task "$task"
      --expect-backend "$backend"
      --expect-seeds "$seed_csv"
      --expect-profile "$profile"
      --min-generated-mess-count "$min_generated_mess_count"
      --require-advisory-scoring
      "${checker_visual_args[@]}"
      "${checker_semantic_args[@]}"
    )
    case "$driver" in
      mcp-smoke)
        checker_args+=(
          --expect-policy realworld_contract_smoke_agent
          --expect-mcp-server molmo_cleanup_realworld
          --require-agent-driven
        )
        if [[ "$profile_requires_clean_success" == "true" ]]; then
          checker_args+=(--require-clean-agent-run)
        fi
        ;;
      openclaw-smoke)
        checker_args+=(
          --expect-policy openclaw_agent
          --expect-mcp-server molmo_cleanup_realworld
          --require-agent-driven
          --require-openclaw-minimum
        )
        if [[ "$profile_requires_clean_success" == "true" ]]; then
          checker_args+=(--require-clean-agent-run)
        fi
        ;;
    esac

    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
      "${checker_args[@]}" \
      "$run_root"
    echo "==> reports:"
    find "$run_root" -maxdepth 2 -name report.html -print

# Cheap default: deterministic MCP smoke on the synthetic backend.
quick-check driver="mcp-smoke" profile="smoke" seed="7" output_dir="output/molmo/quick-check" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "{{driver}}" "{{profile}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Canonical human review report: direct cleanup, real MolmoSpaces/RBY1M visuals.
review-report seeds="1 2 3" output_dir="output/molmo/review-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "direct" "world-oracle-labels" "{{seeds}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Deterministic ADR-0003 MCP tool smoke with real MolmoSpaces/RBY1M visuals.
mcp-smoke-report seed="7" output_dir="output/molmo/mcp-smoke-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "mcp-smoke" "world-oracle-labels" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# OpenClaw-shaped/policy-labeled smoke with real MolmoSpaces/RBY1M visuals.
openclaw-smoke-report seed="7" output_dir="output/molmo/openclaw-smoke-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "openclaw-smoke" "world-oracle-labels" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Raw camera-input evidence report. This proves camera artifact plumbing, not cleanup success.
camera-raw-fpv-report seed="7" output_dir="output/molmo/camera-raw-fpv-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "direct" "camera-raw-fpv" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Live Codex CLI report. Starts the cleanup MCP server and launches Codex.
codex-report seed="7" output_dir="output/molmo/codex-report" task="帮我收拾这个房间" generated_mess_count="10" profile="world-oracle-labels" host="127.0.0.1" port="18788":
    just molmo::cleanup "codex-live" "{{profile}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}" "{{host}}" "{{port}}"

# Probe a detached live-agent run. Defaults to the latest Codex cleanup report.
status path="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "{{path}}" ]]; then
      exec .venv/bin/python scripts/molmo_cleanup/summarize_live_run.py "{{path}}"
    fi
    exec .venv/bin/python scripts/molmo_cleanup/summarize_live_run.py

# Live Claude Code report. Starts the cleanup MCP server and launches Claude Code.
claude-report seed="7" output_dir="output/molmo/claude-report" task="帮我收拾这个房间" generated_mess_count="10" profile="world-oracle-labels" host="127.0.0.1" port="18788":
    just molmo::cleanup "claude-live" "{{profile}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}" "{{host}}" "{{port}}"

# Local rehearsal for the opt-in hosted Molmo live CI job.
ci-rehearsal entry="kimi-k2.6" dry_run="":
    #!/usr/bin/env bash
    set -euo pipefail
    entry="{{entry}}"
    dry_run="{{dry_run}}"
    dry_args=()
    case "$dry_run" in
      ""|live)
        ;;
      --dry-run|dry-run|dry|true)
        dry_args=(--dry-run --skip-uv-sync --skip-prewarm --skip-version-check)
        ;;
      *)
        echo "error: unsupported ci-rehearsal mode '$dry_run' (expected live or --dry-run)" >&2
        exit 1
        ;;
    esac
    .venv/bin/python scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py \
      --entry "$entry" \
      --output-dir "output/molmo/ci-rehearsal" \
      --published-dir "output/molmo/ci-rehearsal/site/molmo/live" \
      "${dry_args[@]}"

# Serial local rehearsal for all Molmo live CI model/profile entries.
ci-rehearsal-all dry_run="":
    #!/usr/bin/env bash
    set -euo pipefail
    dry_run="{{dry_run}}"
    dry_args=()
    case "$dry_run" in
      ""|live)
        ;;
      --dry-run|dry-run|dry|true)
        dry_args=(--dry-run --skip-uv-sync --skip-prewarm --skip-version-check)
        ;;
      *)
        echo "error: unsupported ci-rehearsal-all mode '$dry_run' (expected live or --dry-run)" >&2
        exit 1
        ;;
    esac
    .venv/bin/python scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py \
      --all \
      --continue-on-error \
      --output-dir "output/molmo/ci-rehearsal" \
      --published-dir "output/molmo/ci-rehearsal/site/molmo/live" \
      "${dry_args[@]}"

# Build or execute the current MolmoSpaces apple-to-apple comparison grid.
apple2apple-grid mode="dry-run" output_dir="output/molmo/apple2apple-grid" seed="7" generated_mess_count="10" row="" runtime_map_prior="" visual_grounding_timeout_s="auto":
    #!/usr/bin/env bash
    set -euo pipefail
    mode="{{mode}}"
    output_dir="{{output_dir}}"
    seed="{{seed}}"
    generated_mess_count="{{generated_mess_count}}"
    row="{{row}}"
    runtime_map_prior="{{runtime_map_prior}}"
    visual_grounding_timeout_s="{{visual_grounding_timeout_s}}"

    mode="${mode#mode=}"
    output_dir="${output_dir#output_dir=}"
    seed="${seed#seed=}"
    generated_mess_count="${generated_mess_count#generated_mess_count=}"
    row="${row#row=}"
    runtime_map_prior="${runtime_map_prior#runtime_map_prior=}"
    visual_grounding_timeout_s="${visual_grounding_timeout_s#visual_grounding_timeout_s=}"

    args=(
      --output-dir "$output_dir"
      --seed "$seed"
      --generated-mess-count "$generated_mess_count"
      --visual-grounding-timeout-s "$visual_grounding_timeout_s"
    )
    if [[ -n "$row" ]]; then
      args+=(--row "$row")
    fi
    if [[ -n "$runtime_map_prior" ]]; then
      args+=(--runtime-map-prior "$runtime_map_prior")
    fi
    case "$mode" in
      dry-run|dry|"")
        ;;
      execute|run|live)
        args+=(--execute)
        ;;
      *)
        echo "error: unsupported apple2apple-grid mode '$mode' (expected dry-run or execute)" >&2
        exit 1
        ;;
    esac
    python_bin="${ROBOCLAWS_PYTHON:-}"
    if [[ -z "$python_bin" ]]; then
      if [[ -x ".venv/bin/python" ]]; then
        python_bin=".venv/bin/python"
      elif command -v python3 >/dev/null 2>&1; then
        python_bin="python3"
      else
        python_bin="python"
      fi
    fi
    "$python_bin" scripts/molmo_cleanup/run_molmo_apple2apple_test_grid.py "${args[@]}"

# Build or execute the eight-case live Codex cleanup harness.
codex-harness8 mode="dry-run" *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    mode="{{mode}}"
    output_dir="output/molmo/codex-harness8"
    seed="7"
    generated_mess_count="10"
    row=""
    runtime_map_prior=""
    visual_grounding_timeout_s="auto"
    provider_retry_attempts="1"
    provider_retry_sleep_s="60"
    dino_sidecar_lifecycle="auto"
    dino_sidecar_startup_timeout_s="180"

    mode="${mode#mode=}"
    for override in {{overrides}}; do
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
        output_dir|seed|generated_mess_count|row|runtime_map_prior|visual_grounding_timeout_s|provider_retry_attempts|provider_retry_sleep_s|dino_sidecar_lifecycle|dino_sidecar_startup_timeout_s)
          ;;
        visual_grounding_timeout)
          key="visual_grounding_timeout_s"
          ;;
        provider_retry_sleep)
          key="provider_retry_sleep_s"
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      printf -v "$key" '%s' "$value"
    done

    args=(
      --output-dir "$output_dir"
      --seed "$seed"
      --generated-mess-count "$generated_mess_count"
      --visual-grounding-timeout-s "$visual_grounding_timeout_s"
      --provider-retry-attempts "$provider_retry_attempts"
      --provider-retry-sleep-s "$provider_retry_sleep_s"
      --dino-sidecar-lifecycle "$dino_sidecar_lifecycle"
      --dino-sidecar-startup-timeout-s "$dino_sidecar_startup_timeout_s"
    )
    if [[ -n "$row" ]]; then
      IFS=',' read -r -a selected_rows <<< "$row"
      for selected_row in "${selected_rows[@]}"; do
        [[ -z "$selected_row" ]] && continue
        args+=(--row "$selected_row")
      done
    fi
    if [[ -n "$runtime_map_prior" ]]; then
      args+=(--runtime-map-prior "$runtime_map_prior")
    fi
    case "$mode" in
      dry-run|dry|"")
        ;;
      execute|run|live)
        args+=(--execute --continue-on-error)
        ;;
      *)
        echo "error: unsupported codex-harness8 mode '$mode' (expected dry-run or execute)" >&2
        exit 1
        ;;
    esac
    python_bin="${ROBOCLAWS_PYTHON:-}"
    if [[ -z "$python_bin" ]]; then
      if [[ -x ".venv/bin/python" ]]; then
        python_bin=".venv/bin/python"
      elif command -v python3 >/dev/null 2>&1; then
        python_bin="python3"
      else
        python_bin="python"
      fi
    fi
    "$python_bin" scripts/molmo_cleanup/run_codex_cleanup_harness8.py "${args[@]}"

# Live OpenClaw Gateway report. Starts the cleanup MCP server and then chat::run.
openclaw-report seed="7" output_dir="output/molmo/openclaw-report" task="帮我收拾这个房间" generated_mess_count="10" profile="world-oracle-labels" port="18788":
    just molmo::cleanup "openclaw-live" "{{profile}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}" "0.0.0.0" "{{port}}"

# Fast render-only comparison: current MuJoCo vs Python 3.11 MolmoSpaces Filament.
renderer-comparison seed="7" generated_mess_count="10" output_dir="output/molmo/renderer-comparison" scene_source="procthor-10k-val" scene_index="0" robot_name="rby1m" focus_sample_count="4" render_width="540" render_height="360":
    #!/usr/bin/env bash
    set -euo pipefail
    seed="{{seed}}"
    generated_mess_count="{{generated_mess_count}}"
    output_dir="{{output_dir}}"
    scene_source="{{scene_source}}"
    scene_index="{{scene_index}}"
    robot_name="{{robot_name}}"
    focus_sample_count="{{focus_sample_count}}"
    render_width="{{render_width}}"
    render_height="{{render_height}}"
    seed="${seed#seed=}"
    generated_mess_count="${generated_mess_count#generated_mess_count=}"
    output_dir="${output_dir#output_dir=}"
    scene_source="${scene_source#scene_source=}"
    scene_index="${scene_index#scene_index=}"
    robot_name="${robot_name#robot_name=}"
    focus_sample_count="${focus_sample_count#focus_sample_count=}"
    render_width="${render_width#render_width=}"
    render_height="${render_height#render_height=}"

    standard_python="${ROBOCLAWS_MOLMOSPACES_STANDARD_PYTHON:-.venv/bin/python}"
    filament_python="${ROBOCLAWS_MOLMOSPACES_FILAMENT_PYTHON:-.venv-molmospaces-filament/bin/python}"
    filament_setup_command=(
      'UV_PROJECT_ENVIRONMENT="$PWD/.venv-molmospaces-filament" \'
      '  uv sync --project sidecars/molmospaces-filament \'
      '  --python /home/mi/.local/share/uv/python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11 \'
      '  --index-strategy unsafe-best-match'
      'uv pip install --python .venv-molmospaces-filament/bin/python \'
      '  --default-index https://pypi.org/simple \'
      '  --index https://test.pypi.org/simple/ \'
      '  --index-strategy unsafe-best-match \'
      '  --reinstall-package mujoco-filament mujoco-filament==3.5.1'
    )
    if [[ ! -x "$standard_python" ]]; then
      echo "error: missing standard MolmoSpaces runtime: ${standard_python}" >&2
      echo "       run: uv sync --extra dev --extra molmospaces" >&2
      exit 1
    fi
    if [[ ! -x "$filament_python" ]]; then
      echo "error: missing Filament MolmoSpaces runtime: ${filament_python}" >&2
      echo "       setup command:" >&2
      printf '       %s\n' "${filament_setup_command[@]}" >&2
      exit 1
    fi
    filament_probe="$(
      "$filament_python" -c 'import importlib.metadata as m; import molmo_spaces, mujoco; print(mujoco.__version__ + "\t" + m.version("mujoco-filament"))' 2>/dev/null
    )" || {
      echo "error: incomplete Filament MolmoSpaces runtime: ${filament_python}" >&2
      echo "       expected imports failed: mujoco, molmo_spaces" >&2
      echo "       setup command:" >&2
      printf '       %s\n' "${filament_setup_command[@]}" >&2
      exit 1
    }
    mujoco_import_version="${filament_probe%%$'\t'*}"
    filament_dist_version="${filament_probe#*$'\t'}"
    if [[ "$mujoco_import_version" != "$filament_dist_version" ]]; then
      echo "error: incomplete Filament MolmoSpaces runtime: ${filament_python}" >&2
      echo "       mujoco imports version ${mujoco_import_version}, but mujoco-filament is ${filament_dist_version}" >&2
      echo "       reinstall mujoco-filament after uv sync so it owns the top-level mujoco module" >&2
      echo "       setup command:" >&2
      printf '       %s\n' "${filament_setup_command[@]}" >&2
      exit 1
    fi

    stamp="$({{timestamp_cmd}})"
    run_dir="${output_dir}/${stamp}"
    .venv/bin/python scripts/molmo_cleanup/run_molmospaces_renderer_comparison.py \
      --output-dir "$run_dir" \
      --standard-python "$standard_python" \
      --filament-python "$filament_python" \
      --seed "$seed" \
      --generated-mess-count "$generated_mess_count" \
      --scene-source "$scene_source" \
      --scene-index "$scene_index" \
      --robot-name "$robot_name" \
      --focus-sample-count "$focus_sample_count" \
      --render-width "$render_width" \
      --render-height "$render_height"

# Render-only scene identity probe: same MolmoSpaces scene anchors through MuJoCo and Isaac.
scene-camera-comparison seed="7" generated_mess_count="1" output_dir="output/molmo/scene-camera-comparison" scene_source="procthor-10k-val" scene_index="1" scene_usd_path="output/isaaclab/flattened-semantic-usd/0604_val1_mujoco_body_pose_fix/scene_semantic.usda" render_width="960" render_height="640" genesis="off" lighting_profile="default":
    #!/usr/bin/env bash
    set -euo pipefail
    seed="{{seed}}"
    generated_mess_count="{{generated_mess_count}}"
    output_dir="{{output_dir}}"
    scene_source="{{scene_source}}"
    scene_index="{{scene_index}}"
    scene_usd_path="{{scene_usd_path}}"
    render_width="{{render_width}}"
    render_height="{{render_height}}"
    genesis="{{genesis}}"
    lighting_profile="{{lighting_profile}}"
    raw_args=(
      "$seed"
      "$generated_mess_count"
      "$output_dir"
      "$scene_source"
      "$scene_index"
      "$scene_usd_path"
      "$render_width"
      "$render_height"
      "$genesis"
      "$lighting_profile"
    )
    seed="${seed#seed=}"
    generated_mess_count="${generated_mess_count#generated_mess_count=}"
    output_dir="${output_dir#output_dir=}"
    scene_source="${scene_source#scene_source=}"
    scene_index="${scene_index#scene_index=}"
    scene_usd_path="${scene_usd_path#scene_usd_path=}"
    render_width="${render_width#render_width=}"
    render_height="${render_height#render_height=}"
    genesis="${genesis#genesis=}"
    lighting_profile="${lighting_profile#lighting_profile=}"
    for override in "${raw_args[@]}"; do
      case "$override" in
        seed=*) seed="${override#seed=}" ;;
        generated_mess_count=*) generated_mess_count="${override#generated_mess_count=}" ;;
        output_dir=*) output_dir="${override#output_dir=}" ;;
        scene_source=*) scene_source="${override#scene_source=}" ;;
        scene_index=*) scene_index="${override#scene_index=}" ;;
        scene_usd_path=*) scene_usd_path="${override#scene_usd_path=}" ;;
        render_width=*) render_width="${override#render_width=}" ;;
        render_height=*) render_height="${override#render_height=}" ;;
        genesis=*) genesis="${override#genesis=}" ;;
        lighting_profile=*) lighting_profile="${override#lighting_profile=}" ;;
      esac
    done
    if [[ "$seed" == *=* && "${seed%%=*}" != "seed" ]]; then seed="7"; fi
    if [[ "$generated_mess_count" == *=* && "${generated_mess_count%%=*}" != "generated_mess_count" ]]; then generated_mess_count="1"; fi
    if [[ "$output_dir" == *=* && "${output_dir%%=*}" != "output_dir" ]]; then output_dir="output/molmo/scene-camera-comparison"; fi
    if [[ "$scene_source" == *=* && "${scene_source%%=*}" != "scene_source" ]]; then scene_source="procthor-10k-val"; fi
    if [[ "$scene_index" == *=* && "${scene_index%%=*}" != "scene_index" ]]; then scene_index="1"; fi
    if [[ "$scene_usd_path" == *=* && "${scene_usd_path%%=*}" != "scene_usd_path" ]]; then scene_usd_path="output/isaaclab/flattened-semantic-usd/0604_val1_mujoco_body_pose_fix/scene_semantic.usda"; fi
    if [[ "$render_width" == *=* && "${render_width%%=*}" != "render_width" ]]; then render_width="960"; fi
    if [[ "$render_height" == *=* && "${render_height%%=*}" != "render_height" ]]; then render_height="640"; fi
    if [[ "$genesis" == *=* && "${genesis%%=*}" != "genesis" ]]; then genesis="off"; fi
    if [[ "$lighting_profile" == *=* && "${lighting_profile%%=*}" != "lighting_profile" ]]; then lighting_profile="default"; fi

    molmospaces_python="${ROBOCLAWS_MOLMOSPACES_PYTHON:-.venv/bin/python}"
    isaac_python="${ROBOCLAWS_ISAACLAB_PYTHON:-.venv-isaaclab/bin/python}"
    genesis_python="${ROBOCLAWS_GENESIS_PYTHON:-.venv-genesis/bin/python}"
    if [[ ! -x "$molmospaces_python" ]]; then
      echo "error: missing MolmoSpaces runtime: ${molmospaces_python}" >&2
      echo "       run: uv sync --extra dev --extra molmospaces" >&2
      exit 1
    fi
    if [[ ! -x "$isaac_python" ]]; then
      echo "error: missing Isaac Lab runtime: ${isaac_python}" >&2
      echo "       create .venv-isaaclab/ or set ROBOCLAWS_ISAACLAB_PYTHON" >&2
      exit 1
    fi
    if [[ "$genesis" == "on" && ! -x "$genesis_python" ]]; then
      echo "error: missing Genesis runtime: ${genesis_python}" >&2
      echo "       create .venv-genesis/ or set ROBOCLAWS_GENESIS_PYTHON" >&2
      exit 1
    fi
    if [[ ! -f "$scene_usd_path" ]]; then
      echo "error: missing prepared scene USD: ${scene_usd_path}" >&2
      echo "       prepare or pass scene_usd_path=..." >&2
      exit 1
    fi

    stamp="$({{timestamp_cmd}})"
    run_dir="${output_dir}/${stamp}"
    OMNI_KIT_ACCEPT_EULA="${OMNI_KIT_ACCEPT_EULA:-YES}" \
      .venv/bin/python scripts/molmo_cleanup/run_molmospaces_scene_camera_comparison.py \
      --output-dir "$run_dir" \
      --scene-usd-path "$scene_usd_path" \
      --seed "$seed" \
      --generated-mess-count "$generated_mess_count" \
      --scene-source "$scene_source" \
      --scene-index "$scene_index" \
      --molmospaces-python "$molmospaces_python" \
      --isaac-python "$isaac_python" \
      --genesis "$genesis" \
      --genesis-python "$genesis_python" \
      --render-width "$render_width" \
      --render-height "$render_height" \
      --lighting-profile "$lighting_profile"
