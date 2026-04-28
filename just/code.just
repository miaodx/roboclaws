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

    echo "==> launching Claude Code (cwd=$(pwd))" >&2
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> Paste the kickoff prompt printed above as your first message." >&2
    claude

codex scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

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
    echo "==> launching Codex (cwd=$(pwd))" >&2
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> Paste the kickoff prompt printed above as your first message." >&2
    codex
