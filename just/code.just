# Coding-agent MCP launcher for Codex/Claude Code.
#
# Preferred entrypoints:
# - just code::cc       launch Claude Code wired to the roboclaws MCP
# - just code::codex    launch Codex wired to the roboclaws MCP
#
# MCP server lifecycle is owned by `mcp::up` / `mcp::down` (see just/mcp.just).

set working-directory := '..'

default:
    @just --list code

# Local demos intentionally run coding agents with full permissions by default.
# Any new just recipe that launches Codex or Claude Code should call these
# recipes or reuse these args; avoid bare agent launches that fall back to
# read-only or approval-prompting modes.
codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"
claude_full_permission_args := "--dangerously-skip-permissions --permission-mode bypassPermissions"

cc scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    source scripts/dev/coding_agent_env.sh
    roboclaws_load_dotenv .env
    claude_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CLAUDE_PROVIDER ROBOCLAWS_CLAUDE_MODEL)"
    claude_model_args=()
    claude_env_args=()
    roboclaws_claude_provider_args claude_model_args claude_env_args

    bash scripts/dev/network_status.sh --assert-off-work "Claude Code direct MCP run"

    if ! command -v codex >/dev/null 2>&1; then
      echo "error: codex command not found; install or activate Codex before running code:cc" >&2
      exit 1
    fi

    if ! command -v claude >/dev/null 2>&1; then
      echo "error: claude command not found; install or activate Claude Code before running code:cc" >&2
      exit 1
    fi

    if [[ ! -d demo ]]; then
      echo "error: demo/ directory not found in $(pwd) — required for direct coding-agent mode" >&2
      echo "       (the agent launches from demo/ so the project CLAUDE.md does not auto-load)" >&2
      exit 1
    fi

    cleanup() {
      set +e
      just mcp::down
      set -e
    }
    trap cleanup EXIT INT TERM

    mcp_url="$(just mcp::up "{{scene}}" "{{host}}" "{{port}}")"

    # Switch CWD to demo/ for the agent launch. demo/ is intentionally empty
    # (no CLAUDE.md / AGENTS.md) so the agent's only operating doc is
    # ../skills/ai2thor-navigator/SKILL.md. The project-level CLAUDE.md is
    # development guidance for the repo, not robot control — loading it
    # would mis-route the agent. See demo/README.md for the design.
    echo "" >&2
    echo "==> Switching CWD to demo/ — suppresses project CLAUDE.md / AGENTS.md auto-load." >&2
    echo "    The agent will rely on ../skills/ai2thor-navigator/SKILL.md as its operating doc." >&2
    echo "    (See demo/README.md for the design intent.)" >&2
    echo "" >&2
    cd demo

    codex mcp remove roboclaws >/dev/null 2>&1 || true
    codex mcp add roboclaws --url "$mcp_url"
    claude mcp remove roboclaws >/dev/null 2>&1 || true
    claude mcp add --transport http roboclaws "$mcp_url"

    echo "==> launching Claude Code with full permissions (cwd=$(pwd))" >&2
    if [[ "$claude_profile_summary" != "system defaults" ]]; then
      echo "==> Claude Code provider for this run: ${claude_profile_summary}" >&2
    fi
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> Paste the kickoff prompt printed above as your first message." >&2
    claude_command=(claude "${claude_model_args[@]}" {{claude_full_permission_args}})
    if [[ "${#claude_env_args[@]}" -gt 0 ]]; then
      (
        for entry in "${claude_env_args[@]}"; do
          export "$entry"
        done
        "${claude_command[@]}"
      )
    else
      "${claude_command[@]}"
    fi

# Open the live snapshot viewer for the most recent run (output/runs/).
# Polls latest.{fpv,map,chase}.png written by every observe() call.
# Defaults to port 8787; pass port=NNNN to override.
view run_dir="" port="8787" agent="0":
    #!/usr/bin/env bash
    args=(--agent-id "{{agent}}" --port "{{port}}")
    [[ -n "{{run_dir}}" ]] && args+=(--run-dir "{{run_dir}}")
    exec .venv/bin/python scripts/openclaw/view-snapshots.py "${args[@]}"

codex scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    source scripts/dev/coding_agent_env.sh
    roboclaws_load_dotenv .env
    codex_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL)"
    codex_model_args=()
    roboclaws_codex_provider_args codex_model_args

    if ! command -v codex >/dev/null 2>&1; then
      echo "error: codex command not found; install or activate Codex before running code:codex" >&2
      exit 1
    fi

    if [[ ! -d demo ]]; then
      echo "error: demo/ directory not found in $(pwd) — required for direct coding-agent mode" >&2
      echo "       (the agent launches from demo/ so the project CLAUDE.md does not auto-load)" >&2
      exit 1
    fi

    cleanup() {
      set +e
      just mcp::down
      set -e
    }
    trap cleanup EXIT INT TERM

    mcp_url="$(just mcp::up "{{scene}}" "{{host}}" "{{port}}")"

    # Switch CWD to demo/ for the agent launch. See `cc` recipe above for
    # the rationale — demo/ is intentionally empty so the agent's only
    # operating doc is ../skills/ai2thor-navigator/SKILL.md.
    echo "" >&2
    echo "==> Switching CWD to demo/ — suppresses project CLAUDE.md / AGENTS.md auto-load." >&2
    echo "    The agent will rely on ../skills/ai2thor-navigator/SKILL.md as its operating doc." >&2
    echo "    (See demo/README.md for the design intent.)" >&2
    echo "" >&2
    cd demo

    codex mcp remove roboclaws >/dev/null 2>&1 || true
    codex mcp add roboclaws --url "$mcp_url"
    echo "==> launching Codex with full permissions (cwd=$(pwd))" >&2
    if [[ "$codex_profile_summary" != "system defaults" ]]; then
      echo "==> Codex provider for this run: ${codex_profile_summary}" >&2
    fi
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> Paste the kickoff prompt printed above as your first message." >&2
    codex "${codex_model_args[@]}" {{codex_full_permission_args}}

# Cheap live check for a repo-local Codex OpenAI-compatible provider profile.
# This intentionally refuses `system` so a misspelled profile does not silently
# validate the user's machine default.
codex-provider-smoke prompt="Reply exactly with: roboclaws-codex-provider-ok":
    #!/usr/bin/env bash
    set -euo pipefail

    source scripts/dev/coding_agent_env.sh
    roboclaws_load_dotenv .env
    codex_provider="$(roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER)"
    if [[ "$codex_provider" == "system" ]]; then
      echo "error: no Codex provider profile selected; set ROBOCLAWS_CODEX_PROVIDER=kimi-openai or mimo-openai in .env" >&2
      exit 1
    fi
    codex_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL)"
    codex_model_args=()
    roboclaws_codex_provider_args codex_model_args

    if ! command -v codex >/dev/null 2>&1; then
      echo "error: codex command not found; install or activate Codex before running code:codex-provider-smoke" >&2
      exit 1
    fi

    smoke_dir=".tmp/codex-provider-smoke"
    mkdir -p "$smoke_dir"
    last_message="${smoke_dir}/last-message.md"

    echo "==> Codex provider smoke: ${codex_profile_summary}" >&2
    if ! codex exec \
      --json \
      --sandbox read-only \
      --ephemeral \
      --ignore-user-config \
      --output-last-message "$last_message" \
      "${codex_model_args[@]}" \
      --cd "$PWD" \
      "{{prompt}}"; then
      echo "error: Codex provider smoke failed for ${codex_provider}" >&2
      echo "       The selected endpoint may not support the configured Codex wire API; no system-provider fallback was used." >&2
      exit 1
    fi
