# Phase 81 Summary: MolmoSpaces Post-Placement Rejection Diagnostics

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `81-01-post-placement-rejections-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Render why exact-scene task sampling still rejects `Book_23` after the wide
profile clears robot placement.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Completed on 2026-05-10.

The warmed local probe at
`output/debug-phase81-post-placement-rejections/` reported:

- `Post-Placement Candidate Rejections` rendered in `report.html`;
- profile `wide`;
- 17 successful robot-placement calls;
- 0 robot-placement failures;
- 17 grasp-failure reports for the exact book alias;
- 15 candidate-removal calls;
- final status `blocked_capability` with `HouseInvalidForTask`.

The remaining blocker is post-placement grasp/candidate feasibility, not robot
base placement.

## Evidence

See the source phase plan and git history for embedded verification evidence.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
