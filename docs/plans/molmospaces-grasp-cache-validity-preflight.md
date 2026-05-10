# MolmoSpaces Grasp Cache Validity Preflight

**Status:** Completed under GSD Phase 114 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0104
**Workflow:** `hybrid-phase-pipeline`

## Problem

After the upstream droid Bread grasp package is installed, the runtime loader
path for `Bread_1` exists, but `load_grasps_for_object("Bread_1")` still fails.
The installed `Bread_1_grasps_filtered.npz` contains a `transforms` array with
zero rows.

Existence is therefore not a sufficient readiness gate. The report must show
cache validity, not just cache presence.

## Decision

Validate rigid grasp-cache contents during preflight.

The preflight should:

- parse `.npz` files and count the `transforms` entries;
- parse `.json` files and count the `transforms` entries;
- mark a rigid loader file valid only when it contains at least one transform;
- classify an asset as ready only when at least one rigid loader file is valid;
- render validation status and transform counts in the report;
- keep folder-probe-only files out of rigid readiness.

## Non-Goals

- Do not generate replacement grasps in this phase.
- Do not execute a new exact RBY1M/CuRobo proof command.
- Do not treat `has_grasp_folder=True` as proof that
  `load_grasps_for_object` can succeed.

## Deliverables

- ADR-0105 and this source plan.
- `.planning/phases/114-molmospaces-grasp-cache-validity-preflight/114-01-grasp-cache-validity-preflight-PLAN.md`.
- Validation fields in `grasp_cache_availability_preflight`.
- Report columns for valid status, transform count, and validation result.
- Checker and unit coverage.
- Artifact-derived dry-run report for Phase 114.

## Verification

- `/tmp/roboclaws-molmospaces-spike/.venv/bin/python - <<'PY' ... load_grasps_for_object('Bread_1') ... PY`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --output-dir output/debug-phase114-grasp-cache-validity-preflight --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --prior-planner-probe-run-result output/debug-phase109-grasp-collision-diagnostics/run_result.json --exclude-task-feasibility-blocked --generate-fallback-requests`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase114-grasp-cache-validity-preflight/proof_bundle_run_manifest.json --min-selected-requests 9 --max-selected-requests 9`

## Result

The Phase 114 report at
`output/debug-phase114-grasp-cache-validity-preflight/report.html` renders
`Bread_1` as `missing_cache` with `loader_file_status=present_but_invalid`.
The droid candidate file exists, but reports `valid=False`,
`validation_status=empty`, and `transform_count=0`.
