# Phase 103-01: Grasp Feasibility Signature Matrix

## Goal

Deepen planner task-feasibility blocker handling so repeated
grasp-feasibility failures are summarized through a shared module and one
bundle-level report view.

## Tasks

- Extract task-feasibility blocker kind/summary logic from proof request
  summary code into a shared module.
- Add per-proof grasp-feasibility signatures.
- Add grouped signature counts to proof result summaries.
- Render grouped signatures in proof-bundle reports.
- Extend checker and focused tests.
- Regenerate a local report from the Phase 102 proof outputs without rerunning
  probes.

## Acceptance

- Focused ruff and pytest checks pass.
- The checker validates the regenerated Phase 103 report.
- The report shows Phase 102's five proof blockers as one repeated grasp
  signature.
- The phase does not claim planner-backed proof or cleanup-binding promotion.

## Result

Complete on 2026-05-10.

Implemented:

- `roboclaws/molmo_cleanup/planner_task_feasibility.py`
- `grasp_feasibility_signature` on proof result rows
- `grasp_feasibility_signature_counts` in proof result summaries
- `Grasp Feasibility Signature Matrix` in proof-bundle runner reports
- checker validation for signature groups

Evidence:

- `output/debug-phase103-grasp-signature-report/proof_bundle_run_manifest.json`
- `output/debug-phase103-grasp-signature-report/report.html`

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase103-grasp-signature-report/proof_bundle_run_manifest.json --min-selected-requests 0 --require-proof-outputs`
