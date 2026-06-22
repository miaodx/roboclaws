# CloudML + JuiceFS Eval Capsule

Source plan: `docs/plans/2026-06-18-cloudml-juicefs-eval.md`

Current blocker: no blocker for local real cleanup proof, JuiceFS upload
dry-run, or CloudML dry-run. Formal CloudML submission and bulk JuiceFS asset
upload still require explicit approval.

Blocker fingerprint: `cloudml_submit_or_bulk_asset_upload_requires_confirmation`

Last proven evidence:

- `docker build -f Dockerfile.eval -t roboclaws-eval:local .` passed.
- `ROBOCLAWS_EVAL_OUTPUT_DIR=/tmp/roboclaws-eval-output-current ROBOCLAWS_EVAL_STAMP=offline-smoke-current scripts/dev/run_eval_image_offline_smoke.sh`
  passed with Docker `--network none`.
- Image id: `sha256:66fd32d8943a231830e2ca29fe9467f0f6ff808e6baad45cf9640d728023d81d`.
- Eval artifacts:
  `/tmp/roboclaws-eval-output-current/household_world_smoke_regression/offline-smoke-current/eval_results.json`
  and
  `/tmp/roboclaws-eval-output-current/household_world_smoke_regression/offline-smoke-current/eval_report.html`.
- Eval aggregate: `passed=1`, `failed=0`, `blocked=0`, `pass_at_1=1.0`.
- Pushed eval image:
  `micr.cloud.mioffice.cn/cc-proxy/miuniverse-staging:roboclaws-eval-dfb0a395d1cf-20260619`.
- Pushed image digest:
  `sha256:90a21f7ba1d9336f67c95adedef452d2c75b806da3b853cce374403102a56742`.
- CloudML code source:
  `https://git.n.xiaomi.com/ipg/infra/roboclaws.git`, branch `main`, commit
  `dfb0a395d1cf56121a00ed3f1477e3f7cf8130b3`.
- Clean `mi/main` checkout smoke passed under Docker `--network none` with
  artifacts under
  `/tmp/roboclaws-eval-output-cloudml-phase1-mi-main/household_world_smoke_regression/offline-smoke-mi-main-dfb0a395/`.
- CloudML dry-run YAML generated at
  `/tmp/roboclaws-cloudml-dfb0a395-smoke.yaml` with `dry_run=true` and no
  submitted task id.
- Minimal real product cleanup passed locally:
  `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5 output_dir=/tmp/roboclaws-cleanup-product-local`.
  Artifacts: `/tmp/roboclaws-cleanup-product-local/0620_0903/seed-7/report.html`.
  Backend: `molmospaces_subprocess`; score: `restored_count=4`,
  `total_targets=5`, `mess_restoration_rate=0.8`,
  `sweep_coverage_rate=1.0`, `disturbance_count=0`.
- Minimal real eval cleanup passed locally after the focused eval route was
  wired to the canonical MolmoSpaces map bundle:
  `just agent::eval suite=smoke_regression budget=focused output_dir=/tmp/roboclaws-eval-cleanup-focused-local stamp=cleanup-focused-local-20260620-092357`.
  Artifacts:
  `/tmp/roboclaws-eval-cleanup-focused-local/household_world_smoke_regression/cleanup-focused-local-20260620-092357/eval_results.json`
  and `eval_report.html`; aggregate `passed=1`, `failed=0`, `blocked=0`,
  `pass_at_1=1.0`.
- JuiceFS staging dry-run passed without materializing large MolmoSpaces assets:
  `scripts/dev/stage_cloudml_cleanup_assets.sh` wrote
  `/tmp/roboclaws-cloudml-cleanup-assets-dfb0a395d1cf-20260620/roboclaws_cloudml_cleanup_assets.json`
  and executor planned 97 files / 3,080,839 bytes to
  `robot-intelligent-planning-data/dongxu/gpu_perf/gpu_perf/roboclaws-assets/cleanup-focused/`.
- CloudML product-cleanup dry-run YAML generated at
  `/tmp/roboclaws-cloudml-product-cleanup.yaml` with `dry_run=true`, no
  submitted task id, a public `just run::surface ... preset=cleanup` command,
  and explicit asset checks under
  `/mnt/cloudml/input/roboclaws-assets/cleanup-focused/molmospaces/assets`.

Completed slices:

- Added `Dockerfile.eval` for the baked Roboclaws dev dependency environment.
- Added `scripts/dev/run_eval_image_offline_smoke.sh` for the no-network smoke
  proof.
- Baked `hatchling` and `editables` into the image so runtime editable install
  can use `uv pip install --no-build-isolation --no-deps --editable "$REPO_DIR"`
  without network.
- Declared `editables` in `pyproject.toml` build-system requirements because
  hatchling editable builds need it.
- Added `scripts/dev/build_push_eval_image.sh` for build, local offline smoke,
  and cc-proxy push.
- Added `scripts/dev/cloudml_eval_dry_run.sh` for executor-backed CloudML
  dry-run YAML generation.
- Updated `scripts/dev/run_eval_image_offline_smoke.sh` to support
  `ROBOCLAWS_EVAL_REPO_DIR`, allowing a clean `mi/main` checkout to be mounted
  for proof.
- Updated `scripts/dev/cloudml_eval_dry_run.sh` to default to the public
  product cleanup route:
  `just run::surface surface=household-world world=molmospaces/val_0
  backend=mujoco preset=cleanup agent_engine=direct-runner
  evidence_lane=world-public-labels seed=7
  scenario_setup=relocate-cleanup-related-objects relocation_count=5
  map_bundle=assets/maps/molmospaces/procthor-10k-val/0`. This is compatible
  with the current internal `mi/main` commit.
- Added `scripts/dev/stage_cloudml_cleanup_assets.sh` for manifest-first
  cleanup asset staging and executor JuiceFS upload dry-run.
- Fixed focused direct eval cleanup to pass the canonical
  `assets/maps/molmospaces/procthor-10k-val/0` map bundle to the product
  runner.

Next hypothesis: Phase 2 can submit a minimal real cleanup job to CloudML after
the operator confirms both the materialized MolmoSpaces asset upload and the
CloudML submission. The default CloudML dry-run now uses the public
`just run::surface ... preset=cleanup` product route so it can run with the
older internal `mi/main` commit `dfb0a395d1cf56121a00ed3f1477e3f7cf8130b3`.
Use `ROBOCLAWS_CLOUDML_RUN_MODE=eval-focused` only when the submitted code
commit includes the focused-eval map-bundle fix from this slice.

Next command/artifact:

```bash
ROBOCLAWS_CLOUDML_IMAGE_URL=micr.cloud.mioffice.cn/cc-proxy/miuniverse-staging:roboclaws-eval-dfb0a395d1cf-20260619 \
ROBOCLAWS_CLOUDML_OUTPUT_YAML=/tmp/roboclaws-cloudml-product-cleanup.yaml \
  scripts/dev/cloudml_eval_dry_run.sh

ROBOCLAWS_STAGE_MATERIALIZE_ASSETS=true \
ROBOCLAWS_JUICEFS_URL='https://cloud.mioffice.cn/juicefs/vol-detail?cluster=wlcb-cloudml&name=robot-intelligent-planning-data&path=/dongxu/gpu_perf/gpu_perf/roboclaws-assets/cleanup-focused' \
  scripts/dev/stage_cloudml_cleanup_assets.sh
```

Stop condition: do not remove `--dry_run`, submit a real CloudML job, or upload
the materialized MolmoSpaces asset tree until the target JuiceFS prefix, image
reference, code commit, and expected asset size are accepted.

No-touch scope: no executor target changes, no real CloudML submission, no
real JuiceFS upload/download implementation, no live provider evals, and no
public launch-surface changes.

Parked work: Phase 2 formal CloudML cleanup submit, materialized JuiceFS asset
upload, JuiceFS artifact retrieval/download, live provider evals, report
publishing from JuiceFS.
