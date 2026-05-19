# Phase 77 Plan: MolmoSpaces Task Sampler Failure Diagnostics

## Goal

Capture and render structured upstream task-sampler failure diagnostics for the
current target-side `HouseInvalidForTask` blocker.

## Tasks

1. Add a probe-local task-sampler diagnostics adapter.
2. Record robot-placement attempts, asset failures, candidate removals, and
   placement config.
3. Persist diagnostics in planner probe evidence and proof-result summaries.
4. Render diagnostics in the planner manipulation report and proof-bundle result
   cards.
5. Tighten checkers and tests for diagnostics report text.
6. Run a warmed local RBY1M/CuRobo probe against the current exact
   book/shelf request.

## Acceptance Checks

- The warmed local run remains `blocked_capability` with `HouseInvalidForTask`.
- The report includes `Task Sampler Failure Diagnostics`.
- The artifact records robot-placement attempt and asset-failure counts.
- The checker passes on the warmed artifact.
- Planner-backed cleanup readiness remains blocked.

## Result

Completed on 2026-05-10.

The Phase 77 warmed local probe at
`output/debug-phase77-task-sampler-failure-diagnostics/` reported:

- `robot_placement_attempt_count=17`
- `robot_placement_failure_count=17`
- `asset_failure_count=17`
- `candidate_removal_count=17`
- `asset_uid=Book_23`
- repeated `RobotPlacementError` for
  `book_be4d759484637aeb579b28e6a954b18d_1_0_8`

## Validation

- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py`
- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase77-task-sampler-failure-diagnostics --accept-blocked-capability --accept-rby1m-curobo-blocked`

## Status

Complete.
