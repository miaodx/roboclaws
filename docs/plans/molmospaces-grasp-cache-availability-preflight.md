# MolmoSpaces Grasp Cache Availability Preflight

**Status:** Completed under GSD Phase 112 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0102
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 111 routed `Bread_1` to grasp-cache mitigation, but the report still did
not show whether the local asset cache was missing the object itself or only
the rigid grasp cache consumed by MolmoSpaces' loader.

That distinction matters before generating or restoring cache data. Object
assets being present with loader cache files absent is a different mitigation
than source rotation or scene regeneration.

## Decision

Add a first-class grasp-cache availability preflight to proof-bundle manifests
and reports.

The preflight should:

- read the missing asset IDs from `grasp_feasibility_mitigation_decision`;
- probe the exact rigid loader paths used by
  `molmo_spaces.utils.grasp_sample.load_grasps_for_object`;
- report the droid joint grasp file only as `has_grasp_folder_only`;
- search local THOR object assets for matching XML/OBJ evidence;
- classify each asset as `ready` or `missing_cache`;
- render the result in `report.html` and checker-gate it.

## Non-Goals

- Do not generate new grasp files in this phase.
- Do not execute new RBY1M/CuRobo proof commands.
- Do not claim `Bread_1` is feasible until a later proof clears the loader and
  collision-mask path.

## Deliverables

- ADR-0103 and this source plan.
- `.planning/phases/112-molmospaces-grasp-cache-availability-preflight/112-01-grasp-cache-availability-preflight-PLAN.md`.
- Manifest field `grasp_cache_availability_preflight`.
- Shared report panel `Grasp Cache Availability Preflight`.
- Checker and unit coverage.
- Artifact-derived dry-run report for Phase 112.

## Verification

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --output-dir output/debug-phase112-grasp-cache-availability-preflight --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --prior-planner-probe-run-result output/debug-phase109-grasp-collision-diagnostics/run_result.json --exclude-task-feasibility-blocked --generate-fallback-requests`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase112-grasp-cache-availability-preflight/proof_bundle_run_manifest.json --min-selected-requests 9 --max-selected-requests 9`

## Result

The Phase 112 report at
`output/debug-phase112-grasp-cache-availability-preflight/report.html` renders
`Grasp Cache Availability Preflight` with `status=missing_cache`,
`cache_missing_asset_uids=["Bread_1"]`, object asset status `present`, and
missing rigid loader files for droid, droid-objaverse, and RUM sources.
