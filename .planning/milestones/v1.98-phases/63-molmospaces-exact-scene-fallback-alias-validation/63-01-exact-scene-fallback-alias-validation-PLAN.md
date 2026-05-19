# Phase 63 Plan: MolmoSpaces Exact-Scene Fallback Alias Validation

## Goal

Prevent generated fallback proof commands from using upstream/display aliases
that are not valid MolmoSpaces exact-scene runtime planner names.

## Tasks

1. Filter fallback alias candidates before generating proof commands.
2. Render filtered alias evidence in the proof-bundle runner report.
3. Extend the runner checker to validate filtered alias evidence.
4. Add focused tests for fallback filtering, report visibility, and checker
   coverage.
5. Dry-run the runner against the existing local cleanup artifact and prior
   feasibility-blocked proof bundle.

## Acceptance Checks

- Fallback generation does not produce commands for aliases containing the
  upstream/display `|` delimiter.
- Runner reports include a `Filtered Fallback Aliases` table when aliases are
  skipped.
- The checker rejects stale reports that omit filtered alias evidence.
- The local dry-run reports the four previously failing aliases as filtered and
  produces zero invalid fallback commands.

## Result

Completed on 2026-05-10.

Generated fallback request selection now separates private alias metadata from
executable planner command inputs. Runtime-style aliases can still produce
fallback requests; upstream/display aliases such as `Book|surface|8|79` and
`Sink|5|1|0` are filtered and reported instead.

The dry-run for the current local artifact selected no fallback commands after
filtering, excluded both prior task-feasibility-blocked source requests, and
reported four filtered aliases. The next blocker is finding or deriving new
exact-scene runtime aliases, not retrying display IDs.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase63-alias-filter-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase63-alias-filter-dry-run`
