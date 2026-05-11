# MolmoSpaces Grasp Cache Routing Decision

**Status:** Completed under GSD Phase 111 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0101
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 110 made missing cached grasps visible as
`subkind=grasp_cache_missing`, but the proof-bundle runner still did not make a
clear next-step decision. The broader plan needs to choose between source
rotation and direct missing-cache mitigation before another runtime attempt.

## Decision

Add a first-class grasp-feasibility mitigation decision to proof-bundle
manifests and reports.

The decision should:

- scan prior and current proof-result signature groups;
- route any missing cached grasp asset to `grasp_cache_mitigation`;
- keep source rotation state visible as a separate field;
- render a visual decision panel in `report.html`;
- be checker-gated when present.

## Non-Goals

- Do not generate missing grasp caches in this phase.
- Do not execute new RBY1M/CuRobo proof commands.
- Do not claim `Bread_1` is feasible until a later proof clears the loader and
  collision-mask path.

## Deliverables

- ADR-0102 and this source plan.
- `.planning/phases/111-molmospaces-grasp-cache-routing-decision/111-01-grasp-cache-routing-decision-PLAN.md`.
- Manifest field `grasp_feasibility_mitigation_decision`.
- Shared report panel `Grasp Feasibility Mitigation Decision`.
- Checker and unit coverage.
- Artifact-derived dry-run report for Phase 111.

## Verification

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --output-dir output/debug-phase111-grasp-cache-routing-decision --prior-planner-probe-run-result output/debug-phase109-grasp-collision-diagnostics/run_result.json --exclude-task-feasibility-blocked --generate-fallback-requests`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase111-grasp-cache-routing-decision/proof_bundle_run_manifest.json`

## Result

The Phase 111 report at
`output/debug-phase111-grasp-cache-routing-decision/report.html` renders
`Grasp Feasibility Mitigation Decision` with
`primary_route=grasp_cache_mitigation`,
`recommendation=mitigate_missing_grasp_cache_before_retry`,
`missing_grasp_asset_uids=["Bread_1"]`, and
`source_rotation_state=available_for_unproven_requests`.
