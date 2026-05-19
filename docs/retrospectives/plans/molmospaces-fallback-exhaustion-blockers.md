# MolmoSpaces Fallback Exhaustion Blockers

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0063-summarize-fallback-exhaustion-blockers.md`
**GSD phase:** `.planning/milestones/v1.98-phases/72-molmospaces-fallback-exhaustion-blockers/`

## Problem

Phase 71 made exhausted generated fallback pools visible, but the runner report
still made reviewers infer why the pool was exhausted from lower-level filtered
alias and filtered pair tables.

The current local-dev decision needs a direct blocker summary: do we need richer
pickup root-body aliases, upstream task-feasibility handling, or both?

## Scope

- Add exhausted fallback blocker rows to the private fallback-generation
  manifest section.
- Derive blocker rows from existing filtered alias, filtered pair, and
  unavailable source evidence.
- Render `Fallback Exhaustion Blockers` in the proof-bundle runner report.
- Validate blocker counts and report text in the runner checker.
- Update focused tests for exhausted fallback states.
- Dry-run the merged-prior evidence artifact and verify the report/checker.

## Result

The runner now summarizes exhausted fallback pools with stable blocker codes.
The Phase 72 dry-run reports three blockers:

- `pickup_root_body_alias_required` for three object-side non-root aliases;
- `target_task_feasibility_blocked_pairs` for two blocked alias pairs;
- `no_fallback_candidate_available` for two source requests with no remaining
  generated candidate.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase72-fallback-exhaustion-blockers-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase68-filter-carry-forward-dry-run/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase72-fallback-exhaustion-blockers-dry-run`
