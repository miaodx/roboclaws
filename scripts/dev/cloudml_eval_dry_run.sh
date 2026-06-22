#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
executor_root="${ROBOCLAWS_EXECUTOR_ROOT:-/home/mi/executor}"
executor_config_path="${ROBOCLAWS_EXECUTOR_CONFIG_PATH:-profiles/nvs/miaodongxu.yaml}"
date_stamp="${ROBOCLAWS_CLOUDML_DATE:-$(date +%Y%m%d)}"
env_ref="${ROBOCLAWS_EVAL_ENV_REF:-HEAD}"
code_ref="${ROBOCLAWS_EVAL_CODE_REF:-mi/main}"
env_short="$(git -C "$repo_root" rev-parse --short=8 "$env_ref")"
code_commit="${ROBOCLAWS_CLOUDML_CODE_COMMIT:-$(git -C "$repo_root" rev-parse "$code_ref")}"
code_short="$(git -C "$repo_root" rev-parse --short=12 "$code_commit")"
registry_repo="${ROBOCLAWS_EVAL_REGISTRY_REPO:-micr.cloud.mioffice.cn/cc-proxy/miuniverse-staging}"
default_tag="roboclaws-eval-env-${env_short}-code-${code_short}-${date_stamp}"
image_url="${ROBOCLAWS_CLOUDML_IMAGE_URL:-${registry_repo}:${default_tag}}"
suite="${ROBOCLAWS_CLOUDML_SUITE:-smoke_regression}"
budget="${ROBOCLAWS_CLOUDML_BUDGET:-smoke}"
stamp="${ROBOCLAWS_CLOUDML_STAMP:-cloudml-smoke-${code_short}-${date_stamp}}"
job_name="${ROBOCLAWS_CLOUDML_JOB_NAME:-roboclaws-eval-${code_short}-smoke}"
output_yaml_path="${ROBOCLAWS_CLOUDML_OUTPUT_YAML:-/tmp/roboclaws-cloudml-${stamp}.yaml}"
code_url="${ROBOCLAWS_CLOUDML_CODE_URL:-https://git.n.xiaomi.com/ipg/infra/roboclaws.git}"
code_branch="${ROBOCLAWS_CLOUDML_CODE_BRANCH:-main}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'USAGE'
Usage:
  scripts/dev/cloudml_eval_dry_run.sh

Generates a CloudML custom_train dry-run YAML through executor. This does not
submit a CloudML task.

Environment overrides:
  ROBOCLAWS_CLOUDML_IMAGE_URL     Pushed eval image URL.
  ROBOCLAWS_CLOUDML_CODE_URL      Default: https://git.n.xiaomi.com/ipg/infra/roboclaws.git
  ROBOCLAWS_CLOUDML_CODE_COMMIT   Default: mi/main commit.
  ROBOCLAWS_CLOUDML_SUITE         Default: smoke_regression
  ROBOCLAWS_CLOUDML_BUDGET        Default: smoke
  ROBOCLAWS_CLOUDML_OUTPUT_YAML   Default: /tmp/roboclaws-cloudml-<stamp>.yaml
USAGE
  exit 0
fi

if [[ ! -x "$executor_root/execute.py" ]]; then
  echo "error: executor not found at $executor_root" >&2
  exit 1
fi

image_command="bash -lc 'set -Eeuo pipefail; cd /ml-engine/code/roboclaws.git; test -x /opt/roboclaws/.venv/bin/python; uv pip install --python /opt/roboclaws/.venv/bin/python --no-build-isolation --no-deps --editable /ml-engine/code/roboclaws.git; just agent::eval suite=${suite} budget=${budget} output_dir=/mnt/cloudml/output/roboclaws-evals stamp=${stamp}'"

argv=(
  "$executor_root/execute.py"
  nvs miaodongxu cloudml submit
  --job_name "$job_name"
  --description "Roboclaws deterministic eval ${suite}/${budget} for ${code_commit}"
  --image_url "$image_url"
  --image_command "$image_command"
  --code_url "$code_url"
  --code_branch "$code_branch"
  --code_commit "$code_commit"
  --dry_run true
  --output_yaml_path "$output_yaml_path"
  --json
)

if [[ -n "${ROBOCLAWS_CLOUDML_CODE_TOKEN:-}" ]]; then
  argv+=(--code_token "$ROBOCLAWS_CLOUDML_CODE_TOKEN")
fi

EXECUTOR_CONFIG_PATH="$executor_config_path" "${argv[@]}"
echo "cloudml_yaml=$output_yaml_path"
