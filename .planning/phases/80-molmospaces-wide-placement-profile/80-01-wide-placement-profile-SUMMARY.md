# Phase 80 Summary: MolmoSpaces Wide Placement Profile

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `80-01-wide-placement-profile-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Test whether the exact `Book_23` `HouseInvalidForTask` blocker clears when
the probe uses a visible wider robot-placement profile.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Completed on 2026-05-10.

The warmed local probe at `output/debug-phase80-wide-placement-profile/`
reported:

- profile `wide` applied and rendered in `report.html`;
- effective `place_robot_near(max_tries=100)`;
- radius `[0.0, 2.0]`;
- 17 placement attempts;
- 17 successful placement calls;
- 0 robot-placement failures;
- 0 asset failures;
- 15 downstream candidate removals;
- final status `blocked_capability` with `HouseInvalidForTask`.

The blocker moved from robot placement to post-placement candidate rejection.

## Evidence

See the source phase plan and git history for embedded verification evidence.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
