# MolmoSpaces Fallback Exhaustion Status

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0062-surface-fallback-exhaustion-status.md`
**GSD phase:** `.planning/milestones/v1.98-phases/71-molmospaces-fallback-exhaustion-status/`

## Problem

The merged prior evidence path can correctly generate zero fallback commands
when all known candidates are filtered. Before this slice, that state was
implicit: reviewers had to combine `fallback_required=true`, zero generated
requests, empty command tables, and filtered rows.

## Scope

- Add fallback-generation `status` values for disabled, not-required,
  generated, and exhausted states.
- Render `Fallback status` in the proof-bundle runner report.
- Validate fallback status in the runner checker.
- Update focused tests for generated and exhausted fallback states.
- Dry-run the merged-prior evidence artifact and verify the report/checker.

## Result

The runner now classifies fallback generation directly. The Phase 71 dry-run
renders `Fallback status: exhausted` alongside the discovered aliases, filtered
aliases, and filtered pairs that explain why no command remains.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase71-fallback-exhaustion-status-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase68-filter-carry-forward-dry-run/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase71-fallback-exhaustion-status-dry-run`
