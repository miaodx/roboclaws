# Retired Docker coding-agent MCP launcher for manual debugging.
#
# Preferred entrypoints:
# - just code::docker-build              build the pinned coding-agent image
# - just code::docker-install-wrappers   install wrapper shims for manual debugging
# - just code::codex-provider-smoke      check the repo-local Codex provider route

set working-directory := '..'

default:
    @just --list code

# Current product demos do not launch Codex or Claude Code. These arguments are
# retained only for explicit manual debugging through the retired Docker helper.
# Bare host CLI launches are unsupported unless a human explicitly asks for
# system-CLI debugging.
codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"
claude_full_permission_args := "--dangerously-skip-permissions --permission-mode bypassPermissions"

# Build the pinned Codex / Claude Code Docker image used by manual debugging.
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

# Cheap live check for the repo-local Codex Responses-compatible provider profile.
# This intentionally refuses `system` so missing repo-local keys do not silently
# validate the user's machine default.
codex-provider-smoke prompt="Reply exactly with: roboclaws-codex-provider-ok":
    #!/usr/bin/env bash
    set -euo pipefail

    source scripts/dev/coding_agent_env.sh
    roboclaws_load_dotenv .env
    codex_provider="$(roboclaws_code_agent_provider ROBOCLAWS_PROVIDER_PROFILE codex-router-responses)"
    if [[ "$codex_provider" == "system" ]]; then
      echo "error: unsupported system Codex provider; codex-router-responses is the default and requires CODEX_BASE_URL plus CODEX_API_KEY, or set ROBOCLAWS_PROVIDER_PROFILE=mimo-mify-responses with XM_LLM_API_KEY or minimax-responses with MM_API_KEY" >&2
      exit 1
    fi
    roboclaws_assert_codex_network_allowed "Codex provider smoke"
    codex_profile_summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_PROVIDER_PROFILE ROBOCLAWS_CODEX_MODEL codex-router-responses)"
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
