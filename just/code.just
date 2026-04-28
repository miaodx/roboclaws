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

cc scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    if ! command -v codex >/dev/null 2>&1; then
      echo "error: codex command not found; install or activate Codex before running code:cc" >&2
      exit 1
    fi

    if ! command -v claude >/dev/null 2>&1; then
      echo "error: claude command not found; install or activate Claude Code before running code:cc" >&2
      exit 1
    fi

    cleanup() {
      set +e
      just mcp::down
      set -e
    }
    trap cleanup EXIT INT TERM

    mcp_url="$(just mcp::up "{{scene}}" "{{host}}" "{{port}}")"
    codex mcp remove roboclaws >/dev/null 2>&1 || true
    codex mcp add roboclaws --url "$mcp_url"
    claude mcp remove roboclaws >/dev/null 2>&1 || true
    claude mcp add --transport http roboclaws "$mcp_url"

    echo "==> launching Claude Code with MCP registration" >&2
    echo "==> MCP URL: $mcp_url" >&2
    claude

codex scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    if ! command -v codex >/dev/null 2>&1; then
      echo "error: codex command not found; install or activate Codex before running code:codex" >&2
      exit 1
    fi

    cleanup() {
      set +e
      just mcp::down
      set -e
    }
    trap cleanup EXIT INT TERM

    mcp_url="$(just mcp::up "{{scene}}" "{{host}}" "{{port}}")"
    codex mcp remove roboclaws >/dev/null 2>&1 || true
    codex mcp add roboclaws --url "$mcp_url"
    echo "==> launching Codex with MCP registration" >&2
    echo "==> MCP URL: $mcp_url" >&2
    codex
