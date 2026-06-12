# 0073. Classify Grasp-Feasibility Blockers

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0072 made post-placement rejection visible in individual planner probe
reports. The next architectural gap is bundle-level propagation: proof-result
summaries and runner reports still describe those artifacts as generic
`task_feasibility_status=blocked`.

Without a compact blocker kind, selection and review workflows cannot
distinguish robot-placement failure from grasp-feasibility failure.

## Decision

Add `task_feasibility_blocker_kind` and
`task_feasibility_blocker_summary` to proof-result summaries.

The first classified kinds are:

- `robot_placement` when robot-placement failures are recorded;
- `grasp_feasibility` when grasp failures are recorded after robot placement;
- `task_sampling` for generic `HouseInvalidForTask` without a more specific
  diagnostic.

Render `grasp_feasibility` counts and per-result details in proof-bundle runner
reports and validate those fields in the checker.

## Consequences

- Runner reports can show when a blocked proof is now a grasp/candidate problem
  instead of a robot-placement problem.
- Future selection phases can filter or replace grasp-infeasible exact aliases
  without parsing nested diagnostic tables.
- The classification remains evidence only; it does not promote cleanup
  readiness or generate alternate requests by itself.

## Evidence

Phase 82 validates the classifier with focused tests. It uses the Phase 81
artifact shape as the target behavior and does not require a new local simulator
run.

Verification on 2026-05-10:

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- Manual classification of
  `output/debug-phase81-post-placement-rejections/run_result.json` reports
  `grasp_feasibility_blocked_count=1`,
  `task_feasibility_blocker_kind=grasp_feasibility`, and
  `task_feasibility_blocker_summary="17 grasp failures; 15 candidate-removal calls"`.
