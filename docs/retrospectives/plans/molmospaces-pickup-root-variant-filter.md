# MolmoSpaces Pickup Root Variant Filter

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0060-filter-non-root-pickup-runtime-aliases.md`
**GSD phase:** `.planning/milestones/v1.98-phases/69-molmospaces-pickup-root-variant-filter/`

## Problem

The generated fallback path can discover runtime sibling aliases from prior
`KeyError` valid-name lists, but Phase 65 and Phase 67 showed object-side
siblings with nonzero runtime variants are not pickup root bodies. Retrying
them burns local-dev execution time and produces no planner views or binding
promotion.

## Scope

- Filter object-axis runtime aliases whose variant is not `0`.
- Keep target-axis runtime aliases unaffected by this root-body rule.
- Render filtered object aliases with reason `not_pickup_root_body_alias`.
- Update focused selection and runner tests.
- Dry-run the current cleanup artifact against the Phase 62 warmed fallback
  manifest to prove object-side candidates are filtered before execution.

## Result

The proof-bundle runner now filters non-root pickup runtime variants before
generating fallback commands.

The Phase 69 dry-run generated two target-side commands and filtered three
object-side non-root aliases. This matches the local execution evidence from
Phases 65 and 67 while preserving report visibility for the filtered rows.

The current latest-manifest path remains exhausted by Phase 68; the root-variant
filter prevents future regressions when reusing older KeyError evidence or new
valid-name lists.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase69-pickup-root-variant-filter-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase69-pickup-root-variant-filter-dry-run`
