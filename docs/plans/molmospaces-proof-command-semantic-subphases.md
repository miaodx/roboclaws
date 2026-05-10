# MolmoSpaces Proof Command Semantic Subphases

**Status:** Completed under GSD Phase 132 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0122, `CONTEXT.md`, `docs/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Proof-bundle dry-run reports showed the requested proof execution horizon, but
the individual command rows did not visibly carry the cleanup semantic subphase
sequence the command was meant to prove.

That left a review gap between "this command is for object X to target Y" and
"this command corresponds to the shared `nav, pick, nav, open?, place` cleanup
underlay."

## Decision

Carry semantic subphase metadata on each generated proof command and render it
in the proof-bundle runner report.

Each command row now keeps the raw cleanup tools plus display-ready subphase
entries with label and role detail. The report renders those entries as a
semantic rail, and the runner checker validates the rail whenever command rows
include it.

## Non-Goals

- Do not execute new RBY1M/CuRobo proofs.
- Do not claim planner-backed cleanup from command intent.
- Do not change proof request selection or fallback generation.
- Do not add a second report visual system.

## Acceptance Criteria

- Generated proof command manifest rows include `tools`.
- Generated proof command manifest rows include `semantic_subphases`.
- Proof-bundle runner reports render `Semantic subphases` in command rows.
- The runner checker validates semantic subphase labels/details when present.
- Focused lint, format, pytest, and one dry-run artifact gate pass.

## Result

Complete.

The proof-bundle runner now keeps proof command intent aligned with the shared
cleanup report vocabulary. The fresh dry-run report renders command rows as a
semantic subphase rail before local proof execution.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_valid_runner_artifact`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase132-proof-command-subphases-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase132-proof-command-subphases-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1`
