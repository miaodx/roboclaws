# MolmoSpaces cleanup operator commands.
#
# This module is the human-facing facade for the ADR-0003 cleanup matrix.
# Use `driver`, `runtime`, and `evidence` to make the run shape explicit.
#
# Drivers:
# - direct          deterministic Python cleanup loop; no MCP server
# - mcp-smoke       deterministic ADR-0003 MCP tool smoke; no live LLM agent
# - openclaw-smoke  OpenClaw-labeled MCP smoke; no live Gateway
# - codex-live      live Codex CLI connected to the cleanup MCP server
# - claude-live     live Claude Code connected to the cleanup MCP server
# - openclaw-live   live OpenClaw Gateway connected to the cleanup MCP server
#
# Runtimes:
# - synthetic       api_semantic_synthetic, cheap contract shape
# - molmospaces     real upstream MolmoSpaces subprocess backend
#
# Evidence:
# - semantic        shared report without RBY1M robot-view timeline
# - visual          RBY1M FPV/chase/map/verification timeline
# - raw-fpv         raw FPV-only observation evidence plus robot timeline
#
# Preferred entrypoints:
# - just molmo::quick-check
# - just molmo::review-report
# - just molmo::mcp-smoke-report
# - just molmo::openclaw-smoke-report
# - just molmo::raw-fpv-report
# - just molmo::codex-report
# - just molmo::claude-report
# - just molmo::openclaw-report

set working-directory := '..'

timestamp_cmd := "TZ=Asia/Shanghai date +%m%d_%H%M"
codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"
claude_full_permission_args := "--dangerously-skip-permissions --permission-mode bypassPermissions"

default:
    @just --list molmo

# Explicit matrix runner.
cleanup driver="mcp-smoke" runtime="synthetic" evidence="semantic" seeds="7" output_dir="output/molmo/cleanup" task="帮我收拾这个房间" generated_mess_count="10" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    driver="{{driver}}"
    runtime="{{runtime}}"
    evidence="{{evidence}}"
    seeds="{{seeds}}"
    output_dir="{{output_dir}}"
    task="{{task}}"
    generated_mess_count="{{generated_mess_count}}"
    host="{{host}}"
    port="{{port}}"

    # Just recipe parameters are positional. Strip optional key= prefixes for
    # the first axes so `just molmo::cleanup driver=direct runtime=synthetic`
    # stays usable for operators.
    driver="${driver#driver=}"
    runtime="${runtime#runtime=}"
    evidence="${evidence#evidence=}"
    seeds="${seeds#seeds=}"
    output_dir="${output_dir#output_dir=}"
    task="${task#task=}"
    generated_mess_count="${generated_mess_count#generated_mess_count=}"
    host="${host#host=}"
    port="${port#port=}"

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

    case "$runtime" in
      synthetic|mock)
        backend="api_semantic_synthetic"
        min_generated_mess_count="5"
        ;;
      molmospaces|real)
        backend="molmospaces_subprocess"
        min_generated_mess_count="$generated_mess_count"
        ;;
      *)
        echo "error: unsupported runtime '$runtime' (expected synthetic|molmospaces)" >&2
        exit 1
        ;;
    esac

    perception_mode="visible_object_detections"
    visual_args=()
    checker_visual_args=()
    case "$evidence" in
      semantic)
        ;;
      visual)
        if [[ "$backend" != "molmospaces_subprocess" ]]; then
          echo "error: evidence=visual requires runtime=molmospaces" >&2
          exit 1
        fi
        visual_args=(--include-robot --robot-name rby1m --record-robot-views)
        checker_visual_args=(
          --require-robot-views
          --require-waypoint-honesty
          --require-real-robot-alignment
        )
        ;;
      raw-fpv)
        if [[ "$backend" != "molmospaces_subprocess" ]]; then
          echo "error: evidence=raw-fpv requires runtime=molmospaces" >&2
          exit 1
        fi
        perception_mode="raw_fpv_only"
        visual_args=(--include-robot --robot-name rby1m --record-robot-views)
        checker_visual_args=(--require-robot-views --require-raw-fpv-observations)
        ;;
      *)
        echo "error: unsupported evidence '$evidence' (expected semantic|visual|raw-fpv)" >&2
        exit 1
        ;;
    esac

    stamp="$({{timestamp_cmd}})"
    run_root="${output_dir}/${stamp}"
    mkdir -p "$run_root"

    echo "==> Molmo cleanup matrix"
    echo "    driver   : ${driver}"
    echo "    runtime  : ${runtime} (${backend})"
    echo "    evidence : ${evidence}"
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
        if [[ "$driver" == "openclaw-live" ]]; then
          bash scripts/dev/network_status.sh --assert-off-work "OpenClaw Molmo cleanup live report"
          server_host="0.0.0.0"
          client_url="http://host.docker.internal:${port}/mcp"
        elif [[ "$driver" == "claude-live" ]]; then
          bash scripts/dev/network_status.sh --assert-off-work "Claude Code Molmo cleanup live report"
        fi
        if [[ "$driver" == "codex-live" ]] && ! command -v codex >/dev/null 2>&1; then
          echo "error: codex command not found; install or activate Codex before running molmo::codex-report" >&2
          exit 1
        fi
        if [[ "$driver" == "claude-live" ]] && ! command -v claude >/dev/null 2>&1; then
          echo "error: claude command not found; install or activate Claude Code before running molmo::claude-report" >&2
          exit 1
        fi
        source scripts/dev/coding_agent_env.sh
        roboclaws_load_dotenv .env
        codex_model="$(roboclaws_code_agent_model ROBOCLAWS_CODEX_MODEL)"
        claude_model="$(roboclaws_code_agent_model ROBOCLAWS_CLAUDE_MODEL)"
        codex_model_args=()
        claude_model_args=()
        roboclaws_code_agent_model_args codex_model_args ROBOCLAWS_CODEX_MODEL
        roboclaws_code_agent_model_args claude_model_args ROBOCLAWS_CLAUDE_MODEL
        codex_bin="$(command -v codex || true)"
        claude_bin="$(command -v claude || true)"
        kickoff_prompt="Read skills/molmo-realworld-cleanup/SKILL.md. Then use the roboclaws MCP cleanup tools only: call roboclaws__metric_map and roboclaws__fixture_hints first, sweep waypoints with roboclaws__navigate_to_waypoint then roboclaws__observe, clean plausible observed objects with navigate->pick->navigate->open?->place following required_tool if returned, do not call scene_objects or read private scoring artifacts, then call roboclaws__done when finished so the report is generated."

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
          "${visual_args[@]}"
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
            --kickoff-prompt "$kickoff_prompt"
            --backend "$backend"
            --policy "$policy"
            --task "$task"
            --min-generated-mess-count "$min_generated_mess_count"
            --evidence "$evidence"
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

          tmux new-session -d -s "$session_name" "bash $(printf '%q' "$runner")"
          echo "==> launched detached Codex Molmo cleanup"
          echo "    tmux session : ${session_name}"
          echo "    run dir      : ${run_dir}"
          echo "    status       : just molmo::status ${run_dir}"
          echo "    attach       : tmux attach -t ${session_name}"
          echo "    tail         : tail -f ${run_dir}/driver.log"
          exit 0
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

        case "$driver" in
          claude-live)
            claude mcp remove roboclaws >/dev/null 2>&1 || true
            claude mcp add --transport http roboclaws "$client_url"
            echo "==> launching Claude Code with full permissions"
            if [[ -n "$claude_model" ]]; then
              echo "==> Claude Code model override for this run: ${claude_model}"
            fi
            echo "==> MCP URL: ${client_url}"
            echo "==> kickoff: ${kickoff_prompt}"
            "$claude_bin" "${claude_model_args[@]}" {{claude_full_permission_args}}
            ;;
          openclaw-live)
            echo "==> launching OpenClaw Gateway chat with cleanup skill"
            echo "==> MCP URL from Gateway container: ${client_url}"
            SKILLS_DIR="$PWD/skills/molmo-realworld-cleanup" \
              ROBOCLAWS_MCP_URL="$client_url" \
              just chat::run
            ;;
        esac

        echo "==> waiting for cleanup MCP server to finish after agent done"
        wait "$server_pid"
        trap - EXIT INT TERM

        if [[ -f "${run_dir}/run_result.json" ]]; then
          checker_args=(
            --expect-task "$task"
            --expect-backend "$backend"
            --expect-policy "$policy"
            --expect-mcp-server molmo_cleanup_realworld
            --min-generated-mess-count "$min_generated_mess_count"
            --require-agent-driven
            --require-advisory-scoring
            "${checker_visual_args[@]}"
          )
          if [[ "$driver" == "openclaw-live" ]]; then
            checker_args+=(--require-openclaw-minimum)
          fi
          if [[ "$evidence" == "visual" && "$driver" != "openclaw-live" ]]; then
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
            --generated-mess-count "$generated_mess_count" \
            "${visual_args[@]}" \
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
            "${visual_args[@]}" \
            --output-dir "$run_dir"
          ;;
      esac
    done

    seed_csv="$(printf '%s' "$seeds" | tr ' ' ',')"
    checker_args=(
      --expect-task "$task"
      --expect-backend "$backend"
      --expect-seeds "$seed_csv"
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
        if [[ "$evidence" == "visual" ]]; then
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
        if [[ "$evidence" == "visual" ]]; then
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
quick-check driver="mcp-smoke" runtime="synthetic" evidence="semantic" seed="7" output_dir="output/molmo/quick-check" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "{{driver}}" "{{runtime}}" "{{evidence}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Canonical human review report: direct cleanup, real MolmoSpaces/RBY1M visuals.
review-report seeds="1 2 3" output_dir="output/molmo/review-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "direct" "molmospaces" "visual" "{{seeds}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Deterministic ADR-0003 MCP tool smoke with real MolmoSpaces/RBY1M visuals.
mcp-smoke-report seed="7" output_dir="output/molmo/mcp-smoke-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "mcp-smoke" "molmospaces" "visual" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# OpenClaw-shaped/policy-labeled smoke with real MolmoSpaces/RBY1M visuals.
openclaw-smoke-report seed="7" output_dir="output/molmo/openclaw-smoke-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "openclaw-smoke" "molmospaces" "visual" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Raw FPV-only evidence report. This proves camera artifact plumbing, not cleanup success.
raw-fpv-report seed="7" output_dir="output/molmo/raw-fpv-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::cleanup "direct" "molmospaces" "raw-fpv" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Live Codex CLI report. Starts the cleanup MCP server and launches Codex.
codex-report seed="7" output_dir="output/molmo/codex-report" task="帮我收拾这个房间" generated_mess_count="10" runtime="molmospaces" evidence="visual" host="127.0.0.1" port="18788":
    just molmo::cleanup "codex-live" "{{runtime}}" "{{evidence}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}" "{{host}}" "{{port}}"

# Probe a detached live-agent run. Defaults to the latest Codex cleanup report.
status path="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "{{path}}" ]]; then
      exec .venv/bin/python scripts/molmo_cleanup/summarize_live_run.py "{{path}}"
    fi
    exec .venv/bin/python scripts/molmo_cleanup/summarize_live_run.py

# Live Claude Code report. Starts the cleanup MCP server and launches Claude Code.
claude-report seed="7" output_dir="output/molmo/claude-report" task="帮我收拾这个房间" generated_mess_count="10" runtime="molmospaces" evidence="visual" host="127.0.0.1" port="18788":
    just molmo::cleanup "claude-live" "{{runtime}}" "{{evidence}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}" "{{host}}" "{{port}}"

# Live OpenClaw Gateway report. Starts the cleanup MCP server and then chat::run.
openclaw-report seed="7" output_dir="output/molmo/openclaw-report" task="帮我收拾这个房间" generated_mess_count="10" runtime="molmospaces" evidence="visual" port="18788":
    just molmo::cleanup "openclaw-live" "{{runtime}}" "{{evidence}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}" "0.0.0.0" "{{port}}"
