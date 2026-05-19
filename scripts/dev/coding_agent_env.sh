#!/usr/bin/env bash
# Shared helpers for Codex / Claude Code demo launchers.
#
# Normal users configure only provider keys in the repo-local .env. The
# ROBOCLAWS_* provider/model variables handled in this file are maintainer-only
# escape hatches for tests, CI, and one-off debugging.

roboclaws_load_dotenv() {
  local env_file="${1:-.env}"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

roboclaws_code_agent_provider() {
  local primary_var="$1"
  local provider=""
  if [[ -n "$primary_var" ]]; then
    provider="${!primary_var:-}"
  fi
  if [[ -z "$provider" ]]; then
    provider="${ROBOCLAWS_CODE_AGENT_PROVIDER:-}"
  fi
  if [[ -z "$provider" ]]; then
    case "$primary_var" in
      ROBOCLAWS_CODEX_PROVIDER)
        if [[ -n "${CODEX_BASE_URL:-}" || -n "${CODEX_API_KEY:-}" ]]; then
          provider="codex-env"
        else
          provider="system"
        fi
        ;;
      ROBOCLAWS_CLAUDE_PROVIDER)
        if [[ -n "${MIMO_TP_KEY:-}" ]]; then
          provider="mimo-anthropic"
        elif [[ -n "${KIMI_API_KEY:-}" ]]; then
          provider="kimi-anthropic"
        else
          provider="system"
        fi
        ;;
      *)
        provider="system"
        ;;
    esac
  fi
  printf '%s\n' "$provider"
}

roboclaws_code_agent_profile_default_model() {
  local provider="$1"
  case "$provider" in
    system)
      printf '\n'
      ;;
    codex-env)
      printf 'gpt-5.5\n'
      ;;
    kimi-anthropic)
      printf 'kimi-k2.6\n'
      ;;
    mimo-anthropic)
      printf 'mimo-v2.5-pro\n'
      ;;
    *)
      echo "error: unknown coding-agent provider profile: ${provider}" >&2
      return 2
      ;;
  esac
}

roboclaws_code_agent_profile_base_url() {
  local provider="$1"
  case "$provider" in
    codex-env)
      if [[ -z "${CODEX_BASE_URL:-}" ]]; then
        echo "error: codex-env requires CODEX_BASE_URL; add it to the repo-local .env or export it for this shell" >&2
        return 2
      fi
      printf '%s\n' "${CODEX_BASE_URL}"
      ;;
    kimi-anthropic)
      printf 'https://api.kimi.com/coding/\n'
      ;;
    mimo-anthropic)
      printf 'https://token-plan-cn.xiaomimimo.com/anthropic\n'
      ;;
    system)
      printf '\n'
      ;;
    *)
      echo "error: unknown coding-agent provider profile: ${provider}" >&2
      return 2
      ;;
  esac
}

roboclaws_code_agent_profile_key_env() {
  local provider="$1"
  case "$provider" in
    codex-env)
      printf 'CODEX_API_KEY\n'
      ;;
    kimi-anthropic)
      printf 'KIMI_API_KEY\n'
      ;;
    mimo-anthropic)
      printf 'MIMO_TP_KEY\n'
      ;;
    system)
      printf '\n'
      ;;
    *)
      echo "error: unknown coding-agent provider profile: ${provider}" >&2
      return 2
      ;;
  esac
}

roboclaws_code_agent_profile_wire_api() {
  local provider="$1"
  case "$provider" in
    codex-env)
      printf 'responses\n'
      ;;
    kimi-anthropic|mimo-anthropic)
      printf 'anthropic\n'
      ;;
    system)
      printf '\n'
      ;;
    *)
      echo "error: unknown coding-agent provider profile: ${provider}" >&2
      return 2
      ;;
  esac
}

roboclaws_code_agent_model() {
  local primary_var="$1"
  local provider_var="${2:-}"
  local model="${!primary_var:-}"
  if [[ -z "$model" ]]; then
    model="${ROBOCLAWS_CODE_AGENT_MODEL:-}"
  fi
  if [[ -z "$model" && -n "$provider_var" ]]; then
    local provider
    provider="$(roboclaws_code_agent_provider "$provider_var")" || return
    model="$(roboclaws_code_agent_profile_default_model "$provider")" || return
  fi
  printf '%s\n' "$model"
}

roboclaws_code_agent_model_args() {
  local -n out_args="$1"
  local primary_var="$2"
  local provider_var="${3:-}"
  local model

  out_args=()
  model="$(roboclaws_code_agent_model "$primary_var" "$provider_var")"
  if [[ -n "$model" ]]; then
    out_args=(--model "$model")
  fi
}

roboclaws_code_agent_model_supports_images() {
  local model="${1:-}"
  model="${model##*/}"
  case "$model" in
    mimo-v2.5|mimo-v2.5-pro)
      return 1
      ;;
    *)
      return 0
      ;;
  esac
}

roboclaws_code_agent_prepare_mcp_env() {
  local model="${1:-}"
  local provider="${2:-}"

  if [[ -n "$model" ]]; then
    export MODEL="$model"
  fi

  if [[ -n "$model" ]] && ! roboclaws_code_agent_model_supports_images "$model"; then
    echo "==> model capability guard: ${model} is text-only; MCP observe(auto) will not inline raw images" >&2
    echo "    Use observe_archived for photo evidence, or configure IMAGE_MODEL/ROBOCLAWS_VISION_BRIDGE_MODEL for text-bridge observations." >&2
  fi

  if [[ "$provider" == "kimi-anthropic" ]]; then
    echo "==> Kimi coding profile note: Kimi is image-capable, but long skill context + raw observe images can intermittently return upstream server errors." >&2
    echo "    For batch photo tasks, prefer observe_archived unless visual reasoning is required; scene_objects/goto require privileged-helper opt-in." >&2
  fi
}

roboclaws_code_agent_require_key() {
  local provider="$1"
  local key_env="$2"
  if [[ -z "$key_env" ]]; then
    return 0
  fi
  if [[ -z "${!key_env:-}" ]]; then
    echo "error: ${provider} requires ${key_env}; add it to the repo-local .env or export it for this shell" >&2
    return 2
  fi
}

roboclaws_toml_string() {
  local value="${1//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s"' "$value"
}

roboclaws_codex_provider_args() {
  local -n out_args="$1"
  local provider_var="${2:-ROBOCLAWS_CODEX_PROVIDER}"
  local model_var="${3:-ROBOCLAWS_CODEX_MODEL}"
  local provider model base_url key_env wire_api

  out_args=()
  provider="$(roboclaws_code_agent_provider "$provider_var")" || return
  case "$provider" in
    codex-env)
      ;;
    system)
      echo "error: Codex repo workflows require CODEX_BASE_URL and CODEX_API_KEY; add them to the repo-local .env or export them for this shell" >&2
      return 2
      ;;
    *)
      echo "error: unsupported Codex provider '${provider}'; expected codex-env" >&2
      return 2
      ;;
  esac

  model="$(roboclaws_code_agent_model "$model_var" "$provider_var")" || return
  base_url="$(roboclaws_code_agent_profile_base_url "$provider")" || return
  key_env="$(roboclaws_code_agent_profile_key_env "$provider")" || return
  wire_api="$(roboclaws_code_agent_profile_wire_api "$provider")" || return
  roboclaws_code_agent_require_key "$provider" "$key_env" || return

  out_args=(
    -c "model=$(roboclaws_toml_string "$model")"
    -c "model_provider=$(roboclaws_toml_string "$provider")"
    -c "model_providers.${provider}.name=$(roboclaws_toml_string "$provider")"
    -c "model_providers.${provider}.base_url=$(roboclaws_toml_string "$base_url")"
    -c "model_providers.${provider}.env_key=$(roboclaws_toml_string "$key_env")"
    -c "model_providers.${provider}.wire_api=$(roboclaws_toml_string "$wire_api")"
  )
  roboclaws_codex_transport_args out_args
}

roboclaws_codex_transport_args() {
  local -n _codex_transport_out_args="$1"
  case "${ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS:-0}" in
    1|true|yes)
      _codex_transport_out_args+=(--disable responses_websockets)
      _codex_transport_out_args+=(--disable responses_websockets_v2)
      ;;
  esac
}

roboclaws_claude_provider_args() {
  local model_args_name="$1"
  local env_args_name="$2"
  local provider_var="${3:-ROBOCLAWS_CLAUDE_PROVIDER}"
  local model_var="${4:-ROBOCLAWS_CLAUDE_MODEL}"
  local -n out_model_args="$model_args_name"
  local -n out_env_args="$env_args_name"
  local provider model base_url key_env

  out_model_args=()
  out_env_args=()
  provider="$(roboclaws_code_agent_provider "$provider_var")" || return
  case "$provider" in
    system|kimi-anthropic|mimo-anthropic)
      ;;
    *)
      echo "error: unsupported Claude provider '${provider}'; expected system, kimi-anthropic, or mimo-anthropic" >&2
      return 2
      ;;
  esac

  model="$(roboclaws_code_agent_model "$model_var" "$provider_var")" || return
  if [[ -n "$model" ]]; then
    out_model_args=(--model "$model")
  fi
  if [[ "$provider" == "system" ]]; then
    return 0
  fi

  base_url="$(roboclaws_code_agent_profile_base_url "$provider")" || return
  key_env="$(roboclaws_code_agent_profile_key_env "$provider")" || return
  roboclaws_code_agent_require_key "$provider" "$key_env" || return
  out_env_args=(
    "ANTHROPIC_API_KEY=${!key_env}"
    "ANTHROPIC_BASE_URL=${base_url}"
    "CLAUDE_CODE_SIMPLE=${CLAUDE_CODE_SIMPLE:-1}"
  )
}

roboclaws_assert_claude_code_network_allowed() {
  local label="${1:-Claude Code}"
  local provider
  provider="$(roboclaws_code_agent_provider ROBOCLAWS_CLAUDE_PROVIDER)" || return
  case "$provider" in
    system|kimi-anthropic|mimo-anthropic)
      ;;
    *)
      echo "error: unsupported Claude provider '${provider}'; expected system, kimi-anthropic, or mimo-anthropic" >&2
      return 2
      ;;
  esac

  local rc
  if bash scripts/dev/network_status.sh --is-work-network >/dev/null 2>&1; then
    rc=0
  else
    rc=$?
  fi

  case "$rc" in
    0)
      if [[ "$provider" == "system" ]]; then
        echo "error: work network detected; ${label} is blocked while using system Claude Code provider." >&2
        echo "       Configure MIMO_TP_KEY or KIMI_API_KEY in the repo-local .env, or switch off the work network." >&2
        return 1
      fi
      echo "==> network guard ok: work network with repo-local Claude provider (${provider})" >&2
      ;;
    1)
      echo "==> network guard ok: off work network" >&2
      ;;
    *)
      echo "error: cannot determine network status; curl is required for ${label}." >&2
      return 2
      ;;
  esac
}

roboclaws_assert_codex_network_allowed() {
  local label="${1:-Codex}"
  local provider
  provider="$(roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER)" || return
  case "$provider" in
    system|codex-env)
      ;;
    *)
      echo "error: unsupported Codex provider '${provider}'; expected codex-env" >&2
      return 2
      ;;
  esac

  local rc
  if bash scripts/dev/network_status.sh --is-work-network >/dev/null 2>&1; then
    rc=0
  else
    rc=$?
  fi

  case "$rc" in
    0)
      if [[ "$provider" == "system" ]]; then
        echo "error: work network detected; ${label} is blocked while using system Codex provider." >&2
        echo "       Configure CODEX_BASE_URL and CODEX_API_KEY in the repo-local .env, or switch off the work network." >&2
        return 1
      fi
      echo "==> network guard ok: work network with repo-local Codex provider (${provider})" >&2
      ;;
    1)
      echo "==> network guard ok: off work network" >&2
      ;;
    *)
      echo "error: cannot determine network status; curl is required for ${label}." >&2
      return 2
      ;;
  esac
}

roboclaws_code_agent_profile_summary() {
  local provider_var="$1"
  local model_var="$2"
  local provider model base_url key_env wire_api

  provider="$(roboclaws_code_agent_provider "$provider_var")" || return
  model="$(roboclaws_code_agent_model "$model_var" "$provider_var")" || return
  if [[ "$provider" == "system" ]]; then
    if [[ -n "$model" ]]; then
      printf 'system model=%s\n' "$model"
    else
      printf 'system defaults\n'
    fi
    return 0
  fi

  base_url="$(roboclaws_code_agent_profile_base_url "$provider")" || return
  key_env="$(roboclaws_code_agent_profile_key_env "$provider")" || return
  wire_api="$(roboclaws_code_agent_profile_wire_api "$provider")" || return
  printf '%s model=%s base_url=%s key_env=%s protocol=%s\n' \
    "$provider" "$model" "$base_url" "$key_env" "$wire_api"
}
