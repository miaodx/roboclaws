# Coding-agent MCP launcher for Codex/Claude Code.
#
# Preferred one-command entrypoints:
# - just code::cc
# - just code::codex
# - just code::cleanup (idempotent teardown)

set working-directory := '..'

default:
    @just --list code

server_dir := ".tmp/roboclaws-code-mcp"
server_pid_file := ".tmp/roboclaws-code-mcp/server.pid"
server_log_file := ".tmp/roboclaws-code-mcp/server.log"

_wait_for_port host port:
    #!/usr/bin/env bash
    set -euo pipefail

    for _ in {1..80}; do
      if (echo > /dev/tcp/"{{host}}"/"{{port}}") >/dev/null 2>&1; then
        echo "==> MCP server is listening on {{host}}:{{port}}"
        exit 0
      fi
      sleep 0.25
    done
    echo "error: MCP endpoint not ready at {{host}}:{{port}}" >&2
    exit 1

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

    if ! command -v python >/dev/null 2>&1; then
      echo "error: python command not found" >&2
      exit 1
    fi

    mkdir -p "{{server_dir}}"
    cleanup() {
      set +e
      if [[ -n "${SERVER_PID:-}" ]]; then
        if kill -0 "$SERVER_PID" 2>/dev/null; then
          echo "==> stopping roboclaws MCP server (pid=$SERVER_PID)"
          kill "$SERVER_PID" || true
          wait "$SERVER_PID" 2>/dev/null || true
        fi
      fi
      codex mcp remove roboclaws || true
      claude mcp remove roboclaws || true
      rm -f "{{server_pid_file}}"
      set -e
    }
    trap cleanup EXIT INT TERM

    echo "==> starting roboclaws MCP server (scene={{scene}}, host={{host}}, port={{port}})"
    python examples/coding_agent_nav_server.py --scene "{{scene}}" --host "{{host}}" --port "{{port}}" \
      > "{{server_log_file}}" 2>&1 &
    SERVER_PID=$!
    printf '%s\n' "$SERVER_PID" > "{{server_pid_file}}"

    just code::_wait_for_port host="{{host}}" port="{{port}}" || {
      echo "error: failed to start MCP server" >&2
      cat "{{server_log_file}}" >&2
      exit 1
    }

    mcp_url="http://{{host}}:{{port}}/mcp"
    codex mcp remove roboclaws || true
    codex mcp add roboclaws --url "$mcp_url"
    claude mcp remove roboclaws || true
    claude mcp add --transport http roboclaws "$mcp_url"

    echo "==> launching Claude Code with MCP registration"
    echo "==> MCP URL: $mcp_url"
    echo "==> log: {{server_log_file}}"
    claude

codex scene="FloorPlan201" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail

    if ! command -v codex >/dev/null 2>&1; then
      echo "error: codex command not found; install or activate Codex before running code:codex" >&2
      exit 1
    fi

    if ! command -v python >/dev/null 2>&1; then
      echo "error: python command not found" >&2
      exit 1
    fi

    mkdir -p "{{server_dir}}"
    cleanup() {
      set +e
      if [[ -n "${SERVER_PID:-}" ]]; then
        if kill -0 "$SERVER_PID" 2>/dev/null; then
          echo "==> stopping roboclaws MCP server (pid=$SERVER_PID)"
          kill "$SERVER_PID" || true
          wait "$SERVER_PID" 2>/dev/null || true
        fi
      fi
      codex mcp remove roboclaws || true
      rm -f "{{server_pid_file}}"
      set -e
    }
    trap cleanup EXIT INT TERM

    echo "==> starting roboclaws MCP server (scene={{scene}}, host={{host}}, port={{port}})"
    python examples/coding_agent_nav_server.py --scene "{{scene}}" --host "{{host}}" --port "{{port}}" \
      > "{{server_log_file}}" 2>&1 &
    SERVER_PID=$!
    printf '%s\n' "$SERVER_PID" > "{{server_pid_file}}"

    just code::_wait_for_port host="{{host}}" port="{{port}}" || {
      echo "error: failed to start MCP server" >&2
      cat "{{server_log_file}}" >&2
      exit 1
    }

    mcp_url="http://{{host}}:{{port}}/mcp"
    codex mcp remove roboclaws || true
    codex mcp add roboclaws --url "$mcp_url"
    echo "==> launching Codex with MCP registration"
    echo "==> MCP URL: $mcp_url"
    echo "==> log: {{server_log_file}}"
    codex

cleanup:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "==> cleaning up roboclaws MCP registrations"
    codex mcp remove roboclaws || true
    claude mcp remove roboclaws || true

    if [[ -f "{{server_pid_file}}" ]]; then
      server_pid="$(cat "{{server_pid_file}}")"
      if [[ "$server_pid" =~ ^[0-9]+$ ]] && kill -0 "$server_pid" 2>/dev/null; then
        echo "==> stopping tracked roboclaws MCP server (pid=$server_pid)"
        kill "$server_pid" || true
      else
        echo "==> no live tracked roboclaws MCP server for pid=$server_pid"
      fi
      rm -f "{{server_pid_file}}"
    else
      echo "==> no tracked roboclaws MCP pid file found"
    fi
