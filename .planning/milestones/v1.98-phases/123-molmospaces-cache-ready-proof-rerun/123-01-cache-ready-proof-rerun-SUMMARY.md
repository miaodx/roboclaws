# Phase 123 Summary: MolmoSpaces Cache-Ready Proof Rerun

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `123-01-cache-ready-proof-rerun-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Rerun the exact `Bread_1` planner proof against the newly valid droid loader
cache and classify the next blocker after the missing-cache issue is removed.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The warmed rerun loaded 9 cached `Bread_1` grasps, found 2 non-colliding grasps,
matched the exact cleanup binding, and placed the robot. The proof remains
blocked because CuRobo produced no planned pre-grasp trajectory:
`_execute_trajectory was called with no planned trajectory or trajectory index
>= len(planned_trajectory)`.

## Evidence

- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-cleanup-scene-bound`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
