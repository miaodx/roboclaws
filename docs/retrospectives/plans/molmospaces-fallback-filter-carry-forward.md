# MolmoSpaces Fallback Filter Carry-Forward

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/archive/execution-log/0059-carry-forward-filtered-fallback-candidates.md`
**GSD phase:** `.planning/milestones/v1.98-phases/68-molmospaces-fallback-filter-carry-forward/`

## Problem

Phase 67 proved the remaining discovered book runtime sibling is also a
non-root body. The runner already rendered earlier filtered aliases and pairs,
but those filtered rows were not themselves carried forward as active filters.
That made the latest manifest a weak prior input for the next fallback
generation pass.

## Scope

- Carry prior filtered fallback aliases forward from a prior proof-bundle
  manifest.
- Carry prior filtered fallback pairs forward from a prior proof-bundle
  manifest.
- Keep those carried filters visible in the next runner report.
- Add focused tests for selection exhaustion.
- Dry-run the current cleanup artifact using the Phase 67 executed bundle as
  prior evidence.

## Result

The runner now carries prior filtered aliases and filtered pairs forward.

The Phase 68 dry-run against
`output/debug-phase67-filtered-fallback-execute/proof_bundle_run_manifest.json`
generated no proof commands. It still rendered the five discovered aliases,
seven filtered aliases, and two filtered pairs. Both source requests are now
unavailable through the current fallback candidate pool, so the next useful
slice is pickup root-body alias derivation or validation.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase68-filter-carry-forward-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase67-filtered-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase68-filter-carry-forward-dry-run`
