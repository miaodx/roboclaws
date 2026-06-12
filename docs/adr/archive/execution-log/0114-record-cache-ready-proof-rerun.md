# 0114. Record Cache-Ready Proof Rerun

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0113 installed a non-empty droid `Bread_1` loader cache with 9 validated
transforms. The remaining question was whether the prior exact proof blocker
for `observed_001` to the refrigerator still failed because of grasp cache
loading, or whether a later planner stage would become visible once the cache
was valid.

## Decision

Rerun the exact Phase 109 proof request against the newly valid cache.

The first direct rerun used the default Torch extension cache and timed out
during RBY1M/CuRobo config import, so it did not test the cache path. The
authoritative rerun reused the warmed Phase 102 Torch extension directory and
the same exact cleanup binding.

## Consequences

- The old missing/empty grasp-cache blocker is cleared: the warmed rerun loaded
  `Bread_1` with `cached_grasp_count=9`, `grasp_load_failure_count=0`, and
  `noncolliding_grasp_count=2`.
- Robot placement also cleared under the existing wide placement profile.
- The proof is still `blocked_capability`: CuRobo found no pre-grasp planned
  trajectory and raised `_execute_trajectory was called with no planned
  trajectory or trajectory index >= len(planned_trajectory)`.
- The next blocker is planner trajectory generation for the loaded grasp set,
  not cache availability or exact cleanup-scene binding.

## Evidence

Implemented in Phase 123 on 2026-05-10.

Artifacts:

- `output/debug-phase123-cache-ready-proof001-rerun/run_result.json`
- `output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json`
- `output/debug-phase123-cache-ready-proof001-warmed-rerun/report.html`

Verification:

- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-cleanup-scene-bound`
