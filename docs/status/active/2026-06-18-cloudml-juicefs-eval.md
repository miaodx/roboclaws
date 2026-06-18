# CloudML + JuiceFS Eval Phase 0 Capsule

Source plan: `docs/plans/2026-06-18-cloudml-juicefs-eval.md`

Current blocker: none for local Phase 0 proof. CloudML dry-run/submission still
requires registry URL, queue/resource, Git URL/commit, JuiceFS mount config, and
explicit approval for Phase 1/2.

Blocker fingerprint: `cloudml_config_external_inputs`

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

Completed slices:

- Added `Dockerfile.eval` for the baked Roboclaws dev dependency environment.
- Added `scripts/dev/run_eval_image_offline_smoke.sh` for the no-network smoke
  proof.
- Baked `hatchling` and `editables` into the image so runtime editable install
  can use `uv pip install --no-build-isolation --no-deps --editable "$REPO_DIR"`
  without network.
- Declared `editables` in `pyproject.toml` build-system requirements because
  hatchling editable builds need it.

Next hypothesis: Phase 1 can validate JuiceFS staging and CloudML dry-run shape
once the operator supplies CloudML queue/resource, internal registry image
reference, Git source/commit, JuiceFS mount fields, and credentials.

Next command/artifact:

```bash
docker build -f Dockerfile.eval -t roboclaws-eval:local .
ROBOCLAWS_EVAL_OUTPUT_DIR=/tmp/roboclaws-eval-output-current \
ROBOCLAWS_EVAL_STAMP=offline-smoke-current \
  scripts/dev/run_eval_image_offline_smoke.sh
```

Stop condition: do not expand into CloudML or JuiceFS work until Phase 1/2
platform fields and approval are supplied.

No-touch scope: no executor target changes, no real CloudML submission, no
JuiceFS upload/download implementation, no live provider evals, and no
`just agent::eval` semantics changes.

Parked work: Phase 1 JuiceFS/executor staging, CloudML dry-run with supplied
platform fields, Phase 2 formal CloudML smoke, live provider evals, report
publishing from JuiceFS.
