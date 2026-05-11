# MolmoSpaces Grasp Feasibility Signature Matrix

**Status:** Completed under GSD Phase 103 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0094, Phase 102 repeated grasp-feasibility blocker evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 102 showed five selected seed 10 proof commands all blocking with the
same grasp-feasibility shape. The report rendered each proof row, but the
bundle-level view did not collapse repeated failures into a single blocker
pattern. The task-feasibility naming logic also lived inside
`planner_proof_requests.py`, making it a shallow module for blocker taxonomy.

## Decision

Add a shared planner task-feasibility module and render bundle-level
grasp-feasibility signature groups in proof-bundle reports.

## Non-Goals

- Do not change proof execution behavior.
- Do not treat grouped blockers as planner-backed readiness.
- Do not rerun RBY1M/CuRobo probes.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- Task-feasibility blocker kind/summary calculation lives in a shared module.
- Proof result summaries include per-proof grasp signatures and grouped
  signature counts.
- Proof-bundle reports render `Grasp Feasibility Signature Matrix`.
- The runner checker validates signature groups when present.
- Focused ruff and pytest checks pass.

## Result

Complete on 2026-05-10.

Implemented:

- `roboclaws/molmo_cleanup/planner_task_feasibility.py`
- proof result `grasp_feasibility_signature` fields
- summary-level `grasp_feasibility_signature_counts`
- proof-bundle report `Grasp Feasibility Signature Matrix`
- checker validation for signature groups

Evidence:

- Regenerated report: `output/debug-phase103-grasp-signature-report/report.html`
- Regenerated manifest: `output/debug-phase103-grasp-signature-report/proof_bundle_run_manifest.json`

Observed result:

- Phase 102's five proof blockers group into one signature:
  `17 grasp failures; 15 candidate-removal calls`.

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase103-grasp-signature-report/proof_bundle_run_manifest.json --min-selected-requests 0 --require-proof-outputs`
