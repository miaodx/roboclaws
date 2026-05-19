# MolmoSpaces Missing Grasp Cache Signatures

**Status:** Completed under GSD Phase 110 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0100
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 109 identified the exact bread blocker as missing cached grasps for
`Bread_1`, but proof-result summaries still grouped it as a generic
`grasp_feasibility` pattern. That makes reports less useful for the next
decision because missing cache, zero non-colliding grasps, and generic
post-placement rejection imply different mitigations.

## Decision

Classify missing cached grasps inside the existing grasp-feasibility signature.

This phase should:

- keep `task_feasibility_blocker_kind=grasp_feasibility` for compatibility;
- add a `subkind` such as `grasp_cache_missing`;
- carry grasp-load attempt/failure counts and failed asset UIDs into
  `grasp_feasibility_signature`;
- render the new fields in the shared proof-bundle signature matrix;
- regenerate a runner report from the Phase 109 standalone artifact to prove
  the visual evidence path.

## Non-Goals

- Do not generate grasps or bypass upstream grasp feasibility.
- Do not change planner-proof selection semantics beyond richer signatures.
- Do not claim cleanup readiness from the existing blocked artifact.

## Deliverables

- ADR-0101 and this source plan.
- `.planning/milestones/v1.98-phases/110-molmospaces-missing-grasp-cache-signatures/110-01-missing-grasp-cache-signatures-PLAN.md`.
- Summary/signature support for missing grasp cache subkinds.
- Shared runner report support for subkind and missing asset rows.
- Focused unit coverage and an artifact-derived runner report.

## Verification

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --output-dir output/debug-phase110-missing-grasp-cache-signatures --prior-planner-probe-run-result output/debug-phase109-grasp-collision-diagnostics/run_result.json --exclude-task-feasibility-blocked --generate-fallback-requests`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase110-missing-grasp-cache-signatures/proof_bundle_run_manifest.json`

## Result

The Phase 110 dry-run report regenerated at
`output/debug-phase110-missing-grasp-cache-signatures/report.html` and the
checker passed. Its prior-proof evidence now records one grouped
`grasp_cache_missing` signature with `Bread_1` as the missing grasp asset and
`ValueError` as the grasp-load exception type.
