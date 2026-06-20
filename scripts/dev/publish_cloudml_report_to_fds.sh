#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
executor_root="${ROBOCLAWS_EXECUTOR_ROOT:-/home/mi/executor}"
executor_config_root="${ROBOCLAWS_EXECUTOR_CONFIG_ROOT:-$executor_root/conf}"
executor_config_path="${ROBOCLAWS_EXECUTOR_CONFIG_PATH:-profiles/nvs/miaodongxu.yaml}"
entrypoint="${ROBOCLAWS_PREVIEW_ENTRYPOINT:-}"
entrypoint_explicit=false
if [[ -n "$entrypoint" ]]; then
  entrypoint_explicit=true
fi
public="${ROBOCLAWS_PREVIEW_PUBLIC:-true}"
dry_run="${ROBOCLAWS_PREVIEW_DRY_RUN:-true}"
force="${ROBOCLAWS_PREVIEW_FORCE:-false}"
stamp="${ROBOCLAWS_PREVIEW_STAMP:-}"
source_dir="${ROBOCLAWS_PREVIEW_LOCAL_DIR:-}"
juicefs_url="${ROBOCLAWS_PREVIEW_JUICEFS_URL:-}"
work_dir="${ROBOCLAWS_PREVIEW_WORK_DIR:-/tmp/roboclaws-fds-preview}"
fds_target="${ROBOCLAWS_PREVIEW_FDS_TARGET:-}"
cloudml_job_id="${ROBOCLAWS_PREVIEW_CLOUDML_JOB_ID:-}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'USAGE'
Usage:
  scripts/dev/publish_cloudml_report_to_fds.sh

Publishes one completed Roboclaws experiment report bundle to Xiaomi FDS for
HTML preview. The source can be a local artifact directory or a JuiceFS
vol-detail URL. The script writes a small preview summary, uploads the bundle
with executor, and verifies the returned HTML URL when this is not a dry run.

Environment overrides:
  ROBOCLAWS_PREVIEW_LOCAL_DIR     Local directory containing report.html or
                                  eval_report.html.
  ROBOCLAWS_PREVIEW_JUICEFS_URL   JuiceFS vol-detail URL to download first.
                                  If this contains multiple report.html files,
                                  set LOCAL_DIR or narrow the URL.
  ROBOCLAWS_PREVIEW_WORK_DIR      Default: /tmp/roboclaws-fds-preview.
  ROBOCLAWS_PREVIEW_STAMP         Preview id. Default: source dir basename or
                                  roboclaws-preview-<timestamp>.
  ROBOCLAWS_PREVIEW_FDS_TARGET    Default: miaodongxu/roboclaws/reports/<stamp>.
  ROBOCLAWS_PREVIEW_ENTRYPOINT    Default: auto-detect report.html or
                                  eval_report.html. Set explicitly to force
                                  one entrypoint.
  ROBOCLAWS_PREVIEW_PUBLIC        true|false. Default: true.
  ROBOCLAWS_PREVIEW_DRY_RUN       true|false. Default: true.
  ROBOCLAWS_PREVIEW_FORCE         true|false. Default: false.
  ROBOCLAWS_PREVIEW_CLOUDML_JOB_ID
                                  Optional metadata written to summary JSON.
  ROBOCLAWS_EXECUTOR_ROOT         Default: /home/mi/executor.
  ROBOCLAWS_EXECUTOR_CONFIG_ROOT  Default: $ROBOCLAWS_EXECUTOR_ROOT/conf.
  ROBOCLAWS_EXECUTOR_CONFIG_PATH  Default: profiles/nvs/miaodongxu.yaml.
USAGE
  exit 0
fi

if [[ ! -x "$executor_root/execute.py" ]]; then
  echo "error: executor not found at $executor_root" >&2
  exit 1
fi

bool_true() {
  case "$1" in
    true|1|yes|y|on) return 0 ;;
    false|0|no|n|off|"") return 1 ;;
    *)
      echo "error: expected boolean true|false, got '$1'" >&2
      exit 1
      ;;
  esac
}

slugify() {
  "$repo_root/.venv/bin/python" - "$1" <<'PY'
import re
import sys

value = sys.argv[1].strip().strip("/")
value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
print(value[:96] or "roboclaws-preview")
PY
}

count_report_files() {
  find "$1" -type f -name "$2" | wc -l | tr -d ' '
}

first_report_file() {
  find "$1" -type f -name "$2" | sort | head -1
}

resolve_report_source() {
  local root="$1"
  local selected_file
  local report_count
  local eval_count

  if [[ "$entrypoint_explicit" == "true" ]]; then
    report_count="$(count_report_files "$root" "$entrypoint")"
    case "$report_count" in
      0)
        echo "error: no $entrypoint found under $root" >&2
        exit 1
        ;;
      1)
        selected_file="$(first_report_file "$root" "$entrypoint")"
        printf '%s\t%s\n' "$entrypoint" "$(dirname "$selected_file")"
        ;;
      *)
        echo "error: multiple $entrypoint files found under $root; narrow the source" >&2
        find "$root" -type f -name "$entrypoint" | sort >&2
        exit 1
        ;;
    esac
    return
  fi

  if [[ -f "$root/eval_report.html" ]]; then
    printf '%s\t%s\n' "eval_report.html" "$root"
    return
  fi
  if [[ -f "$root/report.html" ]]; then
    printf '%s\t%s\n' "report.html" "$root"
    return
  fi

  eval_count="$(count_report_files "$root" "eval_report.html")"
  case "$eval_count" in
    0)
      ;;
    1)
      selected_file="$(first_report_file "$root" "eval_report.html")"
      printf '%s\t%s\n' "eval_report.html" "$(dirname "$selected_file")"
      return
      ;;
    *)
      echo "error: multiple eval_report.html files found under $root; narrow the source" >&2
      find "$root" -type f -name "eval_report.html" | sort >&2
      exit 1
      ;;
  esac

  local report_count
  report_count="$(count_report_files "$root" "report.html")"
  case "$report_count" in
    0)
      echo "error: no report.html or eval_report.html found under $root" >&2
      exit 1
      ;;
    1)
      selected_file="$(first_report_file "$root" "report.html")"
      printf '%s\t%s\n' "report.html" "$(dirname "$selected_file")"
      ;;
    *)
      echo "error: multiple report.html files found under $root; narrow the source" >&2
      find "$root" -type f -name "report.html" | sort >&2
      exit 1
      ;;
  esac
}

mkdir -p "$work_dir"

if [[ -n "$source_dir" && -n "$juicefs_url" ]]; then
  echo "error: set only one of ROBOCLAWS_PREVIEW_LOCAL_DIR or ROBOCLAWS_PREVIEW_JUICEFS_URL" >&2
  exit 1
fi

if [[ -z "$source_dir" ]]; then
  if [[ -z "$juicefs_url" ]]; then
    echo "error: set ROBOCLAWS_PREVIEW_LOCAL_DIR or ROBOCLAWS_PREVIEW_JUICEFS_URL" >&2
    exit 1
  fi
  download_dir="$work_dir/juicefs-download"
  rm -rf "$download_dir"
  mkdir -p "$download_dir"
  EXECUTOR_CONFIG_ROOT="$executor_config_root" \
    EXECUTOR_CONFIG_PATH="$executor_config_path" \
    "$executor_root/execute.py" storage juicefs download \
      --url "$juicefs_url" \
      --output_dir "$download_dir" \
      --refresh_list \
      --json
  report_selection="$(resolve_report_source "$download_dir")"
  entrypoint="${report_selection%%$'\t'*}"
  source_dir="${report_selection#*$'\t'}"
fi

source_dir="$(cd "$source_dir" && pwd)"
report_selection="$(resolve_report_source "$source_dir")"
entrypoint="${report_selection%%$'\t'*}"
source_dir="${report_selection#*$'\t'}"
source_dir="$(cd "$source_dir" && pwd)"

if [[ -z "$stamp" ]]; then
  stamp="$(slugify "$(basename "$source_dir")")"
  if [[ "$stamp" == "." || "$stamp" == "/" || -z "$stamp" ]]; then
    stamp="roboclaws-preview-$(date +%Y%m%d-%H%M%S)"
  fi
fi
if [[ -z "$fds_target" ]]; then
  fds_target="miaodongxu/roboclaws/reports/$stamp"
fi

original_source_dir="$source_dir"
bundle_dir="$work_dir/bundles/$stamp"
rm -rf "$bundle_dir"
mkdir -p "$bundle_dir"
cp -a "$original_source_dir/." "$bundle_dir/"

summary_path="$bundle_dir/cloudml_preview_summary.json"
export ROBOCLAWS_PREVIEW_SUMMARY_PATH="$summary_path"
export ROBOCLAWS_PREVIEW_SOURCE_DIR_RESOLVED="$original_source_dir"
export ROBOCLAWS_PREVIEW_BUNDLE_DIR_RESOLVED="$bundle_dir"
export ROBOCLAWS_PREVIEW_JUICEFS_URL_RESOLVED="$juicefs_url"
export ROBOCLAWS_PREVIEW_FDS_TARGET_RESOLVED="$fds_target"
export ROBOCLAWS_PREVIEW_ENTRYPOINT_RESOLVED="$entrypoint"
export ROBOCLAWS_PREVIEW_STAMP_RESOLVED="$stamp"
export ROBOCLAWS_PREVIEW_CLOUDML_JOB_ID_RESOLVED="$cloudml_job_id"

"$repo_root/.venv/bin/python" - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

source_dir = Path(os.environ["ROBOCLAWS_PREVIEW_SOURCE_DIR_RESOLVED"])
bundle_dir = Path(os.environ["ROBOCLAWS_PREVIEW_BUNDLE_DIR_RESOLVED"])
run_result_path = bundle_dir / "run_result.json"
eval_results_path = bundle_dir / "eval_results.json"
run_result = {}
if run_result_path.is_file():
    run_result = json.loads(run_result_path.read_text(encoding="utf-8"))
eval_results = {}
if eval_results_path.is_file():
    eval_results = json.loads(eval_results_path.read_text(encoding="utf-8"))

score = run_result.get("score", {}) if isinstance(run_result, dict) else {}
eval_suite = eval_results.get("suite", {}) if isinstance(eval_results, dict) else {}
eval_aggregate = eval_results.get("aggregate", {}) if isinstance(eval_results, dict) else {}
payload = {
    "schema": "roboclaws_cloudml_preview_summary_v1",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "stamp": os.environ["ROBOCLAWS_PREVIEW_STAMP_RESOLVED"],
    "report_kind": "eval" if eval_results else "product",
    "source_dir": str(source_dir),
    "bundle_dir": str(bundle_dir),
    "source_juicefs_url": os.environ["ROBOCLAWS_PREVIEW_JUICEFS_URL_RESOLVED"],
    "source_cloudml_job_id": os.environ["ROBOCLAWS_PREVIEW_CLOUDML_JOB_ID_RESOLVED"],
    "fds_target": os.environ["ROBOCLAWS_PREVIEW_FDS_TARGET_RESOLVED"],
    "entrypoint": os.environ["ROBOCLAWS_PREVIEW_ENTRYPOINT_RESOLVED"],
    "task_surface": run_result.get("task_surface"),
    "task_intent": run_result.get("task_intent"),
    "task_prompt": run_result.get("task_prompt"),
    "scenario_id": run_result.get("scenario_id"),
    "seed": run_result.get("seed"),
    "terminate_reason": run_result.get("terminate_reason"),
    "score_status": score.get("status"),
    "completion_status": score.get("completion_status"),
    "semantic_acceptability": score.get("semantic_acceptability"),
    "eval_suite_id": eval_suite.get("suite_id"),
    "eval_budget": eval_results.get("budget") if isinstance(eval_results, dict) else None,
    "eval_total": eval_aggregate.get("total"),
    "eval_passed": eval_aggregate.get("passed"),
    "eval_failed": eval_aggregate.get("failed"),
    "eval_blocked": eval_aggregate.get("blocked"),
    "eval_pass_at_1": eval_aggregate.get("pass_at_1"),
    "eval_pass_at_k": eval_aggregate.get("pass_at_k"),
    "eval_pass_caret_k": eval_aggregate.get("pass_caret_k"),
}
Path(os.environ["ROBOCLAWS_PREVIEW_SUMMARY_PATH"]).write_text(
    json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

upload_json="$work_dir/fds-upload-${stamp}.json"
argv=(
  "$executor_root/execute.py" storage fds upload
  --local_dir "$bundle_dir"
  --target "$fds_target"
  --entrypoint "$entrypoint"
  --json
)
bool_true "$public" && argv+=(--public)
bool_true "$dry_run" && argv+=(--dry_run)
bool_true "$force" && argv+=(--force)

EXECUTOR_CONFIG_ROOT="$executor_config_root" \
  EXECUTOR_CONFIG_PATH="$executor_config_path" \
  "${argv[@]}" | tee "$upload_json"

preview_url="$("$repo_root/.venv/bin/python" - "$upload_json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("entrypoint_url") or "")
PY
)"

echo "preview_source_dir=$original_source_dir"
echo "preview_bundle_dir=$bundle_dir"
echo "preview_summary=$summary_path"
echo "fds_upload_result=$upload_json"
echo "fds_target=$fds_target"
echo "preview_url=$preview_url"

if ! bool_true "$dry_run"; then
  if [[ -z "$preview_url" ]]; then
    echo "error: upload did not return an entrypoint URL" >&2
    exit 1
  fi
  headers_path="$work_dir/fds-preview-${stamp}.headers"
  http_code="$(curl -sSIL -o "$headers_path" -w '%{http_code}' "$preview_url")"
  if [[ "$http_code" != "200" ]]; then
    echo "error: preview URL returned HTTP $http_code: $preview_url" >&2
    sed -n '1,40p' "$headers_path" >&2
    exit 1
  fi
  content_type="$(awk 'tolower($1)=="content-type:" {line=$0} END{sub(/\r$/, "", line); print line}' "$headers_path")"
  case "${content_type,,}" in
    *text/html*) ;;
    *)
      echo "error: preview URL is not HTML: $content_type" >&2
      exit 1
      ;;
  esac

  asset_rel="$(
    cd "$bundle_dir"
    find . -maxdepth 3 -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.webp' \) \
      | sed 's#^\./##' | sort | head -1
  )"
  if [[ -n "$asset_rel" ]]; then
    asset_url="${preview_url%/*}/$asset_rel"
    asset_headers_path="$work_dir/fds-preview-${stamp}-asset.headers"
    asset_http_code="$(curl -sSIL -o "$asset_headers_path" -w '%{http_code}' "$asset_url")"
    if [[ "$asset_http_code" != "200" ]]; then
      echo "error: preview asset returned HTTP $asset_http_code: $asset_url" >&2
      sed -n '1,40p' "$asset_headers_path" >&2
      exit 1
    fi
    echo "preview_asset_url=$asset_url"
  fi
fi
