# 0089. Render Grasp-Feasibility Blocker Matrix

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0074 preserved grasp-feasibility blocker memory through proof request
selection, and ADR-0088 rendered the per-proof post-placement rejection flow.
The remaining review gap is selection-level: a broader proof-bundle report can
exclude many object/target pairs as grasp-infeasible, but the report still
relies on a dense table to show which pairs are blocking the next source
rotation.

## Decision

Render a `Grasp Feasibility Blocker Matrix` inside the existing proof request
selection section whenever selection carries grasp-feasibility blockers. The
matrix is a compact card view over the same blocker data already used by the
table:

- object or planner alias;
- target receptacle or target alias;
- source request;
- match kind;
- blocker summary.

The detailed `Grasp Feasibility Blockers` table remains as audit evidence.
Checker coverage requires the matrix when grasp blockers are present.

## Consequences

- Broader proof-bundle reports show the current retry blocker as a visual set
  of object-target pairs before readers inspect table rows.
- No proof selection behavior changes.
- The matrix uses the shared proof-bundle report renderer instead of adding a
  separate report implementation.

## Evidence

Implemented in Phase 98 on 2026-05-10.

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py`
