# Phase 73 Plan: MolmoSpaces Pickup Root Alias Normalization

## Goal

Derive pickup root-body aliases from non-root runtime siblings before reporting
them as an unresolved fallback exhaustion blocker.

## Tasks

1. Normalize object-axis runtime aliases with nonzero variants to variant 0.
2. Persist normalized alias rows in fallback-generation manifest evidence.
3. Render normalized alias rows in the proof-bundle runner report.
4. Validate normalized alias counts and report text in the runner checker.
5. Update focused tests for discovered, filtered, carried-forward, and
   exhausted fallback evidence.
6. Dry-run the merged prior evidence artifact and validate the report/checker.

## Acceptance Checks

- Non-root object runtime aliases produce `pickup_root_variant_normalized`
  evidence rows.
- `report.html` includes `Normalized Pickup Root Aliases`.
- Exhaustion blockers omit `pickup_root_body_alias_required` when every
  non-root object alias has a derived root alias.
- The proof-bundle runner checker rejects inconsistent normalized alias counts
  or missing report text.

## Result

Completed on 2026-05-10.

The Phase 73 dry-run normalizes three non-root object aliases to variant-0
pickup root aliases. It still generates zero commands, but the exhausted
fallback report now names the remaining blockers as
`target_task_feasibility_blocked_pairs` and `no_fallback_candidate_available`.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase73-pickup-root-alias-normalization-dry-run`

## Status

Complete.
