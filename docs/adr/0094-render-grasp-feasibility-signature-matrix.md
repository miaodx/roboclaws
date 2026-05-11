# 0094. Render Grasp Feasibility Signature Matrix

Date: 2026-05-10

## Status

Accepted

## Context

Phase 102 executed five selected seed 10 proof commands. Every command reached
task sampling, cleared robot placement, and then blocked with the same
grasp-feasibility shape: 17 grasp failures, 15 candidate-removal calls, and one
diagnostic view artifact.

The code could classify these blockers, but the classification and summary
logic lived inside `planner_proof_requests.py`. Reports and checkers consumed
the resulting strings without a shared task-feasibility module or a bundle-level
signature view.

## Decision

Create a shared planner task-feasibility module that owns blocker kind,
blocker summary, per-proof grasp signatures, and bundle-level signature groups.

Render those signature groups in proof-bundle reports as a
`Grasp Feasibility Signature Matrix`, and make the checker validate the matrix
when signature groups are present.

## Consequences

- Task-feasibility blocker naming is centralized instead of buried in runner
  summary construction.
- Repeated grasp-feasibility failures are reviewable as one blocker pattern
  across many proof rows.
- Phase 102's five blocked proofs collapse into one signature group in the
  regenerated Phase 103 report.
- This does not make blocked proofs planner-backed; it makes the blocker easier
  to compare before deciding whether to change task-sampler tuning, proof
  source selection, or candidate generation.

## Evidence

Implemented in Phase 103 on 2026-05-10.

Artifacts:

- `output/debug-phase103-grasp-signature-report/proof_bundle_run_manifest.json`
- `output/debug-phase103-grasp-signature-report/report.html`

Key results:

- regenerated signature count: 1
- grouped proof count: 5
- grouped pattern: `17 grasp failures; 15 candidate-removal calls`
- grouped diagnostic views: 5

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase103-grasp-signature-report/proof_bundle_run_manifest.json --min-selected-requests 0 --require-proof-outputs`
