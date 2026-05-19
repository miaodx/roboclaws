# Phase 68 Plan: MolmoSpaces Fallback Filter Carry-Forward

## Goal

Carry prior filtered fallback aliases and pairs forward so the latest executed
bundle manifest is a complete prior input for the next fallback-generation
pass.

## Tasks

1. Treat prior `fallback_generation.filtered_aliases` as active alias filters.
2. Treat prior `fallback_generation.filtered_pairs` as active pair filters.
3. Preserve visible filtered rows in the next proof-bundle runner report.
4. Add focused selection tests for filter carry-forward and exhausted fallback
   generation.
5. Dry-run the current cleanup artifact against the Phase 67 executed bundle as
   prior evidence.

## Acceptance Checks

- Prior filtered non-root object aliases do not regenerate as fallback proof
  commands.
- Prior filtered exact object/target pairs do not regenerate as fallback proof
  commands.
- The dry-run using the Phase 67 manifest generates zero commands.
- The dry-run report still renders discovered aliases, filtered aliases, and
  filtered pairs.
- The runner checker passes for the dry-run artifact.

## Result

Completed on 2026-05-10.

The selection layer now carries prior filtered aliases and filtered pairs
forward. The Phase 68 dry-run using the Phase 67 manifest generated zero proof
commands, reported `fallback_required=true`, and rendered five discovered
aliases, seven filtered aliases, and two filtered pairs.

Both original source requests are unavailable through the current fallback pool.
The next blocker is root-body pickup alias derivation or validation.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase68-filter-carry-forward-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase67-filtered-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase68-filter-carry-forward-dry-run`
