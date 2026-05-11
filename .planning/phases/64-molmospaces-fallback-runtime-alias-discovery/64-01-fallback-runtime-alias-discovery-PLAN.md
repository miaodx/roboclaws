# Phase 64 Plan: MolmoSpaces Fallback Runtime Alias Discovery

## Goal

Generate executable fallback proof commands from exact-scene runtime alias
siblings discovered in prior `KeyError` proof outputs.

## Tasks

1. Mine prior fallback proof `KeyError` blocker messages for exact-scene
   valid-name lists.
2. Derive same-family runtime sibling aliases for the source cleanup request's
   object or target.
3. Merge prior runner excluded-source evidence into the prior result summary so
   a warmed fallback bundle can drive the next fallback generation pass.
4. Render discovered aliases in the proof-bundle runner report and validate
   them through the checker.
5. Dry-run the runner against the current cleanup artifact with the Phase 62
   warmed fallback manifest as prior evidence.

## Acceptance Checks

- Prior `KeyError` valid-name lists produce runtime sibling aliases only when
  they match the source request's current runtime object/target family.
- Discovered aliases appear in generated fallback proof commands.
- Upstream/display aliases remain filtered and visible.
- The runner report includes a `Discovered Runtime Aliases` table.
- The dry-run produces generated commands and passes the runner checker.

## Result

Completed on 2026-05-10.

The runner now discovers runtime sibling aliases from prior exact-scene
`KeyError` proof outputs. The dry-run using the Phase 62 warmed fallback bundle
as prior evidence generated four new fallback proof commands and rendered five
discovered aliases in `report.html`.

The next blocker is local execution of those newly generated runtime-sibling
fallback commands.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase64-runtime-alias-discovery-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase64-runtime-alias-discovery-dry-run`
