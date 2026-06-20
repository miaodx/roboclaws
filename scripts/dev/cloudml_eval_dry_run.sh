#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
executor_root="${ROBOCLAWS_EXECUTOR_ROOT:-/home/mi/executor}"
executor_config_root="${ROBOCLAWS_EXECUTOR_CONFIG_ROOT:-$executor_root/conf}"
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
run_mode="${ROBOCLAWS_CLOUDML_RUN_MODE:-product-cleanup}"
suite="${ROBOCLAWS_CLOUDML_SUITE:-smoke_regression}"
budget="${ROBOCLAWS_CLOUDML_BUDGET:-focused}"
input_rel="${ROBOCLAWS_CLOUDML_INPUT_REL:-roboclaws-assets/cleanup-focused}"
cloudml_assets_dir="/mnt/cloudml/input/${input_rel}/molmospaces/assets"
cloudml_cache_dir="/mnt/cloudml/input/${input_rel}/molmospaces/cache"
stamp="${ROBOCLAWS_CLOUDML_STAMP:-cloudml-cleanup-${code_short}-${date_stamp}}"
job_name="${ROBOCLAWS_CLOUDML_JOB_NAME:-roboclaws-cleanup-${code_short}}"
output_yaml_path="${ROBOCLAWS_CLOUDML_OUTPUT_YAML:-/tmp/roboclaws-cloudml-${stamp}.yaml}"
code_url="${ROBOCLAWS_CLOUDML_CODE_URL:-https://git.n.xiaomi.com/ipg/infra/roboclaws.git}"
code_branch="${ROBOCLAWS_CLOUDML_CODE_BRANCH:-main}"
map_bundle="${ROBOCLAWS_CLOUDML_MAP_BUNDLE:-assets/maps/molmospaces/procthor-10k-val/0}"
product_output_dir="${ROBOCLAWS_CLOUDML_PRODUCT_OUTPUT_DIR:-/mnt/cloudml/output/roboclaws-cleanup-runs/${stamp}}"
eval_output_dir="${ROBOCLAWS_CLOUDML_EVAL_OUTPUT_DIR:-/mnt/cloudml/output/roboclaws-evals}"

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
  ROBOCLAWS_CLOUDML_RUN_MODE      Default: product-cleanup.
                                   product-cleanup runs the public cleanup surface
                                   and is compatible with the current mi/main commit.
                                   eval-focused runs just agent::eval and requires
                                   the focused-eval map-bundle fix in the code commit.
  ROBOCLAWS_CLOUDML_SUITE         Default: smoke_regression
                                   Used only for ROBOCLAWS_CLOUDML_RUN_MODE=eval-focused.
                                   Use cleanup_capability for the 3-trial pass@k suite.
  ROBOCLAWS_CLOUDML_BUDGET        Default: focused
                                   Used only for ROBOCLAWS_CLOUDML_RUN_MODE=eval-focused.
  ROBOCLAWS_CLOUDML_INPUT_REL     Default: roboclaws-assets/cleanup-focused
                                   under the /mnt/cloudml/input JuiceFS mount.
  ROBOCLAWS_CLOUDML_MAP_BUNDLE    Default: assets/maps/molmospaces/procthor-10k-val/0
  ROBOCLAWS_CLOUDML_OUTPUT_YAML   Default: /tmp/roboclaws-cloudml-<stamp>.yaml
  ROBOCLAWS_EXECUTOR_ROOT         Default: /home/mi/executor
  ROBOCLAWS_EXECUTOR_CONFIG_ROOT  Default: $ROBOCLAWS_EXECUTOR_ROOT/conf
  ROBOCLAWS_EXECUTOR_CONFIG_PATH  Default: profiles/nvs/miaodongxu.yaml
USAGE
  exit 0
fi

if [[ ! -x "$executor_root/execute.py" ]]; then
  echo "error: executor not found at $executor_root" >&2
  exit 1
fi

case "$run_mode" in
  product-cleanup)
    run_description="Roboclaws product cleanup"
    cloudml_run_command=(
      just run::surface
      surface=household-world
      world=molmospaces/val_0
      backend=mujoco
      preset=cleanup
      agent_engine=direct-runner
      evidence_lane=world-public-labels
      seed=7
      scenario_setup=relocate-cleanup-related-objects
      relocation_count=5
      "map_bundle=${map_bundle}"
      "output_dir=${product_output_dir}"
    )
    ;;
  eval-focused)
    run_description="Roboclaws focused cleanup eval ${suite}/${budget}"
    cloudml_run_command=(
      just agent::eval
      "suite=${suite}"
      "budget=${budget}"
      "output_dir=${eval_output_dir}"
      "stamp=${stamp}"
    )
    ;;
  *)
    echo "error: unsupported ROBOCLAWS_CLOUDML_RUN_MODE '$run_mode'" >&2
    echo "expected product-cleanup|eval-focused" >&2
    exit 1
    ;;
esac
printf -v cloudml_run_command_text '%q ' "${cloudml_run_command[@]}"
cloudml_run_command_text="${cloudml_run_command_text% }"

image_command="$(
  cat <<EOF
bash -lc 'set -Eeuo pipefail; cd /ml-engine/code/roboclaws.git; export MLSPACES_ASSETS_DIR=${cloudml_assets_dir}; export MLSPACES_CACHE_DIR=${cloudml_cache_dir}; test -x /opt/roboclaws/.venv/bin/python; ln -sfn /opt/roboclaws/.venv .venv; test -x .venv/bin/python; test -f ${cloudml_assets_dir}/scenes/procthor-10k-val/val_0.xml; test -f ${cloudml_assets_dir}/scenes/procthor-10k-val/val_0.json; test -d ${cloudml_assets_dir}/objects/thor; test -d ${cloudml_assets_dir}/robots/rby1m; test -f ${map_bundle}/map.yaml; test -f ${map_bundle}/semantics.json; uv pip install --python /opt/roboclaws/.venv/bin/python --no-build-isolation --no-deps --editable /ml-engine/code/roboclaws.git; ${cloudml_run_command_text}'
EOF
)"

argv=(
  "$executor_root/execute.py"
  nvs miaodongxu cloudml submit
  --job_name "$job_name"
  --description "${run_description} for ${code_commit}"
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

EXECUTOR_CONFIG_ROOT="$executor_config_root" \
  EXECUTOR_CONFIG_PATH="$executor_config_path" \
  "${argv[@]}"
echo "cloudml_yaml=$output_yaml_path"
