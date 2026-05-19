# MolmoSpaces Grasp Cache Generation Preflight

**Status:** Completed under GSD Phase 116 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0107
**Workflow:** `hybrid-phase-pipeline`

## Problem

`Bread_1` still lacks a valid rigid grasp cache. The installed droid package
contains an empty `Bread_1_grasps_filtered.npz`, so exact proof retry remains
blocked.

The upstream MolmoSpaces generator exists, but generation has local
prerequisites that were not visible in proof-bundle runner reports.

## Decision

Add a report-visible generation preflight to the proof-bundle runner.

The preflight should show:

- the missing-cache asset that needs generation;
- object XML and generated NPZ paths;
- final loader cache target path;
- proposed upstream `run_rigid.py` command;
- Python module/runtime checks;
- Manifold executable checks;
- explicit blockers.

## Non-Goals

- Do not install Python packages in this phase.
- Do not build Manifold in this phase.
- Do not synthesize or install fake grasps.
- Do not rerun exact RBY1M/CuRobo proof while generation is blocked.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --output-dir output/debug-phase116-grasp-cache-generation-preflight --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --prior-planner-probe-run-result output/debug-phase109-grasp-collision-diagnostics/run_result.json --exclude-task-feasibility-blocked --generate-fallback-requests`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase116-grasp-cache-generation-preflight/proof_bundle_run_manifest.json --min-selected-requests 9 --max-selected-requests 9`

## Result

The Phase 116 report renders `Grasp Cache Generation Preflight` with
`status=blocked`. `Bread_1` object XML is present, the target loader cache path
is visible, and the proposed `run_rigid.py` command is recorded.

Current blockers are `sklearn_missing`, `python_fcl_missing`,
`manifold_executable_missing`, and `simplify_executable_missing`.
