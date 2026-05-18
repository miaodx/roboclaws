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

# Supported local demos intentionally run coding agents with full permissions.
# Any new just recipe that launches Codex or Claude Code should call these
# recipes or scripts/dev/coding_agent_docker.sh. Bare host CLI launches are
# unsupported unless a human explicitly asks for system-CLI debugging.
codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"
claude_full_permission_args := "--dangerously-skip-permissions --permission-mode bypassPermissions"

# Build the pinned Codex / Claude Code Docker image used by supported
# coding-agent runs.
docker-build:
    @scripts/dev/coding_agent_docker.sh build

# Print versions from the pinned Docker image.
docker-versions:
    @scripts/dev/coding_agent_docker.sh versions

# Install codex/claude wrapper shims that route through the pinned Docker image.
# Public recipes call the Docker runner directly; these shims are for manual
# debugging and CI setup where a command path is required.
# Usage:
#   just code::docker-install-wrappers .tmp/coding-agent-bin
docker-install-wrappers shim_dir=".tmp/coding-agent-bin":
    @scripts/dev/coding_agent_docker.sh ensure
    @scripts/dev/coding_agent_docker.sh install-wrappers "{{shim_dir}}"

cc scene="FloorPlan201" host="127.0.0.1" port="18788" task_name="ai2thor-nav" skill_name="ai2thor-navigator" allow_privileged_tools="0":
    #!/usr/bin/env bash
    set -euo pipefail

    repo_root="$PWD"
    source scripts/dev/coding_agent_env.sh
    roboclaws_load_dotenv .env
    claude_provider="$(roboclaws_code_agent_provider ROBOCLAWS_CLAUDE_PROVIDER)"
    claude_model="$(roboclaws_code_agent_model ROBOCLAWS_CLAUDE_MODEL ROBOCLAWS_CLAUDE_PROVIDER)"
    claude_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CLAUDE_PROVIDER ROBOCLAWS_CLAUDE_MODEL)"
    claude_model_args=()
    claude_env_args=()
    roboclaws_claude_provider_args claude_model_args claude_env_args
    task_name="{{task_name}}"
    skill_name="{{skill_name}}"
    skill_name="${skill_name#skills/}"
    skill_name="${skill_name%/}"
    allow_privileged_tools="{{allow_privileged_tools}}"
    skill_path="../skills/${skill_name}/SKILL.md"
    if [[ ! -f "$repo_root/skills/$skill_name/SKILL.md" ]]; then
      echo "error: missing task skill: skills/${skill_name}/SKILL.md" >&2
      exit 1
    fi

    roboclaws_assert_claude_code_network_allowed "Claude Code direct MCP run"

    scripts/dev/coding_agent_docker.sh ensure

    cleanup() {
      set +e
      "$repo_root/scripts/dev/coding_agent_docker.sh" run claude mcp remove roboclaws >/dev/null 2>&1 || true
      just --justfile "$repo_root/justfile" --working-directory "$repo_root" mcp::down
      set -e
    }
    trap cleanup EXIT INT TERM

    roboclaws_code_agent_prepare_mcp_env "$claude_model" "$claude_provider"
    mcp_url="$(just mcp::up "{{scene}}" "{{host}}" "{{port}}" "$allow_privileged_tools" "$skill_path")"

    agent_workspace="${ROBOCLAWS_CODE_AGENT_WORKSPACE:-/tmp/roboclaws-code-${task_name}-{{port}}}"
    agent_task_dir="${agent_workspace}/task"
    mkdir -p "$agent_task_dir" "${agent_workspace}/skills"
    rm -f "$agent_task_dir/AGENTS.md" "$agent_task_dir/CLAUDE.md" \
      "${agent_workspace}/AGENTS.md" "${agent_workspace}/CLAUDE.md"
    find "${agent_workspace}/skills" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    ln -sfn "$repo_root/skills/$skill_name" \
      "${agent_workspace}/skills/$skill_name"
    {
      printf '# Roboclaws %s Agent Workspace\n\n' "$task_name"
      printf 'Read `%s`, then use the roboclaws MCP tools.\n' "$skill_path"
    } >"${agent_task_dir}/README.md"

    echo "" >&2
    echo "==> Switching CWD to isolated task workspace: ${agent_task_dir}" >&2
    echo "    The agent will rely on ${skill_path} as its operating doc." >&2
    echo "" >&2
    cd "$agent_task_dir"
    export ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE:-1}"
    export ROBOCLAWS_CODE_AGENT_DOCKER_TASK="${ROBOCLAWS_CODE_AGENT_DOCKER_TASK:-${task_name}}"
    export ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS="${ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-${skill_name}}"
    export ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE:-${agent_workspace}/docker}"

    docker_claude=("$repo_root/scripts/dev/coding_agent_docker.sh" run claude)
    "${docker_claude[@]}" mcp remove roboclaws >/dev/null 2>&1 || true
    "${docker_claude[@]}" mcp add --transport http roboclaws "$mcp_url"

    echo "==> launching Docker-backed Claude Code with full permissions (cwd=$(pwd))" >&2
    if [[ "$claude_profile_summary" != "system defaults" ]]; then
      echo "==> Claude Code provider for this run: ${claude_profile_summary}" >&2
    fi
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> Paste the kickoff prompt printed above as your first message." >&2
    claude_command=("${docker_claude[@]}" "${claude_model_args[@]}" {{claude_full_permission_args}})
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

codex scene="FloorPlan201" host="127.0.0.1" port="18788" task_name="ai2thor-nav" skill_name="ai2thor-navigator" allow_privileged_tools="0":
    #!/usr/bin/env bash
    set -euo pipefail

    repo_root="$PWD"
    source scripts/dev/coding_agent_env.sh
    roboclaws_load_dotenv .env
    codex_provider="$(roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER)"
    codex_model="$(roboclaws_code_agent_model ROBOCLAWS_CODEX_MODEL ROBOCLAWS_CODEX_PROVIDER)"
    codex_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL)"
    codex_model_args=()
    roboclaws_codex_provider_args codex_model_args
    task_name="{{task_name}}"
    skill_name="{{skill_name}}"
    skill_name="${skill_name#skills/}"
    skill_name="${skill_name%/}"
    allow_privileged_tools="{{allow_privileged_tools}}"
    skill_path="../skills/${skill_name}/SKILL.md"
    if [[ ! -f "$repo_root/skills/$skill_name/SKILL.md" ]]; then
      echo "error: missing task skill: skills/${skill_name}/SKILL.md" >&2
      exit 1
    fi

    roboclaws_assert_codex_network_allowed "Codex direct MCP run"

    scripts/dev/coding_agent_docker.sh ensure

    cleanup() {
      set +e
      "$repo_root/scripts/dev/coding_agent_docker.sh" run codex mcp remove roboclaws >/dev/null 2>&1 || true
      just --justfile "$repo_root/justfile" --working-directory "$repo_root" mcp::down
      set -e
    }
    trap cleanup EXIT INT TERM

    roboclaws_code_agent_prepare_mcp_env "$codex_model" "$codex_provider"
    mcp_url="$(just mcp::up "{{scene}}" "{{host}}" "{{port}}" "$allow_privileged_tools" "$skill_path")"

    agent_workspace="${ROBOCLAWS_CODE_AGENT_WORKSPACE:-/tmp/roboclaws-code-${task_name}-{{port}}}"
    agent_task_dir="${agent_workspace}/task"
    mkdir -p "$agent_task_dir" "${agent_workspace}/skills"
    rm -f "$agent_task_dir/AGENTS.md" "$agent_task_dir/CLAUDE.md" \
      "${agent_workspace}/AGENTS.md" "${agent_workspace}/CLAUDE.md"
    find "${agent_workspace}/skills" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    ln -sfn "$repo_root/skills/$skill_name" \
      "${agent_workspace}/skills/$skill_name"
    {
      printf '# Roboclaws %s Agent Workspace\n\n' "$task_name"
      printf 'Read `%s`, then use the roboclaws MCP tools.\n' "$skill_path"
    } >"${agent_task_dir}/README.md"

    echo "" >&2
    echo "==> Switching CWD to isolated task workspace: ${agent_task_dir}" >&2
    echo "    The agent will rely on ${skill_path} as its operating doc." >&2
    echo "" >&2
    cd "$agent_task_dir"
    export ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE:-1}"
    export ROBOCLAWS_CODE_AGENT_DOCKER_TASK="${ROBOCLAWS_CODE_AGENT_DOCKER_TASK:-${task_name}}"
    export ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS="${ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-${skill_name}}"
    export ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE="${ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE:-${agent_workspace}/docker}"

    docker_codex=("$repo_root/scripts/dev/coding_agent_docker.sh" run codex)
    "${docker_codex[@]}" mcp remove roboclaws >/dev/null 2>&1 || true
    "${docker_codex[@]}" mcp add roboclaws --url "$mcp_url"
    echo "==> launching Docker-backed Codex with full permissions (cwd=$(pwd))" >&2
    if [[ "$codex_profile_summary" != "system defaults" ]]; then
      echo "==> Codex provider for this run: ${codex_profile_summary}" >&2
    fi
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> Paste the kickoff prompt printed above as your first message." >&2
    "${docker_codex[@]}" "${codex_model_args[@]}" {{codex_full_permission_args}}

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

    scripts/dev/coding_agent_docker.sh ensure

    smoke_dir=".tmp/codex-provider-smoke"
    mkdir -p "$smoke_dir"
    last_message="${smoke_dir}/last-message.md"

    echo "==> Docker-backed Codex provider smoke: ${codex_profile_summary}" >&2
    if ! scripts/dev/coding_agent_docker.sh run codex exec \
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
