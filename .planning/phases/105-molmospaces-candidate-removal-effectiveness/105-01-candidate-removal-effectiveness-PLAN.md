# Phase 105-01: Candidate Removal Effectiveness

## Goal

Expose whether repeated grasp-feasibility blocker removal calls actually remove
the requested candidate from the upstream sampler candidate pool.

## Tasks

- Extend task-sampler failure diagnostics around `report_grasp_failure()` and
  `_remove_candidate_object()`.
- Record threshold state, candidate-name presence, candidate counts, and
  effective-removal state.
- Render candidate-removal effectiveness in standalone planner reports,
  proof-bundle result cards, and grouped grasp signatures.
- Update checker gates and focused tests.
- Record the decision in ADR, CONTEXT, the source plan, and GSD state.

## Acceptance

- Existing grasp-feasibility artifacts remain renderable.
- New diagnostics can distinguish removal calls from effective removals.
- Reports show candidate-name misses and effective-removal counts when present.
- Focused ruff and pytest checks pass.

## Result

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
- robot-placement failures: 0
