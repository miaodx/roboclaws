# 56-01 Proof Request Feasibility Selection Plan

## Goal

Add a bounded proof-request selection seam so local proof-bundle runs can skip
requests already known to be exact-scene RBY1M task-feasibility blocked and
report when fallback generation is required.

## Tasks

1. Add ADR/source-plan context for proof request feasibility selection.
2. Add manifest-level request selection from prior proof-result summaries.
3. Filter generated proof commands through that selection.
4. Render selected/excluded requests and fallback-required status in runner
   reports.
5. Extend the runner checker and focused tests.
6. Update roadmap/state/context docs with the Phase 56 result.

## Verification

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py`

## Result

Implemented. Proof-bundle runner manifests now include
`planner_cleanup_proof_request_selection_v1`; the runner can load a prior
proof-bundle manifest, exclude requests with prior
`task_feasibility_status=blocked`, filter generated probe commands to selected
requests, and render selected/excluded requests plus fallback-required state in
the runner report. The remaining work is generating alternate RBY1M-feasible
requests when every exact cleanup request is excluded.
