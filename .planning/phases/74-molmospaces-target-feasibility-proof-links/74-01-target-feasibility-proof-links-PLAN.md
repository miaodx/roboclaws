# Phase 74 Plan: MolmoSpaces Target Feasibility Proof Links

## Goal

Make target-feasibility filtered fallback pairs point to the exact prior proof
artifacts that established the filter.

## Tasks

1. Merge prior fallback proof results by request ID plus planner object/target
   aliases.
2. Enrich filtered target-feasibility pair rows with proof report, run result,
   worker stage, and status fields.
3. Render the enriched fields in the proof-bundle runner report.
4. Validate enriched pair fields in the runner checker.
5. Update focused tests for colliding fallback IDs and pair artifact links.
6. Dry-run the merged prior evidence artifact with executed Phase 65 and Phase
   67 manifests.

## Acceptance Checks

- Distinct fallback attempts with the same generated request ID but different
  planner aliases are not overwritten during prior merge.
- `Filtered Fallback Pairs` rows include prior proof report paths and last
  worker stage when available.
- The Phase 74 report checker passes on the regenerated dry-run artifact.
- The fallback pool remains exhausted with blockers narrowed to target
  task-feasibility and no remaining candidate.

## Result

Completed on 2026-05-10.

The Phase 74 dry-run renders both target-feasibility filtered pairs with Phase
65 proof report links and `worker_exception` stage evidence.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase74-target-feasibility-proof-links-dry-run`

## Status

Complete.
