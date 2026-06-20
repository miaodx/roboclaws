#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
executor_root="${ROBOCLAWS_EXECUTOR_ROOT:-/home/mi/executor}"
executor_config_root="${ROBOCLAWS_EXECUTOR_CONFIG_ROOT:-$executor_root/conf}"
executor_config_path="${ROBOCLAWS_EXECUTOR_CONFIG_PATH:-profiles/nvs/miaodongxu.yaml}"
date_stamp="${ROBOCLAWS_STAGE_DATE:-$(date +%Y%m%d)}"
code_ref="${ROBOCLAWS_EVAL_CODE_REF:-mi/main}"
code_commit="${ROBOCLAWS_CLOUDML_CODE_COMMIT:-$(git -C "$repo_root" rev-parse "$code_ref")}"
code_short="$(git -C "$repo_root" rev-parse --short=12 "$code_commit")"
input_rel="${ROBOCLAWS_JUICEFS_INPUT_REL:-roboclaws-assets/cleanup-focused}"
stage_dir="${ROBOCLAWS_STAGE_DIR:-/tmp/roboclaws-cloudml-cleanup-assets-${code_short}-${date_stamp}}"
registry_repo="${ROBOCLAWS_EVAL_REGISTRY_REPO:-micr.cloud.mioffice.cn/cc-proxy/miuniverse-staging}"
image_url="${ROBOCLAWS_CLOUDML_IMAGE_URL:-${registry_repo}:roboclaws-eval-env-$(git -C "$repo_root" rev-parse --short=8 HEAD)-code-${code_short}-${date_stamp}}"
juicefs_url="${ROBOCLAWS_JUICEFS_URL:-https://cloud.mioffice.cn/juicefs/vol-detail?cluster=wlcb-cloudml&name=robot-intelligent-planning-data&path=/dongxu/gpu_perf/gpu_perf/${input_rel}}"
materialize_assets="${ROBOCLAWS_STAGE_MATERIALIZE_ASSETS:-false}"
include_grasps="${ROBOCLAWS_STAGE_INCLUDE_GRASPS:-false}"
run_upload_dry_run="${ROBOCLAWS_STAGE_RUN_UPLOAD_DRY_RUN:-true}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'USAGE'
Usage:
  scripts/dev/stage_cloudml_cleanup_assets.sh

Prepares a local CloudML cleanup asset staging directory and, by default, asks
executor for a JuiceFS upload dry-run. The default path does not copy the large
MolmoSpaces object cache; it writes a manifest and small repo map assets only.

Environment overrides:
  ROBOCLAWS_STAGE_DIR                 Default: /tmp/roboclaws-cloudml-cleanup-assets-<code>-<date>
  ROBOCLAWS_JUICEFS_INPUT_REL         Default: roboclaws-assets/cleanup-focused
                                      under the CloudML /mnt/cloudml/input mount.
  ROBOCLAWS_JUICEFS_URL               Full cloud.mioffice.cn JuiceFS vol-detail URL.
  ROBOCLAWS_STAGE_MATERIALIZE_ASSETS  Set true to dereference/copy real MolmoSpaces
                                      cleanup assets into the staging directory.
  ROBOCLAWS_STAGE_INCLUDE_GRASPS      Set true to include grasps/droid when materializing.
  ROBOCLAWS_STAGE_RUN_UPLOAD_DRY_RUN  Set false to skip executor upload dry-run.
  ROBOCLAWS_EXECUTOR_ROOT             Default: /home/mi/executor
  ROBOCLAWS_EXECUTOR_CONFIG_ROOT      Default: $ROBOCLAWS_EXECUTOR_ROOT/conf
  ROBOCLAWS_EXECUTOR_CONFIG_PATH      Default: profiles/nvs/miaodongxu.yaml

Real JuiceFS upload is intentionally not performed by this script. After review,
run the printed executor command without --dry_run if the target path is accepted.
USAGE
  exit 0
fi

if [[ ! -x "$repo_root/.venv/bin/python" ]]; then
  echo "error: repo-local .venv is required to discover MolmoSpaces assets" >&2
  exit 1
fi

if [[ ! -x "$executor_root/execute.py" ]]; then
  echo "error: executor not found at $executor_root" >&2
  exit 1
fi

resolve_molmospaces_paths() {
  "$repo_root/.venv/bin/python" - <<'PY'
from molmo_spaces.molmo_spaces_constants import ASSETS_DIR, DATA_CACHE_DIR
print(ASSETS_DIR)
print(DATA_CACHE_DIR)
PY
}

mapfile -t molmospaces_paths < <(resolve_molmospaces_paths)
assets_source="${MLSPACES_ASSETS_DIR:-${molmospaces_paths[0]}}"
cache_source="${MLSPACES_CACHE_DIR:-${molmospaces_paths[1]}}"

require_path() {
  local path="$1"
  local label="$2"
  if [[ ! -e "$path" ]]; then
    echo "error: missing $label: $path" >&2
    exit 1
  fi
}

copy_tree_following_symlinks() {
  local src="$1"
  local dst="$2"
  require_path "$src" "$src"
  mkdir -p "$dst"
  if command -v rsync >/dev/null 2>&1; then
    rsync -aL "$src"/ "$dst"/
  else
    cp -aL "$src"/. "$dst"/
  fi
}

copy_file_following_symlink() {
  local src="$1"
  local dst="$2"
  require_path "$src" "$src"
  mkdir -p "$(dirname "$dst")"
  cp -L "$src" "$dst"
}

mkdir -p "$stage_dir"
mkdir -p "$stage_dir/maps"
copy_tree_following_symlinks "$repo_root/assets/maps/molmospaces" "$stage_dir/maps/molmospaces"

require_path "$assets_source/scenes/procthor-10k-val/val_0.xml" \
  "MolmoSpaces val_0 scene XML"
require_path "$assets_source/scenes/procthor-10k-val/val_0.json" \
  "MolmoSpaces val_0 scene metadata"
require_path "$assets_source/objects/thor" \
  "MolmoSpaces THOR object assets"
require_path "$assets_source/robots/rby1m" \
  "MolmoSpaces RBY1M robot assets"

materialized_paths=()
if [[ "$materialize_assets" == "true" ]]; then
  copy_file_following_symlink \
    "$assets_source/scenes/procthor-10k-val/val_0.xml" \
    "$stage_dir/molmospaces/assets/scenes/procthor-10k-val/val_0.xml"
  copy_file_following_symlink \
    "$assets_source/scenes/procthor-10k-val/val_0.json" \
    "$stage_dir/molmospaces/assets/scenes/procthor-10k-val/val_0.json"
  copy_tree_following_symlinks \
    "$assets_source/objects/thor" \
    "$stage_dir/molmospaces/assets/objects/thor"
  copy_tree_following_symlinks \
    "$assets_source/robots/rby1m" \
    "$stage_dir/molmospaces/assets/robots/rby1m"
  materialized_paths+=(
    "molmospaces/assets/scenes/procthor-10k-val/val_0.xml"
    "molmospaces/assets/scenes/procthor-10k-val/val_0.json"
    "molmospaces/assets/objects/thor"
    "molmospaces/assets/robots/rby1m"
  )
  if [[ "$include_grasps" == "true" ]]; then
    copy_tree_following_symlinks \
      "$assets_source/grasps/droid" \
      "$stage_dir/molmospaces/assets/grasps/droid"
    materialized_paths+=("molmospaces/assets/grasps/droid")
  fi
fi

manifest_path="$stage_dir/roboclaws_cloudml_cleanup_assets.json"
export ROBOCLAWS_STAGE_MANIFEST_PATH="$manifest_path"
export ROBOCLAWS_STAGE_DIR_RESOLVED="$stage_dir"
export ROBOCLAWS_STAGE_INPUT_REL="$input_rel"
export ROBOCLAWS_STAGE_JUICEFS_URL="$juicefs_url"
export ROBOCLAWS_STAGE_CODE_COMMIT="$code_commit"
export ROBOCLAWS_STAGE_IMAGE_URL="$image_url"
export ROBOCLAWS_STAGE_ASSETS_SOURCE="$assets_source"
export ROBOCLAWS_STAGE_CACHE_SOURCE="$cache_source"
export ROBOCLAWS_STAGE_MATERIALIZE_ASSETS="$materialize_assets"
export ROBOCLAWS_STAGE_INCLUDE_GRASPS="$include_grasps"
export ROBOCLAWS_STAGE_MATERIALIZED_PATHS="$(IFS=:; echo "${materialized_paths[*]}")"

"$repo_root/.venv/bin/python" - <<'PY'
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

repo_root = Path(os.environ.get("PWD", ".")).resolve()
stage_dir = Path(os.environ["ROBOCLAWS_STAGE_DIR_RESOLVED"]).resolve()
materialized = [
    item for item in os.environ["ROBOCLAWS_STAGE_MATERIALIZED_PATHS"].split(":") if item
]

def du(path: str) -> str:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        return "missing"
    try:
        return subprocess.check_output(["du", "-sh", str(candidate)], text=True).split()[0]
    except Exception:
        return "unavailable"

payload = {
    "schema": "roboclaws_cloudml_cleanup_assets_v1",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "stage_dir": str(stage_dir),
    "juicefs": {
        "input_rel": os.environ["ROBOCLAWS_STAGE_INPUT_REL"],
        "url": os.environ["ROBOCLAWS_STAGE_JUICEFS_URL"],
        "cloudml_mount_path": "/mnt/cloudml/input",
        "expected_molmospaces_assets_dir": (
            f"/mnt/cloudml/input/{os.environ['ROBOCLAWS_STAGE_INPUT_REL']}"
            "/molmospaces/assets"
        ),
        "expected_molmospaces_cache_dir": (
            f"/mnt/cloudml/input/{os.environ['ROBOCLAWS_STAGE_INPUT_REL']}"
            "/molmospaces/cache"
        ),
    },
    "git": {
        "code_commit": os.environ["ROBOCLAWS_STAGE_CODE_COMMIT"],
        "source_path": "cloudml.codeConfig",
    },
    "image": {
        "url": os.environ["ROBOCLAWS_STAGE_IMAGE_URL"],
    },
    "source_assets": {
        "molmospaces_assets_dir": os.environ["ROBOCLAWS_STAGE_ASSETS_SOURCE"],
        "molmospaces_assets_size": du(os.environ["ROBOCLAWS_STAGE_ASSETS_SOURCE"]),
        "molmospaces_cache_dir": os.environ["ROBOCLAWS_STAGE_CACHE_SOURCE"],
        "molmospaces_cache_size": du(os.environ["ROBOCLAWS_STAGE_CACHE_SOURCE"]),
    },
    "staged_assets": {
        "materialized": os.environ["ROBOCLAWS_STAGE_MATERIALIZE_ASSETS"] == "true",
        "include_grasps": os.environ["ROBOCLAWS_STAGE_INCLUDE_GRASPS"] == "true",
        "paths": materialized,
        "repo_map_assets": "maps/molmospaces",
    },
    "required_cloudml_checks": [
        "molmospaces/assets/scenes/procthor-10k-val/val_0.xml",
        "molmospaces/assets/scenes/procthor-10k-val/val_0.json",
        "molmospaces/assets/objects/thor",
        "molmospaces/assets/robots/rby1m",
        "repo:assets/maps/molmospaces/procthor-10k-val/0/map.yaml",
        "repo:assets/maps/molmospaces/procthor-10k-val/0/semantics.json",
    ],
    "eval": {
        "minimal_real_cleanup_product": (
            "just run::surface surface=household-world world=molmospaces/val_0 "
            "backend=mujoco preset=cleanup agent_engine=direct-runner "
            "evidence_lane=world-public-labels seed=7 "
            "scenario_setup=relocate-cleanup-related-objects relocation_count=5 "
            "map_bundle=assets/maps/molmospaces/procthor-10k-val/0 "
            "output_dir=/mnt/cloudml/output/roboclaws-cleanup-runs/<stamp>"
        ),
        "minimal_real_cleanup_eval": (
            "ROBOCLAWS_CLOUDML_RUN_MODE=eval-focused "
            "just agent::eval suite=smoke_regression budget=focused "
            "output_dir=/mnt/cloudml/output/roboclaws-evals"
        ),
        "pass_k_cleanup": (
            "just agent::eval suite=cleanup_capability budget=focused "
            "output_dir=/mnt/cloudml/output/roboclaws-evals"
        ),
    },
}
Path(os.environ["ROBOCLAWS_STAGE_MANIFEST_PATH"]).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

echo "stage_dir=$stage_dir"
echo "manifest=$manifest_path"
echo "juicefs_url=$juicefs_url"
echo "materialized_assets=$materialize_assets"
echo "upload_dry_run_command=EXECUTOR_CONFIG_ROOT=$executor_config_root EXECUTOR_CONFIG_PATH=$executor_config_path $executor_root/execute.py storage juicefs upload --local_dir '$stage_dir' --url '$juicefs_url' --dry_run --json"

if [[ "$run_upload_dry_run" == "true" ]]; then
  EXECUTOR_CONFIG_ROOT="$executor_config_root" \
    EXECUTOR_CONFIG_PATH="$executor_config_path" \
    "$executor_root/execute.py" storage juicefs upload \
      --local_dir "$stage_dir" \
      --url "$juicefs_url" \
      --dry_run \
      --json
fi
