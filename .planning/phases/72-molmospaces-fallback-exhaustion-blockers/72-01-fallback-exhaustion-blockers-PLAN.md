# Phase 72 Plan: MolmoSpaces Fallback Exhaustion Blockers

## Goal

Make exhausted generated-fallback pools report the concrete blocker categories
that prevent new proof commands.

## Tasks

1. Derive fallback exhaustion blocker rows from filtered alias, filtered pair,
   and unavailable source evidence.
2. Persist blocker count and rows in the fallback-generation manifest section.
3. Render blocker rows in the proof-bundle runner report.
4. Validate blocker counts and report text in the runner checker.
5. Update focused unit tests for exhausted fallback states.
6. Dry-run the merged prior evidence artifact and validate the report/checker.

## Acceptance Checks

- Exhausted fallback generation includes at least one blocker row.
- The merged-prior dry-run reports blockers for pickup root-body alias gaps,
  target task-feasibility blocked pairs, and unavailable source requests.
- `report.html` includes `Fallback Exhaustion Blockers`.
- The proof-bundle runner checker rejects inconsistent blocker counts or report
  text.

## Result

Completed on 2026-05-10.

The Phase 72 dry-run reports `Fallback status: exhausted`, zero generated
commands, and three explicit blocker rows:
`pickup_root_body_alias_required`, `target_task_feasibility_blocked_pairs`, and
`no_fallback_candidate_available`.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase72-fallback-exhaustion-blockers-dry-run`

## Status

Complete.
