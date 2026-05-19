# MolmoSpaces Cache-Ready Proof Rerun

**Status:** Completed under GSD Phase 123 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0113, Phase 109 exact proof request, Phase 102 warmed Torch extension cache, `CONTEXT.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 122 made the droid `Bread_1` loader cache valid, but that alone did not
prove the exact planner cleanup request would pass. The next evidence slice
needed to rerun the exact proof request that previously failed as missing grasp
cache and classify the new blocker.

## Decision

Rerun `observed_001` to the refrigerator with the same exact cleanup binding as
Phase 109.

Two runs were recorded:

- a direct rerun with the default Torch extension cache, which timed out during
  RBY1M/CuRobo config import and did not test the cache path;
- a warmed rerun using the Phase 102 Torch extension directory, which reached
  task sampling and planner policy execution.

## Non-Goals

- Do not tune CuRobo planning parameters in this slice.
- Do not run a cleanup rerun, because no planner-backed proof was produced.
- Do not treat cache validity as sufficient for final cleanup readiness.

## Acceptance Criteria

- The warmed rerun reaches task sampling and uses the exact cleanup binding.
- The artifact shows whether `Bread_1` grasps load from the new droid cache.
- Any remaining blocker is classified after cache loading.
- The existing manipulation-probe checker accepts the blocked artifact.

## Result

Complete.

The warmed proof rerun loaded `Bread_1` from the installed droid cache with
`cached_grasp_count=9`, `grasp_load_failure_count=0`, and
`noncolliding_grasp_count=2`. The exact cleanup binding matched the sampled
task, robot placement succeeded, and the policy reached pre-grasp execution.

The proof still blocked, but the blocker moved to CuRobo trajectory generation:
`_execute_trajectory was called with no planned trajectory or trajectory index
>= len(planned_trajectory)`.

Artifacts:

- `output/debug-phase123-cache-ready-proof001-rerun/run_result.json`
- `output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json`
- `output/debug-phase123-cache-ready-proof001-warmed-rerun/report.html`

Verification:

- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-cleanup-scene-bound`
