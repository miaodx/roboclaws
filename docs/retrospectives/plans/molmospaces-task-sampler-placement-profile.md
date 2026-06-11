# MolmoSpaces Task Sampler Robot Placement Profile

**Status:** Completed in Phase 78 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0069-add-task-sampler-robot-placement-profile.md`

## Goal

Make robot-placement feasibility mitigation explicit, reusable, and reportable
for the current exact book/shelf planner proof blocker.

## Problem

Phase 77 showed the blocker is repeated robot-placement failure for `Book_23`.
The upstream RBY1M sampler still hardcodes `place_robot_near(max_tries=10)`, so
plain config mutation would be incomplete and potentially misleading.

## Scope

- Add a visible `--task-sampler-robot-placement-profile relaxed` probe option.
- Mutate task-sampler placement config before sampler construction.
- Wrap the actual `place_robot_near` call during sampling so hardcoded
  `max_tries` is overridden and recorded.
- Render the profile and effective call arguments in planner probe reports.
- Carry the profile through proof-result summaries and proof-bundle command
  generation.
- Validate with focused tests and a warmed local RBY1M/CuRobo probe.

## Non-Goals

- Do not patch MolmoSpaces upstream source.
- Do not change cleanup-loop semantics or ADR-0003 public/private rules.
- Do not claim planner-backed cleanup readiness unless the strict proof clears.
- Do not hide a still-blocked run behind the relaxed profile.

## Acceptance Criteria

- `run_result.json` records `task_sampler_robot_placement_profile` when a
  profile is requested.
- `report.html` renders a `Task Sampler Robot Placement Profile` section.
- Task-sampler failure diagnostics record actual `place_robot_near` requested
  and effective arguments.
- Proof-bundle commands can request the same profile.
- The warmed local artifact proves whether the current blocker clears or remains
  after the relaxed profile is applied.

## Result

Completed on 2026-05-10.

The warmed local artifact
`output/debug-phase78-task-sampler-placement-profile/report.html` proves the
relaxed profile applied to the actual upstream placement calls:

- config changed from radius `[0.0, 0.7]`, safety `0.35`, visibility `yes`,
  attempts `10` to radius `[0.0, 1.2]`, safety `0.15`, visibility `no`,
  attempts `50`;
- all 17 `place_robot_near` calls used effective `max_tries=50`;
- all 17 calls still returned `false`, leaving `HouseInvalidForTask` as
  `blocked_capability`.

The next slice should inspect deeper robot placement feasibility around the
exact `Book_23` scene location rather than adding more alias fallback plumbing.
