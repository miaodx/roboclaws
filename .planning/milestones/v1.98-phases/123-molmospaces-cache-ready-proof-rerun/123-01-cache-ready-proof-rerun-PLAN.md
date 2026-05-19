# Phase 123 Plan: MolmoSpaces Cache-Ready Proof Rerun

## Goal

Rerun the exact `Bread_1` planner proof against the newly valid droid loader
cache and classify the next blocker after the missing-cache issue is removed.

## Context

Phase 122 installed a validated `Bread_1` droid cache with 9 transforms. Earlier
exact proof evidence for `observed_001` to the refrigerator blocked on missing
or empty grasp-cache data. The same proof request now needs a local rerun to
show whether the cache fix is enough or exposes a later planner issue.

## Scope

- Rerun the exact Phase 109 cleanup binding.
- Use the warmed Phase 102 Torch extension cache for the authoritative run.
- Validate the blocked artifact with the existing manipulation-probe checker.
- Record ADR-0114, source plan, `CONTEXT.md`, and `.planning/STATE.md`.

## Acceptance Criteria

- The warmed rerun reaches the exact sampled task.
- The artifact proves `Bread_1` grasps load from the droid cache.
- The artifact records the next blocker after cache loading.
- The manipulation-probe checker accepts the result as a valid blocked
  RBY1M/CuRobo artifact.

## Verification

- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-cleanup-scene-bound`

## Result

Complete on 2026-05-10.

The warmed rerun loaded 9 cached `Bread_1` grasps, found 2 non-colliding grasps,
matched the exact cleanup binding, and placed the robot. The proof remains
blocked because CuRobo produced no planned pre-grasp trajectory:
`_execute_trajectory was called with no planned trajectory or trajectory index
>= len(planned_trajectory)`.
