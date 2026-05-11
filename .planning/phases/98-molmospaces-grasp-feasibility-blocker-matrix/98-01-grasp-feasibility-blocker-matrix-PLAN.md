# Phase 98-01: Grasp-Feasibility Blocker Matrix

## Goal

Make proof-bundle selection reports visually show the object-target pairs that
are already excluded as grasp-feasibility blockers.

## Tasks

- Add a selection-level grasp-feasibility blocker matrix renderer.
- Keep the existing detailed blocker table as audit evidence.
- Require the matrix in the proof-bundle runner checker when grasp blockers
  exist.
- Add focused report/checker tests.
- Update ADR, plan, CONTEXT, and planning state.

## Acceptance

- Reports with `grasp_feasibility_blockers` include
  `Grasp Feasibility Blocker Matrix`.
- The matrix is rendered by the shared proof-bundle report path.
- Checker and focused tests cover the new visual.
- The phase is committed with code, tests, and docs.

## Result

Complete on 2026-05-10.

Implemented:

- compact grasp blocker matrix cards in `Proof Request Selection`;
- checker coverage for matrix presence;
- focused report/checker tests.

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py`
