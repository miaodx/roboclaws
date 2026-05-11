# MolmoSpaces Discovered Runtime Fallback Proof Execution

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0056-run-discovered-runtime-fallback-proofs.md`
**GSD phase:** `.planning/phases/65-molmospaces-discovered-runtime-fallback-proof-execution/`

## Problem

Phase 64 proved the runner can mine exact-scene runtime sibling aliases from
prior `KeyError` valid-name lists and generate four new fallback proof
commands. Those commands still needed local RBY1M/CuRobo execution evidence
before the next architectural decision could be made.

The goal of this slice is not to promote cleanup primitives automatically. It
is to execute the discovered runtime-sibling fallback commands and record
whether they reach strict planner-backed proof, cleanup primitive binding, or a
more precise blocker.

## Scope

- Execute the Phase 64 generated fallback commands locally with the Phase 62
  warmed fallback manifest as prior evidence.
- Keep `--warmup-rby1m-curobo` enabled and use an output-local Torch extension
  cache.
- Require proof outputs through the proof-bundle runner checker.
- Record the exact proof result summary, blockers, and visual/report evidence.
- Keep cleanup readiness blocked unless a proof promotes exact cleanup
  primitive binding.

## Result

The local run wrote
`output/debug-phase65-discovered-runtime-fallback-execute/report.html` and
`proof_bundle_run_manifest.json`.

The runner selected and executed four generated fallback requests:

- `proof_001_fallback_01`
- `proof_001_fallback_02`
- `proof_002_fallback_01`
- `proof_002_fallback_02`

Warmup completed through RBY1M/CuRobo config import, and no proof timed out at
config import. All four commands attempted execution and reached task sampling,
then all four blocked:

- target-sibling aliases still hit `HouseInvalidForTask`;
- object-sibling aliases hit `AssertionError: Object is not a root body`.

The bundle summary reported zero planner-backed proofs, zero cleanup binding
promotions, and zero planner views. This narrows the next blocker from runtime
alias discovery to root-body alias validity and upstream task feasibility.

## Validation

- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase65-discovered-runtime-fallback-execute --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2 --warmup-rby1m-curobo --execute-probes`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py --require-proof-outputs output/debug-phase65-discovered-runtime-fallback-execute`
