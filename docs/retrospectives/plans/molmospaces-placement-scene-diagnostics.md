# MolmoSpaces Placement Scene Diagnostics

**Status:** Completed in Phase 79 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0070-render-placement-scene-diagnostics.md`

## Goal

Turn the remaining exact `Book_23` robot-placement blocker into durable
scene-level free-space evidence in the shared planner report.

## Problem

Phase 78 proved the relaxed placement profile is actually applied to upstream
`place_robot_near` calls. The request still fails, but current artifacts do not
show whether the target location has too little free map area, the nearest free
point is too far, or the failure is deeper in collision checking.

## Scope

- Record placement scene diagnostics for actual `place_robot_near` calls.
- Include target position, sampling radius, safety radius, map free-point
  counts, free-space fraction, nearest free point, and radius-band counts.
- Render a `Placement Scene Diagnostics` report view.
- Surface compact placement free-space metrics in proof-bundle result cards.
- Gate report rendering with focused checker coverage.
- Run a warmed local RBY1M/CuRobo probe against the exact `Book_23` request.

## Non-Goals

- Do not patch MolmoSpaces upstream.
- Do not change robot placement behavior beyond the already explicit Phase 78
  profile.
- Do not claim cleanup planner-backed readiness unless strict proof clears.
- Do not add a second cleanup report renderer.

## Acceptance Criteria

- `run_result.json` contains `placement_scene_diagnostics` under
  `task_sampler_failure_diagnostics`.
- `report.html` renders `Placement Scene Diagnostics`.
- Proof-bundle result cards can show placement free-space metrics when present.
- Focused tests and checkers cover the new evidence.
- The warmed local artifact either clears the blocker or explains the remaining
  `HouseInvalidForTask` with scene-level free-space metrics.

## Result

Completed on 2026-05-10.

The warmed local artifact
`output/debug-phase79-placement-scene-diagnostics/report.html` renders
`Placement Scene Diagnostics` for the exact `Book_23` blocker.

The run remains `blocked_capability`, but the report now explains why the
relaxed profile still cannot place RBY1M near the object:

- 17 placement attempts and 17 `place_robot_near` calls;
- target `book_be4d759484637aeb579b28e6a954b18d_1_0_8`;
- sampling radius `[0.0, 1.2]`;
- valid free-point count `2231`;
- free-space fraction `0.012326`;
- nearest free point distance `1.111824m`;
- radius bands below `1.0m` contain zero free points.

The next slice should decide whether to use a wider exact-scene placement
profile, target a different pickup pose/object variant, or add an upstream
task-feasibility prefilter before proof generation.
