# Phase 80 Plan: MolmoSpaces Wide Placement Profile

## Goal

Test whether the exact `Book_23` `HouseInvalidForTask` blocker clears when
the probe uses a visible wider robot-placement profile.

## Tasks

1. Add `wide` to the task-sampler robot-placement profile choices.
2. Apply radius `[0.0, 2.0]`, safety radius `0.15`, no visibility gate, and
   `place_robot_near(max_tries=100)`.
3. Pass the profile through proof-bundle runner command generation.
4. Cover the new profile with focused unit tests.
5. Run a warmed local exact-scene RBY1M/CuRobo probe.
6. Update the ADR, plan, roadmap, state, and CONTEXT evidence.

## Acceptance Checks

- Focused ruff checks pass for changed Python files.
- Focused pytest passes for planner probe and proof-bundle command coverage.
- The warmed local artifact passes the planner manipulation checker.
- The report renders profile `wide`, effective max tries `100`, and placement
  scene diagnostics.

## Result

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

## Validation

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_manipulation_probe.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase80-wide-placement-profile --accept-blocked-capability --accept-rby1m-curobo-blocked`

## Status

Complete.
