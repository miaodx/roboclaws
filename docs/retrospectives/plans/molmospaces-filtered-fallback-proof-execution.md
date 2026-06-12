# MolmoSpaces Filtered Fallback Proof Execution

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/archive/execution-log/0058-execute-filtered-fallback-proofs.md`
**GSD phase:** `.planning/milestones/v1.98-phases/67-molmospaces-filtered-fallback-proof-execution/`

## Problem

Phase 66 filtered known-bad generated fallback candidates and left two
remaining proof commands for the untried book runtime sibling
`book_be4d759484637aeb579b28e6a954b18d_1_2_8`. Those commands needed real local
execution before the next fallback slice could decide whether another command
generation pass is useful.

## Scope

- Execute the Phase 66 filtered fallback command set locally.
- Keep RBY1M/CuRobo warmup enabled with an output-local Torch extension cache.
- Require proof outputs through the proof-bundle runner checker.
- Record whether the remaining commands become planner-backed, promote cleanup
  binding, or reveal a more precise blocker.

## Result

The local run wrote
`output/debug-phase67-filtered-fallback-execute/report.html` and
`proof_bundle_run_manifest.json`.

Both remaining commands executed and reached task sampling. Both failed with
`AssertionError: Object is not a root body` for
`book_be4d759484637aeb579b28e6a954b18d_1_2_8`.

The bundle summary reported two proof outputs, two execution attempts, zero
timeouts, zero config-import timeouts, zero planner-backed proofs, zero cleanup
binding promotions, and zero planner views.

The next local-dev slice should derive or validate pickup root-body aliases
before creating more object-side fallback commands.

## Validation

- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase67-filtered-fallback-execute --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase65-discovered-runtime-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2 --warmup-rby1m-curobo --execute-probes`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py --require-proof-outputs output/debug-phase67-filtered-fallback-execute`
