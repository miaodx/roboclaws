# MolmoSpaces Proof Bundle Request Filter

**Status:** Completed under GSD Phase 133 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0122, ADR-0123, `CONTEXT.md`, `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

The stricter two-step proof-bundle dry-run for the Phase 126 cleanup artifact
selects ten ready proof requests. Executing all ten is a broad local RBY1M/CuRobo
job, but the next useful proof attempt should be one cleanup object at a time.

## Decision

Add explicit request-id filtering to the proof-bundle runner.

The runner accepts repeatable `--request-id` flags, applies them before the
existing exclusion modes, records a `request_filter` block in the manifest, and
renders a `Request ID Filter` table in the report. The checker validates that
view when present.

## Non-Goals

- Do not execute a real RBY1M/CuRobo proof in this phase.
- Do not change fallback generation semantics.
- Do not hide the full ready-request count.
- Do not remove the full-bundle execution path.

## Acceptance Criteria

- CLI supports repeatable `--request-id`.
- Selection output records requested/matched/unavailable/missing request IDs.
- Runner reports render `Request ID Filter`.
- Runner checker validates request filter report content.
- A bounded dry-run against the Phase 126 cleanup artifact selects exactly one
  request.
- Focused lint, format, pytest, and bounded dry-run artifact gate pass.

## Result

Complete.

`--request-id proof_001` reduces the Phase 126 stricter dry-run from ten proof
commands to one, while preserving Proof Execution Horizon and Semantic
Subphases views in the report.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_filters_to_requested_request_ids tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_valid_runner_artifact`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase133-request-filter-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase133-request-filter-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`
