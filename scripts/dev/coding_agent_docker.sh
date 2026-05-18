#!/usr/bin/env bash
# Build and run the pinned Codex / Claude Code CLI image.

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

# shellcheck disable=SC1091
source "${script_dir}/coding_agent_toolchain.env"

dockerfile="${ROBOCLAWS_CODE_AGENT_DOCKERFILE:-Dockerfile.coding-agents}"
image="${ROBOCLAWS_CODE_AGENT_IMAGE}"

usage() {
  cat <<'USAGE' >&2
usage: scripts/dev/coding_agent_docker.sh <command> [args...]

commands:
  build                    Build the pinned coding-agent image.
  ensure                   Build the image only when it is missing locally.
  run <codex|claude> ...   Run a pinned CLI in Docker.
  versions                 Print pinned Codex and Claude Code versions.
  install-wrappers <dir>   Write codex/claude wrapper shims into <dir>.
USAGE
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker not found in PATH" >&2
    exit 1
  fi
}

build_image() {
  require_docker
  docker build \
    -f "${repo_root}/${dockerfile}" \
    --build-arg "ROBOCLAWS_NODE_IMAGE=${ROBOCLAWS_CODE_AGENT_NODE_IMAGE}" \
    --build-arg "CODEX_NPM_PACKAGE=${ROBOCLAWS_CODEX_NPM_PACKAGE}" \
    --build-arg "CLAUDE_CODE_NPM_PACKAGE=${ROBOCLAWS_CLAUDE_CODE_NPM_PACKAGE}" \
    -t "${image}" \
    "${repo_root}"
}

ensure_image() {
  require_docker
  if ! docker image inspect "${image}" >/dev/null 2>&1; then
    build_image
  fi
}

prepare_nav_workspace() {
  local workspace_dir="${ROBOCLAWS_CODE_AGENT_DOCKER_NAV_WORKSPACE:-${repo_root}/.tmp/coding-agent-nav-workspace}"
  mkdir -p "${workspace_dir}/demo" "${workspace_dir}/skills"
  if [[ -f "${repo_root}/demo/README.md" ]]; then
    cp "${repo_root}/demo/README.md" "${workspace_dir}/demo/README.md"
  fi
  rm -f "${workspace_dir}/AGENTS.md" "${workspace_dir}/CLAUDE.md"
  printf '%s\n' "${workspace_dir}"
}

pass_env_if_set() {
  local -n out_args="$1"
  local name
  shift
  for name in "$@"; do
    if [[ -n "${!name+x}" ]]; then
      out_args+=(-e "${name}")
    fi
  done
}

run_cli() {
  local binary="${1:-}"
  if [[ -z "${binary}" ]]; then
    usage
    exit 2
  fi
  shift
  case "${binary}" in
    codex|claude)
      ;;
    *)
      echo "error: unsupported pinned CLI '${binary}' (expected codex or claude)" >&2
      exit 2
      ;;
  esac

  ensure_image

  local home_dir="${ROBOCLAWS_CODE_AGENT_DOCKER_HOME:-${repo_root}/.tmp/coding-agent-docker-home}"
  mkdir -p "${home_dir}"

  local cwd="${PWD}"
  local network="${ROBOCLAWS_CODE_AGENT_DOCKER_NETWORK:-host}"
  local user_mode="${ROBOCLAWS_CODE_AGENT_DOCKER_USER:-host}"
  local add_host="${ROBOCLAWS_CODE_AGENT_DOCKER_ADD_HOST:-1}"
  local use_host_codex_home="${ROBOCLAWS_CODE_AGENT_DOCKER_USE_HOST_CODEX_HOME:-0}"
  local host_codex_home="${ROBOCLAWS_CODE_AGENT_DOCKER_HOST_CODEX_HOME:-${CODEX_HOME:-${HOME}/.codex}}"
  local isolate_nav_workspace="${ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_NAV_WORKSPACE:-0}"
  local container_workdir="${cwd}"
  local workspace_mount_args=()

  if [[ "${isolate_nav_workspace}" == "1" ]]; then
    if [[ "${cwd}" != "${repo_root}" && "${cwd}" != "${repo_root}/"* ]]; then
      echo "error: isolated nav workspace requires cwd under ${repo_root}; got ${cwd}" >&2
      exit 1
    fi
    local nav_workspace
    nav_workspace="$(prepare_nav_workspace)"
    local rel_cwd="${cwd#${repo_root}}"
    rel_cwd="${rel_cwd#/}"
    container_workdir="/workspace"
    if [[ -n "${rel_cwd}" ]]; then
      container_workdir="/workspace/${rel_cwd}"
    fi
    workspace_mount_args=(
      -v "${nav_workspace}:/workspace"
      -v "${repo_root}/skills/ai2thor-navigator:/workspace/skills/ai2thor-navigator:ro"
    )
  else
    workspace_mount_args=(-v "${repo_root}:${repo_root}")
  fi

  local docker_args=(run --rm)
  if [[ -t 0 && -t 1 ]]; then
    docker_args+=(-it)
  fi
  if [[ -n "${network}" ]]; then
    docker_args+=(--network "${network}")
  fi
  if [[ "${add_host}" == "1" ]]; then
    docker_args+=(--add-host=host.docker.internal:host-gateway)
  fi
  if [[ "${user_mode}" == "host" ]]; then
    docker_args+=(--user "$(id -u):$(id -g)")
  elif [[ "${user_mode}" != "root" ]]; then
    docker_args+=(--user "${user_mode}")
  fi

  docker_args+=(
    -e "HOME=/home/agent"
    -e "TERM=${TERM:-xterm-256color}"
    -v "${home_dir}:/home/agent"
    -w "${container_workdir}"
    "${workspace_mount_args[@]}"
  )
  if [[ "${use_host_codex_home}" == "1" ]]; then
    if [[ ! -d "${host_codex_home}" ]]; then
      echo "error: host Codex home not found: ${host_codex_home}" >&2
      exit 1
    fi
    docker_args+=(
      -e "CODEX_HOME=/home/agent/.codex"
      -v "${host_codex_home}:/home/agent/.codex"
    )
  fi
  pass_env_if_set docker_args \
    ANTHROPIC_API_KEY \
    ANTHROPIC_BASE_URL \
    ANTHROPIC_AUTH_TOKEN \
    CLAUDE_CODE_SIMPLE \
    CLAUDE_CODE_USE_BEDROCK \
    CLAUDE_CODE_USE_VERTEX \
    OPENAI_API_KEY \
    KIMI_API_KEY \
    MIMO_TP_KEY \
    ROBOCLAWS_CLAUDE_PROVIDER \
    ROBOCLAWS_CLAUDE_MODEL \
    ROBOCLAWS_CODEX_PROVIDER \
    ROBOCLAWS_CODEX_MODEL \
    ROBOCLAWS_CODE_AGENT_PROVIDER \
    ROBOCLAWS_CODE_AGENT_MODEL \
    MODEL

  exec docker "${docker_args[@]}" "${image}" "${binary}" "$@"
}

install_wrappers() {
  local shim_dir="${1:-}"
  if [[ -z "${shim_dir}" ]]; then
    usage
    exit 2
  fi
  mkdir -p "${shim_dir}"

  local binary
  for binary in codex claude; do
    cat >"${shim_dir}/${binary}" <<SHIM
#!/usr/bin/env bash
set -euo pipefail
export ROBOCLAWS_CODE_AGENT_IMAGE=${image@Q}
exec ${repo_root@Q}/scripts/dev/coding_agent_docker.sh run ${binary@Q} "\$@"
SHIM
    chmod +x "${shim_dir}/${binary}"
  done
  echo "${shim_dir}"
}

command="${1:-}"
case "${command}" in
  build)
    build_image
    ;;
  ensure)
    ensure_image
    ;;
  run)
    shift
    run_cli "$@"
    ;;
  versions)
    "${BASH_SOURCE[0]}" run codex --version
    "${BASH_SOURCE[0]}" run claude --version
    ;;
  install-wrappers)
    shift
    install_wrappers "$@"
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "error: unknown command '${command}'" >&2
    usage
    exit 2
    ;;
esac
