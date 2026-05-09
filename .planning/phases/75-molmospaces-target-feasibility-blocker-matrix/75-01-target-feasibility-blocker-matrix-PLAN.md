# Phase 75 Plan: MolmoSpaces Target Feasibility Blocker Matrix

## Goal

Make the remaining target-feasibility blockers visible in one proof-bundle
runner report view that covers both source requests and generated fallback
pairs.

## Tasks

1. Add selection-owned target-feasibility blocker rows to proof request
   selection.
2. Preserve optional prior proof artifact and worker-stage fields for excluded
   source requests.
3. Render `Target Feasibility Blockers` in the shared proof-bundle runner
   report.
4. Validate blocker counts and report text in the runner checker.
5. Update focused tests for manifest, runner, report, and checker behavior.
6. Dry-run the current artifact chain with Phase 57, 62, 65, and 67 prior
   manifests.

## Acceptance Checks

- The manifest includes `target_feasibility_blocker_count` and
  `target_feasibility_blockers`.
- The report renders source request blockers and fallback pair blockers in one
  table.
- Existing filtered fallback pair proof links remain visible.
- The checker passes on the regenerated Phase 75 dry-run artifact.
- The fallback pool remains exhausted with the same upstream task-feasibility
  blocker classification.

## Result

Completed on 2026-05-10.

The Phase 75 dry-run rendered four target-feasibility blockers: two source
request rows without proof links in the available evidence, and two fallback
pair rows with Phase 65 proof report links and `worker_exception` stage.

## Validation

- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase75-target-feasibility-blocker-matrix-dry-run`

## Status

Complete.
