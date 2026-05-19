# Phase 58 Plan: MolmoSpaces Generated Fallback Proof Execution

## Goal

Run generated fallback proof requests through the local RBY1M/CuRobo proof
bundle runner and record whether any generated request produces strict proof and
cleanup primitive binding promotion.

## Inputs

- Source plan:
  `docs/retrospectives/plans/molmospaces-generated-fallback-proof-execution.md`
- ADR:
  `docs/adr/0049-run-generated-fallback-proofs-as-local-dev-evidence.md`
- Existing generated fallback runner support from Phase 57.
- Local cleanup artifact:
  `output/debug-real-binding/run_result.json`
- Synthetic prior blocked summary for the local retry:
  `output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json`

## Tasks

1. Run the proof-bundle runner with `--exclude-task-feasibility-blocked`,
   `--generate-fallback-requests`, `--execute-probes`, and local
   RBY1M/CuRobo settings.
2. Validate the resulting runner artifact with
   `scripts/check_molmo_planner_proof_bundle_runner_result.py
   --require-proof-outputs`.
3. Inspect the proof result summary for planner-backed count, task-feasibility
   status, cleanup binding promotion, blockers, and planner views.
4. Update CONTEXT, roadmap, state, and this plan with the result.

## Acceptance Checks

- Runner checker passes with required proof outputs.
- The runner report includes generated fallback request rows and proof result
  rows for each executed fallback.
- The result records whether cleanup primitive binding promoted or which target
  runtime blocker remains.

## Result

Completed on 2026-05-10.

Executed command:

```bash
.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py \
  output/debug-real-binding/run_result.json \
  --output-dir output/debug-phase58-fallback-execute \
  --probe-mode execute \
  --embodiment rby1m \
  --steps 1 \
  --timeout-s 180 \
  --renderer-device-id 0 \
  --torch-extensions-dir output/debug-phase58-fallback-execute/torch_extensions \
  --prior-proof-bundle-manifest output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json \
  --exclude-task-feasibility-blocked \
  --generate-fallback-requests \
  --fallback-alias-limit 2 \
  --execute-probes
```

Validation:

```bash
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py \
  --require-proof-outputs output/debug-phase58-fallback-execute
```

The checker passed. The manifest/report contain four generated fallback
requests and four executed proof outputs.

Observed proof result summary:

- `status=probes_executed`
- `command_count=4`
- generated fallback requests: 4
- planner-backed proofs: 0
- cleanup binding promotions: 0
- task-feasibility blocked proofs: 0
- planner view artifacts: 0
- each proof status: `blocked_capability`
- each proof task feasibility: `not_reached`
- each proof blocker: `timeout`
- each proof last worker stage: `rby1m_config_import`

This phase did not promote cleanup primitive binding. The generated fallback
requests timed out before task sampling, so the next work should address
target-runtime warmup/JIT progress or timeout-stage diagnostics for generated
fallback execution.
