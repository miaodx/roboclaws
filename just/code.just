# Coding-agent MCP launcher for Codex/Claude Code.
#
# Preferred one-command entrypoints:
# - just code::cc
# - just code::codex
# - just code::mcp_up
# - just code::mcp_down (idempotent teardown)

set working-directory := '..'

default:
    @just --list code

server_dir := ".tmp/roboclaws-code-mcp"
server_pid_file := ".tmp/roboclaws-code-mcp/server.pid"
server_log_file := ".tmp/roboclaws-code-mcp/server.log"
server_url_file := ".tmp/roboclaws-code-mcp/server.url"

_wait_for_port host port:
    #!/usr/bin/env bash
    set -euo pipefail

    for _ in {1..80}; do
      if (echo > /dev/tcp/"{{host}}"/"{{port}}") >/dev/null 2>&1; then
        echo "==> MCP server is listening on {{host}}:{{port}}" >&2
        exit 0
      fi
      sleep 0.25
    done
    echo "error: MCP endpoint not ready at {{host}}:{{port}}" >&2
    exit 1

mcp_up scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    if ! command -v python >/dev/null 2>&1; then
      echo "error: python command not found" >&2
      exit 1
    fi

    mkdir -p "{{server_dir}}"

    if [[ -f "{{server_pid_file}}" ]]; then
      existing_pid="$(cat "{{server_pid_file}}" || true)"
      if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
        mcp_url="http://{{host}}:{{port}}/mcp"
        printf '%s\n' "$mcp_url" > "{{server_url_file}}"
        echo "$mcp_url"
        exit 0
      fi
    fi

    echo "==> starting roboclaws MCP server (scene={{scene}}, host={{host}}, port={{port}})" >&2
    python examples/coding_agent_nav_server.py --scene "{{scene}}" --host "{{host}}" --port "{{port}}" \
      > "{{server_log_file}}" 2>&1 &
    SERVER_PID=$!
    printf '%s\n' "$SERVER_PID" > "{{server_pid_file}}"

    just code::_wait_for_port "{{host}}" "{{port}}" || {
      echo "error: failed to start MCP server" >&2
      cat "{{server_log_file}}" >&2
      exit 1
    }

    mcp_url="http://{{host}}:{{port}}/mcp"
    printf '%s\n' "$mcp_url" > "{{server_url_file}}"
    echo "$mcp_url"

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
      codex mcp remove roboclaws >/dev/null 2>&1 || true
      claude mcp remove roboclaws >/dev/null 2>&1 || true
      just code::mcp_down
      set -e
    }
    trap cleanup EXIT INT TERM

    mcp_url="$(just code::mcp_up "{{scene}}" "{{host}}" "{{port}}")"
    codex mcp remove roboclaws >/dev/null 2>&1 || true
    codex mcp add roboclaws --url "$mcp_url"
    claude mcp remove roboclaws >/dev/null 2>&1 || true
    claude mcp add --transport http roboclaws "$mcp_url"

    echo "==> launching Claude Code with MCP registration" >&2
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> log: {{server_log_file}}" >&2
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
      codex mcp remove roboclaws >/dev/null 2>&1 || true
      just code::mcp_down
      set -e
    }
    trap cleanup EXIT INT TERM

    mcp_url="$(just code::mcp_up "{{scene}}" "{{host}}" "{{port}}")"
    codex mcp remove roboclaws >/dev/null 2>&1 || true
    codex mcp add roboclaws --url "$mcp_url"
    echo "==> launching Codex with MCP registration" >&2
    echo "==> MCP URL: $mcp_url" >&2
    echo "==> log: {{server_log_file}}" >&2
    codex

mcp_down:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "==> cleaning up roboclaws MCP registrations" >&2
    codex mcp remove roboclaws >/dev/null 2>&1 || true
    claude mcp remove roboclaws >/dev/null 2>&1 || true

    if [[ -f "{{server_pid_file}}" ]]; then
      server_pid="$(cat "{{server_pid_file}}" || true)"
      if [[ "$server_pid" =~ ^[0-9]+$ ]] && kill -0 "$server_pid" 2>/dev/null; then
        echo "==> stopping tracked roboclaws MCP server (pid=$server_pid)" >&2
        if ! kill "$server_pid" 2>/dev/null; then
          if kill -0 "$server_pid" 2>/dev/null; then
            owner="$(ps -p "$server_pid" -o user= 2>/dev/null | tr -d ' ' || echo '?')"
            echo "==> ERROR: cannot signal tracked pid=$server_pid (owner=$owner) — permission denied; try \`sudo kill $server_pid\`" >&2
          fi
        fi
        wait "$server_pid" 2>/dev/null || true
      else
        echo "==> no live tracked roboclaws MCP server for pid=$server_pid" >&2
      fi
      rm -f "{{server_pid_file}}"
    else
      echo "==> no tracked roboclaws MCP pid file found" >&2
    fi

    # Backstop: reap any orphan roboclaws MCP server processes that lost their
    # PID file (crash, disk wipe, manual rm). Project policy: only one
    # roboclaws MCP per machine, so name-based reaping is safe.
    if command -v pgrep >/dev/null 2>&1; then
      orphan_pids="$(pgrep -f 'python[^ ]*[ ].*coding_agent_nav_server\.py' || true)"
      if [[ -n "$orphan_pids" ]]; then
        while IFS= read -r orphan_pid; do
          [[ -z "$orphan_pid" ]] && continue
          if kill "$orphan_pid" 2>/dev/null; then
            echo "==> reaped orphan coding_agent_nav_server.py (pid=$orphan_pid)" >&2
          elif kill -0 "$orphan_pid" 2>/dev/null; then
            orphan_owner="$(ps -p "$orphan_pid" -o user= 2>/dev/null | tr -d ' ' || echo '?')"
            echo "==> ERROR: cannot kill orphan pid=$orphan_pid (owner=$orphan_owner) — permission denied; try \`sudo kill $orphan_pid\`" >&2
          fi
        done <<< "$orphan_pids"
      fi
    fi

    rm -f "{{server_log_file}}" "{{server_url_file}}"
