# Phase 79 Plan: MolmoSpaces Placement Scene Diagnostics

## Goal

Render scene-level free-space evidence for the exact `Book_23`
`HouseInvalidForTask` robot-placement blocker.

## Tasks

1. Capture placement scene diagnostics inside the existing
   `place_robot_near` diagnostic wrapper.
2. Record target position, sampling area, valid free-point count, free-space
   fraction, nearest free point, and radius-band counts.
3. Render a `Placement Scene Diagnostics` panel in planner probe reports.
4. Surface compact placement free-space metrics in proof-bundle result cards.
5. Add checker and focused unit-test coverage for the new report view.
6. Run a warmed local RBY1M/CuRobo probe for the exact `Book_23` request.

## Acceptance Checks

- Focused ruff checks pass for changed Python files.
- Focused pytest passes for planner probe, report, proof request, and proof
  bundle checker coverage.
- The warmed local artifact passes
  `check_molmo_planner_manipulation_probe.py` with blocked-capability
  acceptance.
- The artifact report contains `Placement Scene Diagnostics`.

## Result

Completed on 2026-05-10.

The warmed local probe at
`output/debug-phase79-placement-scene-diagnostics/` reported:

- `Placement Scene Diagnostics` rendered in `report.html`;
- 17 robot-placement attempts and 17 failed `place_robot_near` calls;
- target `book_be4d759484637aeb579b28e6a954b18d_1_0_8`;
- sampling radius `[0.0, 1.2]`;
- 2,231 valid free map points in the sampling annulus;
- free-space fraction `0.012326`;
- no free points below `1.0m`;
- nearest free point distance `1.111824m`;
- final status remains `blocked_capability`.

## Validation

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase79-placement-scene-diagnostics --accept-blocked-capability --accept-rby1m-curobo-blocked`

## Status

Complete.
