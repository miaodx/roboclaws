# Phase 105 Summary: Phase 105-01: Candidate Removal Effectiveness

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `105-01-candidate-removal-effectiveness-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Expose whether repeated grasp-feasibility blocker removal calls actually remove
the requested candidate from the upstream sampler candidate pool.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

Code changes:

- `scripts/run_molmo_planner_manipulation_probe.py`
- `roboclaws/molmo_cleanup/report.py`
- `roboclaws/molmo_cleanup/planner_task_feasibility.py`
- planner probe and proof-bundle checker updates
- focused test coverage

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`

Runtime evidence:

- `output/debug-phase105-grasp-removal-effectiveness-probe/run_result.json`
- `output/debug-phase105-grasp-removal-effectiveness-probe/report.html`

Observed runtime result:

- status: `blocked_capability`
- blocker: `HouseInvalidForTask`
- grasp failures: 17
- candidate-removal calls: 15
- effective removals: 0
- candidate-name misses: 15
- threshold-exceeded rows: 15
- threshold-crossed rows: 1

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Evidence

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`

Runtime evidence:

- `output/debug-phase105-grasp-removal-effectiveness-probe/run_result.json`
- `output/debug-phase105-grasp-removal-effectiveness-probe/report.html`

Observed runtime result:

- status: `blocked_capability`
- blocker: `HouseInvalidForTask`
- grasp failures: 17
- candidate-removal calls: 15
- effective removals: 0
- candidate-name misses: 15
- threshold-exceeded rows: 15
- threshold-crossed rows: 1
- robot-placement failures: 0

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
