# MolmoSpaces Pickup Root Alias Normalization

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/archive/execution-log/0064-normalize-pickup-root-runtime-aliases.md`
**GSD phase:** `.planning/milestones/v1.98-phases/73-molmospaces-pickup-root-alias-normalization/`

## Problem

Phase 72 showed a `pickup_root_body_alias_required` blocker, but the current
runtime alias names contain an obvious local normalization rule: object aliases
with nonzero variants can be mapped back to variant 0 for the same
prefix/group/room.

Before looking for a new upstream source, the runner should derive and report
that root alias normalization inside the existing fallback-selection interface.

## Scope

- Normalize object-axis runtime aliases with nonzero variants to variant 0.
- Carry normalized alias rows in fallback-generation manifest evidence.
- Render a `Normalized Pickup Root Aliases` table in the proof-bundle runner
  report.
- Validate normalized alias counts and report text in the checker.
- Update tests for generated, exhausted, and carried-forward fallback evidence.
- Dry-run the merged prior evidence artifact and verify the report/checker.

## Result

The runner now derives pickup root aliases from non-root runtime siblings. The
Phase 73 dry-run normalized three aliases:

- two book aliases to `book_be4d759484637aeb579b28e6a954b18d_1_0_8`;
- one bowl alias to `bowl_46a21212675e4d90993a86b1232e6f40_1_0_8`.

No new proof commands were generated because the resulting root-alias pairs are
already filtered or unavailable. The report now shows the remaining blockers as
target task-feasibility-blocked pairs and no remaining generated candidate.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase73-pickup-root-alias-normalization-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase68-filter-carry-forward-dry-run/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase73-pickup-root-alias-normalization-dry-run`
