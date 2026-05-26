# MolmoSpaces cleanup operator commands.
#
# This module is the human-facing facade for the ADR-0003 cleanup matrix.
# Use `driver` and `profile` to make the public run shape explicit.
#
# Drivers:
# - direct          deterministic Python cleanup loop; no MCP server
# - mcp-smoke       deterministic ADR-0003 MCP tool smoke; no live LLM agent
# - openclaw-smoke  OpenClaw-labeled MCP smoke; no live Gateway
# - codex-live      live Codex CLI connected to the cleanup MCP server
# - claude-live     live Claude Code connected to the cleanup MCP server
# - openclaw-live   live OpenClaw Gateway connected to the cleanup MCP server
#
# Profiles:
# - smoke           synthetic contract sanity with world labels and semantic report
# - world-labels    MolmoSpaces/RBY1M report; agent receives structured world labels
# - camera-raw      MolmoSpaces/RBY1M report; agent receives raw camera artifacts
# - camera-labels   MolmoSpaces/RBY1M report; agent receives camera-derived labels
#
# Preferred entrypoints:
# - just molmo::quick-check
# - just molmo::review-report
# - just molmo::mcp-smoke-report
# - just molmo::openclaw-smoke-report
# - just molmo::camera-raw-report
# - just molmo::codex-report
# - just molmo::claude-report
# - just molmo::openclaw-report

set working-directory := '..'

timestamp_cmd := "TZ=Asia/Shanghai date +%m%d_%H%M"
codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"
claude_full_permission_args := "--dangerously-skip-permissions --permission-mode bypassPermissions"

default:
    @just --list molmo

# Explicit profile runner.
cleanup driver="mcp-smoke" profile="smoke" seeds="7" output_dir="output/molmo/cleanup" task="帮我收拾这个房间" generated_mess_count="10" host="127.0.0.1" port="18788" map_bundle="auto" cleanup_routine="auto" robot_views="auto" visual_grounding="sim":
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
    visual_grounding="{{visual_grounding}}"

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
    visual_grounding="${visual_grounding#visual_grounding=}"

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

    perception_mode="visible_object_detections"
    visual_args=()
    checker_visual_args=()
    profile_requires_clean_success="true"
    visual_grounding_args=()
    if [[ "$visual_grounding" != "sim" ]]; then
      visual_grounding_args=(--visual-grounding "$visual_grounding")
    fi
    case "$profile" in
      smoke)
        backend="api_semantic_synthetic"
        min_generated_mess_count="5"
        ;;
      world-labels)
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
      camera-raw)
        backend="molmospaces_subprocess"
        min_generated_mess_count="$generated_mess_count"
        perception_mode="raw_fpv_only"
        visual_args=(--include-robot --robot-name rby1m --record-robot-views)
        checker_visual_args=(
          --require-robot-views
          --require-raw-fpv-observations
          --require-model-declared-observations
          --min-model-declared-observations 7
          --min-model-declared-actions 7
          --min-semantic-accepted-count 7
          --min-sweep-coverage 1.0
        )
        ;;
      camera-labels)
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
        echo "error: unsupported profile '$profile' (expected smoke|world-labels|camera-raw|camera-labels)" >&2
        exit 1
        ;;
    esac
    if [[ "$cleanup_routine" == "auto" ]]; then
      cleanup_routine="skill"
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
    if [[ "$profile" != "smoke" ]]; then
      if [[ -z "$map_bundle_dir" ]]; then
        echo "error: profile '$profile' requires a selected prebuilt Nav2 map bundle" >&2
        exit 1
      fi
      map_bundle_args+=(--require-map-bundle)
    fi

    stamp="$({{timestamp_cmd}})"
    run_root="${output_dir}/${stamp}"
    mkdir -p "$run_root"

    echo "==> Molmo cleanup matrix"
    echo "    driver   : ${driver}"
    echo "    profile  : ${profile}"
    echo "    backend  : ${backend}"
    echo "    input    : ${perception_mode}"
    echo "    map      : ${map_bundle_dir:-not required}"
    echo "    routine  : ${cleanup_routine}"
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
          export ROBOCLAWS_CODE_AGENT_DOCKER_TASK="${ROBOCLAWS_CODE_AGENT_DOCKER_TASK:-molmo-cleanup}"
          export ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS="${ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-molmo-realworld-cleanup}"
          export ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE:-${run_dir}/agent-docker-workspace}"
        fi
        case "$profile" in
          camera-raw)
            kickoff_prompt="Read skills/molmo-realworld-cleanup/SKILL.md. This is the trace-preserving RAW_FPV skill lane. Then use the roboclaws MCP cleanup tools only: call roboclaws__metric_map and roboclaws__fixture_hints first, build an exact waypoint checklist from metric_map.inspection_waypoints, sweep every inspection waypoint with roboclaws__navigate_to_waypoint then roboclaws__observe, and mark a waypoint complete only after that waypoint_id has a roboclaws__observe response. Inspect each raw FPV image block returned by observe, do not expect structured labels, and when you see a plausible cleanup object call roboclaws__navigate_to_visual_candidate with source_observation_id, a broad category when uncertain (food, dish, book, linen, toy, electronics, pillow), target_fixture_id, evidence_note, and image_region before pick. Use image_region={type:bbox,value:[x,y,width,height]} or {type:verbal_region,value:front of desk}; do not send bare x/y/width/height fields. Omit source_fixture_id unless you are confident. If visual candidate grounding is unresolved, continue the waypoint sweep instead of calling done; if your successful cleanup count is still below seven, reobserve from another public waypoint or retry the candidate at most once with a broader category or clearer verbal_region. When grounding succeeds, pick the returned object and place it using candidate_fixture_id and recommended_tool from the response when present, and increment your successful cleanup count only after the place/place_inside succeeds. Do not pre-register raw-FPV candidates with roboclaws__declare_visual_candidates. Clean at least seven grounded visual candidates with navigate_to_visual_candidate->pick->navigate_to_receptacle->open?->place when grounding succeeds, do not call scene_objects or read private scoring artifacts, compare the checklist before roboclaws__done, visit any missing waypoint_id, and call roboclaws__done only after every metric_map.inspection_waypoints waypoint_id has been observed and at least seven grounded cleanup chains have succeeded so the report is generated."
            ;;
          camera-labels)
            kickoff_prompt="Read skills/molmo-realworld-cleanup/SKILL.md. Then use the roboclaws MCP cleanup tools only: call roboclaws__metric_map and roboclaws__fixture_hints first, build an exact waypoint checklist from metric_map.inspection_waypoints, treat the selected Nav2 map bundle only through metric_map/fixture_hints and not raw occupancy images, sweep every waypoint with roboclaws__navigate_to_waypoint then roboclaws__observe, mark a waypoint complete only after that waypoint_id has an observe response, call roboclaws__declare_visual_candidates for each raw FPV observation before choosing cleanup candidates, and treat returned candidates as coming from the configured visual-grounding pipeline without asking for service URLs, credentials, image paths, or model hosts. Clean plausible observed_* camera candidates with navigate->pick->navigate->open?->place following required_tool if returned, do not call scene_objects or read private scoring artifacts, compare the checklist before roboclaws__done, visit any missing waypoint_id, and call roboclaws__done only after every metric_map.inspection_waypoints waypoint_id has been observed so the report is generated."
            ;;
          *)
            kickoff_prompt="Read skills/molmo-realworld-cleanup/SKILL.md. Then use the roboclaws MCP cleanup tools only: call roboclaws__metric_map and roboclaws__fixture_hints first, build an exact waypoint checklist from metric_map.inspection_waypoints, treat the selected Nav2 map bundle only through metric_map/fixture_hints and not raw occupancy images, sweep every waypoint with roboclaws__navigate_to_waypoint then roboclaws__observe, mark a waypoint complete only after that waypoint_id has an observe response, clean plausible observed objects with navigate->pick->navigate->open?->place following required_tool if returned, do not call scene_objects or read private scoring artifacts, compare the checklist before roboclaws__done, visit any missing waypoint_id, and call roboclaws__done only after every metric_map.inspection_waypoints waypoint_id has been observed so the report is generated."
            ;;
        esac

        server_args=(
          --host "$server_host"
          --port "$port"
          --output-dir "$run_dir"
          --seed "$seed"
          --policy "$policy"
          --backend "$backend"
          --task "$task"
          --generated-mess-count "$generated_mess_count"
          --perception-mode "$perception_mode"
          --cleanup-profile "$profile"
          "${map_bundle_args[@]}"
          "${visual_args[@]}"
          "${visual_grounding_args[@]}"
        )

        if [[ "$driver" == "codex-live" ]]; then
          if ! command -v tmux >/dev/null 2>&1; then
            echo "error: tmux command not found; install tmux before running detached Codex cleanup" >&2
            exit 1
          fi

          active_runner="$(pgrep -af 'scripts/molmo_cleanup/run_live_codex_cleanup[.]py' || true)"
          active_server="$(pgrep -af 'examples/molmo_cleanup/molmo_realworld_cleanup_agent_server[.]py' || true)"
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
            ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS
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
          active_server="$(pgrep -af 'examples/molmo_cleanup/molmo_realworld_cleanup_agent_server[.]py' || true)"
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

        .venv/bin/python examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py "${server_args[@]}" &
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
          .venv/bin/python examples/molmo_cleanup/molmospaces_realworld_cleanup.py \
            --seed "$seed" \
            --backend "$backend" \
            --task "$task" \
            --fixture-hint-mode room_only \
            --perception-mode "$perception_mode" \
            --cleanup-profile "$profile" \
            "${map_bundle_args[@]}" \
            --generated-mess-count "$generated_mess_count" \
            "${visual_args[@]}" \
            "${visual_grounding_args[@]}" \
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
            --perception-mode "$perception_mode" \
            --cleanup-profile "$profile" \
            "${map_bundle_args[@]}" \
            "${visual_args[@]}" \
            "${visual_grounding_args[@]}" \
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
    just molmo::cleanup "direct" "world-labels" "{{seeds}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Deterministic ADR-0003 MCP tool smoke with real MolmoSpaces/RBY1M visuals.
mcp-smoke-report seed="7" output_dir="output/molmo/mcp-smoke-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "mcp-smoke" "world-labels" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# OpenClaw-shaped/policy-labeled smoke with real MolmoSpaces/RBY1M visuals.
openclaw-smoke-report seed="7" output_dir="output/molmo/openclaw-smoke-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "openclaw-smoke" "world-labels" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Raw camera-input evidence report. This proves camera artifact plumbing, not cleanup success.
camera-raw-report seed="7" output_dir="output/molmo/camera-raw-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "direct" "camera-raw" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Live Codex CLI report. Starts the cleanup MCP server and launches Codex.
codex-report seed="7" output_dir="output/molmo/codex-report" task="帮我收拾这个房间" generated_mess_count="10" profile="world-labels" host="127.0.0.1" port="18788":
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
claude-report seed="7" output_dir="output/molmo/claude-report" task="帮我收拾这个房间" generated_mess_count="10" profile="world-labels" host="127.0.0.1" port="18788":
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

# Live OpenClaw Gateway report. Starts the cleanup MCP server and then chat::run.
openclaw-report seed="7" output_dir="output/molmo/openclaw-report" task="帮我收拾这个房间" generated_mess_count="10" profile="world-labels" port="18788":
    just molmo::cleanup "openclaw-live" "{{profile}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}" "0.0.0.0" "{{port}}"
