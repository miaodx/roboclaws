# Phase 78 Plan: MolmoSpaces Task Sampler Robot Placement Profile

## Goal

Add a visible probe-local robot-placement profile and use it to test whether the
current exact book/shelf `HouseInvalidForTask` blocker is caused by default
sampler placement strictness.

## Tasks

1. Add a `--task-sampler-robot-placement-profile relaxed` probe option.
2. Apply task-sampler config overrides before sampler construction.
3. Wrap `env.place_robot_near` during task sampling so hardcoded
   `max_tries=10` becomes visible and overridable.
4. Persist profile evidence and actual placement-call arguments in
   `run_result.json`.
5. Render profile evidence in planner reports and compact proof-bundle result
   cards.
6. Allow proof-bundle command generation to request the profile.
7. Run focused tests and a warmed local RBY1M/CuRobo probe.

## Acceptance Checks

- The warmed local artifact includes `Task Sampler Robot Placement Profile`.
- The artifact shows before/after config and effective `place_robot_near`
  arguments.
- The checker passes on the warmed artifact, accepting blocked RBY1M/CuRobo
  state.
- Planner-backed cleanup readiness remains blocked unless strict proof clears.

## Result

Completed on 2026-05-10.

The warmed local probe at
`output/debug-phase78-task-sampler-placement-profile/` reported:

- profile `relaxed` requested and applied;
- radius `[0.0, 0.7] -> [0.0, 1.2]`;
- robot safety radius `0.35 -> 0.15`;
- visibility check `yes -> no`;
- `place_robot_near` requested `max_tries=10` but effective `max_tries=50`;
- 17 placement calls, 17 placement failures, 17 asset failures, and
  `HouseInvalidForTask`.

## Validation

- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase78-task-sampler-placement-profile --accept-blocked-capability --accept-rby1m-curobo-blocked`

## Status

Complete.
