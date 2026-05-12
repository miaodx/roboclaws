#!/usr/bin/env bash
# Shared helpers for Codex / Claude Code demo launchers.

roboclaws_load_dotenv() {
  local env_file="${1:-.env}"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

roboclaws_code_agent_model() {
  local primary_var="$1"
  local model="${!primary_var:-}"
  if [[ -z "$model" ]]; then
    model="${ROBOCLAWS_CODE_AGENT_MODEL:-}"
  fi
  printf '%s\n' "$model"
}

roboclaws_code_agent_model_args() {
  local -n out_args="$1"
  local primary_var="$2"
  local model

  out_args=()
  model="$(roboclaws_code_agent_model "$primary_var")"
  if [[ -n "$model" ]]; then
    out_args=(--model "$model")
  fi
}
