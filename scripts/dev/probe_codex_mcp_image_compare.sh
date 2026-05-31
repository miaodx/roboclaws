#!/usr/bin/env bash
# Cross-test Codex provider handling of images returned by MCP tools.

set -euo pipefail

usage() {
  cat <<'USAGE' >&2
usage: scripts/dev/probe_codex_mcp_image_compare.sh <fpv_png[,fpv_png...]> [both|mify|codex-env] [output_dir]

Environment:
  PORT                  MCP server port (default: 18891)
  HOST                  MCP server host (default: 127.0.0.1)
  CODEX_TIMEOUT_S       Timeout per provider run (default: 420)
  ROBOCLAWS_CODEX_MODEL Optional provider model override

The script uses the repo's Docker-backed Codex launcher and provider helpers.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
  exit $([[ $# -lt 1 ]] && echo 2 || echo 0)
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

fpv_arg="$1"
provider_filter="${2:-both}"
output_root="${3:-.tmp/codex-vision-smoke/$(date +%Y%m%d_%H%M%S)-mcp-image-compare}"
host="${HOST:-127.0.0.1}"
port="${PORT:-18891}"
timeout_s="${CODEX_TIMEOUT_S:-420}"

case "$provider_filter" in
  both|mify|codex-env)
    ;;
  *)
    echo "error: unsupported provider filter '$provider_filter' (expected both|mify|codex-env)" >&2
    exit 2
    ;;
esac

IFS=',' read -r -a fpv_paths <<<"$fpv_arg"
if [[ "${#fpv_paths[@]}" -lt 1 ]]; then
  echo "error: at least one FPV image is required" >&2
  exit 2
fi
for fpv_path in "${fpv_paths[@]}"; do
  if [[ ! -f "$fpv_path" ]]; then
    echo "error: FPV image not found: $fpv_path" >&2
    exit 2
  fi
done

# shellcheck disable=SC1091
source scripts/dev/coding_agent_env.sh
roboclaws_load_dotenv .env

scripts/dev/coding_agent_docker.sh ensure
mkdir -p "$output_root"

server_args=(--host "$host" --port "$port")
for fpv_path in "${fpv_paths[@]}"; do
  server_args+=(--fpv-path "$fpv_path")
done

.venv/bin/python scripts/dev/probe_codex_mcp_image_server.py \
  "${server_args[@]}" \
  >"$output_root/server.log" \
  2>&1 &
server_pid=$!

cleanup() {
  set +e
  kill "$server_pid" >/dev/null 2>&1 || true
  scripts/dev/coding_agent_docker.sh run codex mcp remove vision_smoke >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 50); do
  if python3 - <<PY >/dev/null 2>&1
import socket

sock = socket.create_connection(("$host", int("$port")), timeout=0.2)
sock.close()
PY
  then
    break
  fi
  sleep 0.1
done

if [[ "${#fpv_paths[@]}" -eq 1 ]]; then
  prompt='This is a live MCP image transport test. Call synthetic_image_probe first, inspect its returned image. Then call fpv_image_probe second with index=1, inspect its returned image. Output only strict JSON with this shape: {"synthetic_image_received": boolean, "synthetic_objects": [string], "fpv_image_received": boolean, "fpv_visible_cleanup_objects": [string], "fpv_scene_summary": string}. Do not use markdown. Do not guess from tool names; use the returned image contents.'
else
  fpv_count="${#fpv_paths[@]}"
  prompt="This is a live MCP image transport/cache test. Call synthetic_image_probe first and inspect its returned image. Then call fpv_image_probe ${fpv_count} times in order with index=1 through index=${fpv_count}; inspect every returned image separately. Output only strict JSON with this shape: {\"synthetic_image_received\": boolean, \"synthetic_objects\": [string], \"fpv_images\": [{\"index\": number, \"image_received\": boolean, \"visible_cleanup_objects\": [string], \"scene_summary\": string}]}. Do not use markdown. Do not reuse observations across indices. Do not guess from file names, hashes, or tool names; use each returned image contents."
fi

run_provider() {
  local provider="$1"
  export ROBOCLAWS_CODEX_PROVIDER="$provider"

  roboclaws_assert_codex_network_allowed "Codex MCP image compare ${provider}"
  local codex_model_args=()
  roboclaws_codex_provider_args codex_model_args
  local summary
  summary="$(roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL)"

  local out_dir="$output_root/$provider"
  mkdir -p "$out_dir"
  {
    printf 'profile=%s\n' "$summary"
    printf 'mcp_url=http://%s:%s/mcp\n' "$host" "$port"
    printf 'fpv_count=%s\n' "${#fpv_paths[@]}"
    local index=1
    for fpv_path in "${fpv_paths[@]}"; do
      printf 'fpv_path_%s=%s\n' "$index" "$fpv_path"
      sha256sum "$fpv_path"
      index=$((index + 1))
    done
  } >"$out_dir/run-meta.txt"

  scripts/dev/coding_agent_docker.sh run codex mcp remove vision_smoke >/dev/null 2>&1 || true
  scripts/dev/coding_agent_docker.sh run codex mcp add \
    vision_smoke \
    --url "http://$host:$port/mcp" \
    >"$out_dir/mcp-add.log" \
    2>&1

  set +e
  timeout "$timeout_s" scripts/dev/coding_agent_docker.sh run codex exec \
    --json \
    --output-last-message "$out_dir/last-message.md" \
    "${codex_model_args[@]}" \
    --dangerously-bypass-approvals-and-sandbox \
    --cd "$repo_root" \
    "$prompt" \
    </dev/null \
    >"$out_dir/events.jsonl" \
    2>"$out_dir/stderr.log"
  local status=$?
  set -e

  {
    printf 'exit_code=%s\n' "$status"
    printf 'timeout_s=%s\n' "$timeout_s"
    printf 'out_dir=%s\n' "$out_dir"
  } >"$out_dir/result.txt"

  printf '\n[%s last-message]\n' "$provider"
  sed -n '1,160p' "$out_dir/last-message.md" 2>/dev/null || true
  printf '\n'
}

case "$provider_filter" in
  both)
    run_provider mify
    run_provider codex-env
    ;;
  *)
    run_provider "$provider_filter"
    ;;
esac

printf 'output_root=%s\n' "$output_root"
