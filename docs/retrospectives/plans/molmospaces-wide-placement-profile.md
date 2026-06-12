# MolmoSpaces Wide Placement Profile

**Status:** Completed in Phase 80 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0071-add-wide-placement-profile-retry.md`

## Goal

Use the Phase 79 low-free-space evidence to run an explicit wider
robot-placement profile for the exact `Book_23` planner proof request.

## Problem

The relaxed profile proves hidden sampler defaults are not the blocker, and
Placement Scene Diagnostics show no free points within `1.0m` of `Book_23`.
The current `[0.0, 1.2]m` annulus may be too narrow to find a feasible base
pose, but widening the search must be visible and gated.

## Scope

- Add `--task-sampler-robot-placement-profile wide`.
- Apply radius `[0.0, 2.0]`, safety radius `0.15`, no visibility gate, and
  `max_tries=100` to the actual `place_robot_near` calls.
- Expose the profile through proof-bundle runner command generation.
- Validate the profile with focused tests.
- Run a warmed local RBY1M/CuRobo exact-scene probe.

## Non-Goals

- Do not hide downstream planner failures if task sampling clears.
- Do not mutate MolmoSpaces upstream.
- Do not claim cleanup planner-backed readiness without strict proof and exact
  cleanup binding promotion.
- Do not create a second report implementation.

## Acceptance Criteria

- `wide` is accepted by the probe and proof-bundle runner CLIs.
- `run_result.json` records profile `wide`, radius `[0.0, 2.0]`, and effective
  `place_robot_near(max_tries=100)`.
- `report.html` renders the profile and placement scene diagnostics.
- Focused tests and the artifact checker pass.
- The warmed local artifact shows whether the blocker clears or remains.

## Result

Completed on 2026-05-10.

The warmed local artifact
`output/debug-phase80-wide-placement-profile/report.html` shows the wide
profile changed the current blocker:

- profile `wide` applied;
- radius changed to `[0.0, 2.0]`;
- effective `place_robot_near(max_tries=100)`;
- 17 placement attempts and 17 successful placement calls;
- 0 robot-placement failures;
- 0 asset failures;
- 15 downstream candidate removals;
- final status remains `blocked_capability` with `HouseInvalidForTask`.

Placement Scene Diagnostics now show 74,110 valid free points and free-space
fraction `0.147406` in the `[0.0, 2.0]m` annulus. There are still no free
points below `1.0m`, and the nearest free point remains `1.111824m` away.

The next slice should capture post-placement candidate rejection causes, likely
grasp feasibility or target-preparation rejection, because robot placement is
no longer the failing step under the wide profile.
