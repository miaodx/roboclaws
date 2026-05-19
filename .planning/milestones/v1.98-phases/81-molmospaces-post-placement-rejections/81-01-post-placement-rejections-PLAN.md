# Phase 81 Plan: MolmoSpaces Post-Placement Rejection Diagnostics

## Goal

Render why exact-scene task sampling still rejects `Book_23` after the wide
profile clears robot placement.

## Tasks

1. Wrap `report_grasp_failure` in task-sampler failure diagnostics.
2. Record grasp failure counts, thresholds, candidate-pool sizes, and removal
   status.
3. Render `Post-Placement Candidate Rejections` in planner reports.
4. Surface compact grasp-rejection counts in proof-bundle result cards.
5. Add focused checker and unit-test coverage.
6. Run a warmed local wide-profile probe.

## Acceptance Checks

- Focused ruff checks pass for changed Python files.
- Focused pytest passes for planner probe, report, proof request, and proof
  bundle checker coverage.
- The warmed local artifact passes the planner manipulation checker.
- The report contains `Post-Placement Candidate Rejections`.

## Result

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

## Validation

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase81-post-placement-rejections --accept-blocked-capability --accept-rby1m-curobo-blocked`

## Status

Complete.
