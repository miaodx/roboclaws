# MolmoSpaces Exact-Scene Fallback Alias Validation

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0054-filter-fallback-aliases-to-exact-scene-runtime-names.md`
**GSD phase:** `.planning/milestones/v1.98-phases/63-molmospaces-exact-scene-fallback-alias-validation/`

## Problem

The warmed generated fallback proof run got past RBY1M/CuRobo config import and
reached task sampling, but all four generated fallback probes failed with
`KeyError` invalid planner aliases. The failing aliases were upstream/display
names, not exact-scene runtime names:

- `Book|surface|8|79`
- `ShelvingUnit|2|3`
- `Bowl|surface|8|77`
- `Sink|5|1|0`

The runner needs to keep that alias metadata visible without turning it into
executable proof commands.

## Scope

- Filter generated fallback aliases before command generation.
- Keep filtered aliases visible in the runner manifest and report.
- Extend the runner checker so filtered-alias evidence cannot silently drop out
  of `report.html`.
- Dry-run the selection against the existing local cleanup artifact and prior
  feasibility-blocked proof bundle.

## Result

Fallback generation now filters upstream/display aliases containing `|` before
building executable commands. The proof-bundle runner report includes a
`Filtered Fallback Aliases` table and a `Filtered aliases` metric.

The local dry-run against `output/debug-real-binding/run_result.json` and
`output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json` produced:

- `selected_count=0`
- `excluded_count=2`
- `generated_fallback_request_count=0`
- `fallback_required=true`
- `filtered_alias_count=4`

This means the current artifact has no alternate executable fallback aliases
after exact-scene filtering. That is preferable to rerunning invalid fallback
commands that fail at task sampling.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase63-alias-filter-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase57-prior-blocked/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase63-alias-filter-dry-run`
