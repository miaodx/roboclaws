# Phase 66 Plan: MolmoSpaces Fallback Failed Candidate Memory

## Goal

Prevent generated fallback proof selection from retrying runtime aliases and
alias pairs that prior local execution has already proven invalid or
task-feasibility blocked.

## Tasks

1. Carry prior `fallback_generation.discovered_aliases` forward when loading a
   prior proof-bundle manifest.
2. Detect prior generated fallback results with non-root-body object blockers
   and filter those object aliases from future fallback command generation.
3. Detect prior generated fallback results with task-feasibility-blocked
   object/target pairs and filter those exact pairs.
4. Render filtered fallback pairs in the proof-bundle runner report.
5. Extend checker and tests for filtered-pair evidence.
6. Dry-run the current cleanup artifact against the Phase 65 executed bundle as
   prior evidence.

## Acceptance Checks

- Prior discovered runtime aliases survive from a prior runner manifest into
  the next selection pass.
- Object aliases with prior `Object is not a root body` blockers do not appear
  in generated proof commands.
- Exact alias pairs that previously hit `HouseInvalidForTask` do not appear in
  generated proof commands.
- `report.html` shows `Filtered Fallback Pairs`.
- The runner checker validates filtered-pair counts and visible report rows.
- The Phase 66 dry-run passes the runner checker.

## Result

Completed on 2026-05-10.

The selection layer now carries prior discovered aliases forward, filters
known non-root object aliases, and filters previously task-feasibility-blocked
object/target pairs. The proof-bundle runner report now includes a `Filtered
Fallback Pairs` table and a `Filtered pairs` metric.

The dry-run using the Phase 65 manifest generated two remaining proof commands
for `proof_001`, both using the untried book runtime sibling
`book_be4d759484637aeb579b28e6a954b18d_1_2_8`. It filtered six aliases and two
prior blocked pairs, leaving `proof_002` unavailable for this fallback pass.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase66-failed-fallback-candidate-memory-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase65-discovered-runtime-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase66-failed-fallback-candidate-memory-dry-run`
