# MolmoSpaces Grasp-Feasibility Blocker Matrix

**Status:** Completed under GSD Phase 98 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0074, ADR-0088, ADR-0089
**Workflow:** `hybrid-phase-pipeline`

## Problem

The broader proof-bundle report can preserve grasp-feasibility blocker memory,
but the selection-level state is still table-first. After Phase 95, the next
human decision is whether to rotate proof sources or reduce the shared
grasp-feasibility blocker. That decision needs a quick visual read of which
object-target pairs are already blocked.

## Decision

Render a `Grasp Feasibility Blocker Matrix` in the proof request selection
section. The matrix reuses the existing blocker data and sits next to the
existing detailed table.

## Non-Goals

- Do not change proof request selection.
- Do not execute new MolmoSpaces proofs.
- Do not replace the detailed blocker table.
- Do not treat a visual blocker matrix as planner-backed cleanup readiness.

## Acceptance Criteria

- Proof-bundle reports with `grasp_feasibility_blockers` render a visual
  `Grasp Feasibility Blocker Matrix`.
- The matrix shows object/target route, source request, prior match, and
  blocker summary.
- The runner checker requires the matrix when grasp blockers are present.
- Focused lint and pytest pass.

## Result

Complete on 2026-05-10.

Implemented:

- selection-level grasp blocker matrix renderer;
- proof-bundle report integration before the detailed blocker table;
- checker assertion for matrix presence;
- focused report/checker tests.

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py`
