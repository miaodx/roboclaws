# MolmoSpaces Post-Placement Rejection Diagnostics

**Status:** Completed in Phase 81 on 2026-05-10
**Parent plan:** `docs/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0072-capture-post-placement-candidate-rejections.md`

## Goal

Explain why the exact `Book_23` proof request still ends in
`HouseInvalidForTask` after the wide placement profile clears robot placement.

## Problem

Phase 80 showed all `place_robot_near` calls succeed under the wide profile,
but the sampler still removes candidates and eventually rejects the house. The
report needs to show whether those removals are caused by grasp-feasibility
thresholds or another post-placement rejection path.

## Scope

- Wrap `report_grasp_failure` in the task-sampler diagnostics adapter.
- Record grasp failure counts, thresholds, candidate-pool sizes, and removal
  status.
- Render a `Post-Placement Candidate Rejections` report view.
- Surface compact grasp-rejection counts in proof-bundle result cards.
- Validate with focused tests and a warmed local wide-profile probe.

## Non-Goals

- Do not change grasp sampling, collision checks, or upstream task sampling.
- Do not claim planner-backed cleanup readiness.
- Do not add a second report renderer.

## Acceptance Criteria

- `run_result.json` records `grasp_failures` under
  `task_sampler_failure_diagnostics`.
- `report.html` renders `Post-Placement Candidate Rejections`.
- The checker fails when the evidence exists but the report view is missing.
- The warmed local artifact identifies whether downstream candidate removals
  are caused by grasp-failure thresholds.

## Result

Completed on 2026-05-10.

The warmed local artifact
`output/debug-phase81-post-placement-rejections/report.html` renders
`Post-Placement Candidate Rejections` for the exact `Book_23` request.

The run remains `blocked_capability`, but the report now distinguishes the
failure from robot placement:

- profile `wide`;
- 17/17 successful `place_robot_near` calls;
- 0 robot-placement failures;
- 17 grasp-failure reports;
- 15 candidate-removal calls;
- final blocker `HouseInvalidForTask`.

The candidate count stays at 17 during the recorded grasp-failure calls, so the
forced exact alias is repeatedly rejected for grasp feasibility without actually
shrinking the upstream candidate pool.

The next slice should test a grasp-feasible candidate or add a prefilter that
avoids proof requests whose forced exact alias has no feasible grasps.
