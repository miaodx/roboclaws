# Phase 69 Plan: MolmoSpaces Pickup Root Variant Filter

## Goal

Prevent generated fallback proof commands from using object-side runtime aliases
that can be identified as non-root bodies before local execution.

## Tasks

1. Add an object-axis runtime alias filter for nonzero runtime variants.
2. Leave target-axis runtime aliases unaffected by this root-body rule.
3. Render filtered pickup aliases with reason `not_pickup_root_body_alias`.
4. Update focused selection and runner tests.
5. Dry-run the current cleanup artifact against the Phase 62 warmed fallback
   manifest to verify object-side candidates are filtered before command
   generation.

## Acceptance Checks

- Object-axis aliases matching `<prefix>_<group>_<variant>_<room>` with
  `variant != 0` are not used in generated proof commands.
- Target-axis aliases with nonzero variants can still be generated.
- The runner report shows `not_pickup_root_body_alias` filtered rows.
- The Phase 69 dry-run passes the runner checker.

## Result

Completed on 2026-05-10.

The runner now filters non-root pickup runtime variants before fallback command
generation. A dry-run against the Phase 62 warmed fallback evidence generated
two target-side commands and filtered three object-side runtime siblings with
reason `not_pickup_root_body_alias`.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase69-pickup-root-variant-filter-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase69-pickup-root-variant-filter-dry-run`
