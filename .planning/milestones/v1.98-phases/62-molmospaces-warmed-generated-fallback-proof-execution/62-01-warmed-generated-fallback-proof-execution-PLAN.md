# Phase 62 Plan: MolmoSpaces Warmed Generated Fallback Proof Execution

## Goal

Produce local evidence for generated fallback proof execution after the new
RBY1M/CuRobo warmup step, and record whether the warmed run gets past
`rby1m_config_import`.

## Tasks

1. Run the proof-bundle runner against the existing cleanup artifact with
   generated fallback requests, `--warmup-rby1m-curobo`, and proof execution.
2. Validate the runner artifact with required proof outputs.
3. Inspect the proof-result summary for planner-backed proof, cleanup binding
   promotion, planner views, task feasibility, blockers, and last worker stage.
4. Update ADR/source-plan/state docs with the observed outcome.

## Acceptance Checks

- `output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json`
  exists locally.
- `output/debug-phase62-warmed-fallback-execute/report.html` includes the
  warmup and proof-result sections.
- `scripts/check_molmo_planner_proof_bundle_runner_result.py
  --require-proof-outputs` passes on the output directory.
- The phase result documents the exact blocker if generated fallback proof still
  does not promote cleanup primitive binding.

## Result

Completed on 2026-05-10.

The warmed run passed the runner checker with required proof outputs. Warmup got
through RBY1M/CuRobo config import and compiled the output-local CuRobo
extensions. All four generated fallback proofs then reached task sampling and
failed with `KeyError` invalid planner alias names, not timeout.

## Validation

- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase62-warmed-fallback-execute --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2 --warmup-rby1m-curobo --execute-probes`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py --require-proof-outputs output/debug-phase62-warmed-fallback-execute`
