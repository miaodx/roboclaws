#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
phase="${ROBOCLAWS_EXPERIMENT_PHASE:-all}"
dry_run="${ROBOCLAWS_EXPERIMENT_DRY_RUN:-true}"
stamp="${ROBOCLAWS_EXPERIMENT_STAMP:-}"
publish_when_ready="${ROBOCLAWS_EXPERIMENT_PUBLISH_WHEN_READY:-false}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'USAGE'
Usage:
  scripts/dev/cloudml_experiment_flow.sh

Coordinates the executor-backed CloudML experiment loop:
  1. stage local assets/code as JuiceFS-friendly archives,
  2. generate or submit the CloudML job through executor,
  3. publish a completed report bundle to FDS for HTML preview.

CloudML execution is asynchronous. The default `all` phase performs asset
staging and job generation/submission only. Publish after the CloudML output
directory contains report.html or eval_report.html by running phase=publish
with either a local directory or a JuiceFS URL.

Environment overrides:
  ROBOCLAWS_EXPERIMENT_PHASE          all|stage-assets|submit|publish.
                                      Default: all.
  ROBOCLAWS_EXPERIMENT_DRY_RUN        true|false. Default: true. Controls
                                      JuiceFS/FDS upload and CloudML submit
                                      safety defaults.
  ROBOCLAWS_EXPERIMENT_STAMP          Shared experiment id. Default is inherited
                                      by lower scripts when set.
  ROBOCLAWS_EXPERIMENT_PUBLISH_WHEN_READY
                                      true|false. Default: false. If true with
                                      phase=all, publish is attempted after
                                      submit/generate using PREVIEW_* inputs.

Stage asset overrides are passed to stage_cloudml_cleanup_assets.sh.
CloudML submit overrides are passed to cloudml_eval_dry_run.sh.
Preview overrides are passed to publish_cloudml_report_to_fds.sh.

Typical sequence:
  # Prepare archives and inspect upload plan.
  ROBOCLAWS_EXPERIMENT_PHASE=stage-assets scripts/dev/cloudml_experiment_flow.sh

  # Stage/upload assets and submit CloudML.
  ROBOCLAWS_EXPERIMENT_DRY_RUN=false ROBOCLAWS_EXPERIMENT_STAMP=<experiment> \
    ROBOCLAWS_CLOUDML_IMAGE_URL=<pushed-image> scripts/dev/cloudml_experiment_flow.sh

  # After CloudML writes report.html or eval_report.html, publish it for discussion.
  ROBOCLAWS_EXPERIMENT_PHASE=publish ROBOCLAWS_EXPERIMENT_DRY_RUN=false \
    ROBOCLAWS_PREVIEW_JUICEFS_URL='<vol-detail-url-to-run-dir>' \
    scripts/dev/cloudml_experiment_flow.sh
USAGE
  exit 0
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

run_stage_assets() {
  echo "experiment_phase=stage-assets"
  if bool_true "$dry_run"; then
    export ROBOCLAWS_STAGE_RUN_UPLOAD_DRY_RUN="${ROBOCLAWS_STAGE_RUN_UPLOAD_DRY_RUN:-true}"
    export ROBOCLAWS_STAGE_RUN_UPLOAD="${ROBOCLAWS_STAGE_RUN_UPLOAD:-false}"
  else
    export ROBOCLAWS_STAGE_RUN_UPLOAD_DRY_RUN="${ROBOCLAWS_STAGE_RUN_UPLOAD_DRY_RUN:-false}"
    export ROBOCLAWS_STAGE_RUN_UPLOAD="${ROBOCLAWS_STAGE_RUN_UPLOAD:-true}"
  fi
  if [[ -n "$stamp" ]]; then
    export ROBOCLAWS_STAGE_DIR="${ROBOCLAWS_STAGE_DIR:-/tmp/roboclaws-cloudml-cleanup-assets-$stamp}"
  fi
  "$repo_root/scripts/dev/stage_cloudml_cleanup_assets.sh"
}

run_submit() {
  echo "experiment_phase=submit"
  if bool_true "$dry_run"; then
    export ROBOCLAWS_CLOUDML_DRY_RUN="${ROBOCLAWS_CLOUDML_DRY_RUN:-true}"
  else
    export ROBOCLAWS_CLOUDML_DRY_RUN="${ROBOCLAWS_CLOUDML_DRY_RUN:-false}"
  fi
  if [[ -n "$stamp" ]]; then
    export ROBOCLAWS_CLOUDML_STAMP="${ROBOCLAWS_CLOUDML_STAMP:-$stamp}"
    export ROBOCLAWS_CLOUDML_JOB_NAME="${ROBOCLAWS_CLOUDML_JOB_NAME:-roboclaws-$stamp}"
  fi
  "$repo_root/scripts/dev/cloudml_eval_dry_run.sh"
}

run_publish() {
  echo "experiment_phase=publish"
  if bool_true "$dry_run"; then
    export ROBOCLAWS_PREVIEW_DRY_RUN="${ROBOCLAWS_PREVIEW_DRY_RUN:-true}"
  else
    export ROBOCLAWS_PREVIEW_DRY_RUN="${ROBOCLAWS_PREVIEW_DRY_RUN:-false}"
  fi
  if [[ -n "$stamp" ]]; then
    export ROBOCLAWS_PREVIEW_STAMP="${ROBOCLAWS_PREVIEW_STAMP:-$stamp}"
  fi
  "$repo_root/scripts/dev/publish_cloudml_report_to_fds.sh"
}

case "$phase" in
  stage-assets)
    run_stage_assets
    ;;
  submit)
    run_submit
    ;;
  publish)
    run_publish
    ;;
  all)
    run_stage_assets
    run_submit
    if bool_true "$publish_when_ready"; then
      run_publish
    else
      echo "experiment_publish=deferred"
      echo "hint: run ROBOCLAWS_EXPERIMENT_PHASE=publish after CloudML produces report.html or eval_report.html"
    fi
    ;;
  *)
    echo "error: unsupported ROBOCLAWS_EXPERIMENT_PHASE '$phase'" >&2
    echo "expected all|stage-assets|submit|publish" >&2
    exit 1
    ;;
esac
