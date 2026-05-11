# MolmoSpaces Target Feasibility Blocker Matrix

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0066-render-target-feasibility-blocker-matrix.md`
**GSD phase:** `.planning/phases/75-molmospaces-target-feasibility-blocker-matrix/`

## Problem

Phase 74 linked target-feasibility filtered fallback pairs to their prior proof
artifacts, but the report still made reviewers combine two tables to understand
the blocker:

- original source requests blocked by prior task feasibility;
- generated fallback pairs blocked by prior task feasibility.

That split left a visual gap in the proof-bundle runner report and made the
remaining upstream task-feasibility blocker less obvious.

## Scope

- Add manifest-level `target_feasibility_blockers` evidence owned by proof
  request selection.
- Include both source request blockers and generated fallback pair blockers.
- Preserve optional proof links and worker-stage evidence when available.
- Render one `Target Feasibility Blockers` table in the shared runner report.
- Validate the count and row values in the runner checker.
- Dry-run against Phase 57, 62, 65, and 67 prior manifests to prove the report
  view over the current real artifact chain.

## Result

The Phase 75 dry-run reports four target-feasibility blockers:

- two `source_request` rows for the original cleanup proof requests;
- two `fallback_pair` rows for generated runtime-alias target pairs;
- the fallback-pair rows link to Phase 65 proof reports and show
  `worker_exception`.

The fallback pool remains exhausted with no generated commands.

## Validation

- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase75-target-feasibility-blocker-matrix-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase65-discovered-runtime-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase67-filtered-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase75-target-feasibility-blocker-matrix-dry-run`
