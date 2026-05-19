# MolmoSpaces Runtime Assets Grasp Cache Preflight

**Status:** Completed under GSD Phase 113 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0103
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 112 made the missing rigid `Bread_1` grasp cache visible, but the report
used the data-cache root as the displayed assets directory. The runtime loader
uses MolmoSpaces' `ASSETS_DIR`, which is often a symlink-root under
`~/.cache/molmospaces/assets/<install-hash>`.

Before generating or restoring cache data, the report should show both the
runtime loader path and the symlink-resolved data-cache target.

## Decision

Bind grasp-cache availability preflight to `planner_scene.scene_xml`.

The preflight should:

- derive the runtime assets root from the first `scenes` ancestor in the planner
  scene XML path;
- use that root before falling back to environment/default roots;
- keep loader-relative paths unchanged;
- record symlink-resolved paths for loader probes and object asset probes;
- render those resolved paths in the shared proof-bundle report;
- validate the fields through the proof-bundle checker.

## Non-Goals

- Do not generate new grasp files in this phase.
- Do not execute new RBY1M/CuRobo proof commands.
- Do not change the cleanup report visual underlay or semantic subphase labels.

## Deliverables

- ADR-0104 and this source plan.
- `.planning/milestones/v1.98-phases/113-molmospaces-runtime-assets-grasp-cache-preflight/113-01-runtime-assets-grasp-cache-preflight-PLAN.md`.
- `assets_dir_source=planner_scene` in proof-bundle preflight manifests.
- Resolved loader/object paths in `Grasp Cache Availability Preflight`.
- Checker and unit coverage.
- Artifact-derived dry-run report for Phase 113.

## Verification

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --output-dir output/debug-phase113-runtime-assets-grasp-cache-preflight --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --prior-planner-probe-run-result output/debug-phase109-grasp-collision-diagnostics/run_result.json --exclude-task-feasibility-blocked --generate-fallback-requests`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase113-runtime-assets-grasp-cache-preflight/proof_bundle_run_manifest.json --min-selected-requests 9 --max-selected-requests 9`

## Result

The Phase 113 report at
`output/debug-phase113-runtime-assets-grasp-cache-preflight/report.html`
renders `Grasp Cache Availability Preflight` with
`assets_dir_source=planner_scene`, the runtime `ASSETS_DIR` root, and resolved
cache targets such as
`~/.cache/molmo-spaces-resources/grasps/droid/20251116/Bread_1/Bread_1_grasps_filtered.npz`.
