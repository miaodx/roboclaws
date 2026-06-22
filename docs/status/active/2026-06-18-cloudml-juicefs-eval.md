# CloudML + JuiceFS Eval Capsule

Source plan: `docs/plans/2026-06-18-cloudml-juicefs-eval.md`

Current blocker: no blocker for image push or CloudML dry-run. Formal CloudML
submission still requires explicit approval.

Blocker fingerprint: `cloudml_submit_requires_confirmation`

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

Next hypothesis: Phase 2 can submit the deterministic `smoke_regression` job to
CloudML with the dry-run YAML shape after the operator confirms formal submit.

Next command/artifact:

```bash
ROBOCLAWS_CLOUDML_IMAGE_URL=micr.cloud.mioffice.cn/cc-proxy/miuniverse-staging:roboclaws-eval-dfb0a395d1cf-20260619 \
ROBOCLAWS_CLOUDML_OUTPUT_YAML=/tmp/roboclaws-cloudml-dfb0a395-smoke.yaml \
  scripts/dev/cloudml_eval_dry_run.sh
```

Stop condition: do not submit a real CloudML job until the dry-run YAML and
submitted image reference are accepted.

No-touch scope: no executor target changes, no real CloudML submission, no
JuiceFS upload/download implementation, no live provider evals, and no
`just agent::eval` semantics changes.

Parked work: Phase 2 formal CloudML smoke, JuiceFS artifact retrieval/download,
live provider evals, report publishing from JuiceFS.
