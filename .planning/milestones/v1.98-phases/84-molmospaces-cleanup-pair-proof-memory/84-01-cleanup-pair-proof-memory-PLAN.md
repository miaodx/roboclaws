# Phase 84 Plan: MolmoSpaces Cleanup-Pair Proof Memory

## Goal

Match prior proof-result memory by cleanup object/target pair when request IDs
change across regenerated proof manifests.

## Tasks

1. Add a cleanup-pair prior-result index.
2. Prefer request-id matches, then fall back to object/target matches.
3. Record `prior_result_match_kind` in selection artifacts.
4. Render `Prior match` in proof-bundle runner reports.
5. Add focused tests for request-id and object/target match behavior.

## Acceptance Checks

- Focused ruff checks pass for changed implementation, checker, and tests.
- Focused pytest covers regenerated request ID fallback matching.
- Runner report tests cover the visible `Prior match` field.

## Result

Implemented.

Selection memory now follows cleanup-facing identity when needed:
`prior_result_match_kind=request_id` for exact matches and
`prior_result_match_kind=object_target` for regenerated request IDs with the
same cleanup object/target pair.

Focused validation passed:

- `uv run ruff check` on changed implementation, checker, and test files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- Manual regenerated-request selection check reports
  `prior_result_match_kind=object_target`.

## Status

Complete.
