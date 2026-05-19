# Phase 67 Plan: MolmoSpaces Filtered Fallback Proof Execution

## Goal

Execute the failed-candidate-filtered fallback proof commands left by Phase 66
and record whether the remaining runtime sibling can produce strict
planner-backed cleanup evidence.

## Tasks

1. Run the proof-bundle runner against the current cleanup artifact with the
   Phase 65 executed manifest as prior evidence.
2. Enable generated fallback selection, failed-candidate memory, RBY1M/CuRobo
   warmup, low-memory target runtime settings, and real proof execution.
3. Validate the runner artifact with required proof outputs.
4. Inspect the proof result summary for proof status, cleanup binding
   promotion, timeout status, task-feasibility status, worker stages, and
   planner view availability.
5. Record the outcome in ADR, source plan, roadmap, context, and GSD state.

## Acceptance Checks

- The local bundle manifest reaches `status=probes_executed`.
- Exactly the two Phase 66 remaining fallback commands are selected.
- All selected commands produce proof output artifacts.
- Warmup evidence is present in the runner report.
- The checker passes with `--require-proof-outputs`.
- The phase explicitly records whether cleanup primitive binding promoted.

## Result

Completed on 2026-05-10.

The local run executed two generated fallback commands, both using
`book_be4d759484637aeb579b28e6a954b18d_1_2_8`. Warmup got through config
import, both proofs reached task sampling, and neither timed out.

Both proofs remained `blocked_capability` with
`AssertionError: Object is not a root body`. The proof result summary reported
`planner_backed_count=0`, `cleanup_binding_promoted_count=0`,
`timeout_count=0`, and `view_artifact_count=0`.

The next blocker is pickup root-body alias derivation or validation before any
new object-side fallback execution.

## Validation

- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase67-filtered-fallback-execute --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase65-discovered-runtime-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2 --warmup-rby1m-curobo --execute-probes`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py --require-proof-outputs output/debug-phase67-filtered-fallback-execute`
