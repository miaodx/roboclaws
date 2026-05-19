# MolmoSpaces Warmed Generated Fallback Proof Execution

**Status:** Completed in GSD Phase 62 on 2026-05-10
**Source:** CONTEXT.md, ADR-0053, Phase 58/60/61 evidence
**Workflow:** `hybrid-phase-pipeline`

## Goal

Run generated fallback proof requests locally through the warmed proof-bundle
runner path and record whether RBY1M/CuRobo gets past `rby1m_config_import`.

## Scope

- Use the existing ADR-0003 `molmospaces_subprocess` cleanup artifact from the
  prior exact-scene proof bundle flow.
- Use the prior task-feasibility-blocked summary that generated Phase 58
  fallback requests.
- Run the proof-bundle runner with fallback generation, proof execution, and
  `--warmup-rby1m-curobo`.
- Validate the resulting runner artifact with required proof outputs.
- Record whether any generated fallback proof reaches task sampling,
  planner-backed proof, planner views, or cleanup primitive binding promotion.

## Acceptance

- Runner manifest contains the visible RBY1M/CuRobo warmup section.
- Warmup and proof commands share the same output-local Torch extension cache.
- Runner checker passes with `--require-proof-outputs`.
- Result summary states exact proof outcomes and remaining blocker.

## Out Of Scope

- Relaxing proof validation.
- Treating warmup success alone as planner-backed cleanup readiness.
- Changing fallback request generation logic unless execution exposes a concrete
  bug.

## Result

Completed on 2026-05-10 as local-dev evidence.

Output artifact:
`output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json`
with report `output/debug-phase62-warmed-fallback-execute/report.html`.

The runner used `--warmup-rby1m-curobo`, generated four fallback proof
requests, executed the warmup plus all four proof commands, and passed the
runner checker with required proof outputs:

```bash
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py \
  --require-proof-outputs output/debug-phase62-warmed-fallback-execute
```

Warmup result:

- `status=blocked_capability` because config-import mode does not attempt
  execution;
- `last_worker_stage=worker_success`;
- `rby1m_config_import_done` after about 394 seconds;
- all visible CuRobo extension families compiled into the output-local
  `torch_extensions` cache.

Generated proof result summary:

- `status=probes_executed`;
- `command_count=4`;
- planner-backed proofs: 0;
- cleanup binding promotions: 0;
- timeout blockers: 0;
- `rby1m_config_import` timeout blockers: 0;
- task-feasibility blocked proofs: 4;
- planner view artifacts: 0;
- last worker stage counts: `worker_exception=4`.

All four generated fallback probes got past config import and reached task
sampling. They then failed with `KeyError` invalid planner alias names:

- `ShelvingUnit|2|3`;
- `Book|surface|8|79`;
- `Sink|5|1|0`;
- `Bowl|surface|8|77`.

The blocker has moved from RBY1M/CuRobo warmup timeout to fallback alias
validity against the exact MolmoSpaces scene name set.

## Validation

- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase62-warmed-fallback-execute --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2 --warmup-rby1m-curobo --execute-probes`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py --require-proof-outputs output/debug-phase62-warmed-fallback-execute`
