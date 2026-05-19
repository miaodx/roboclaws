# MolmoSpaces Fallback Timeout Stage Reporting

**Status:** Completed in GSD Phase 60 on 2026-05-10
**Source:** Phase 58 local evidence, CONTEXT.md, ADR-0051
**Workflow:** `hybrid-phase-pipeline`

## Problem

Generated fallback execution now produces proof outputs, but the bundle report
collapses all four Phase 58 failures to `timeout`. The per-proof artifacts have
`last_worker_stage=rby1m_config_import` and compact stage events in stdout, but
the bundle-level report does not surface them.

## Decision

Add timeout-stage evidence to the proof result summary and runner report.

This phase should:

- copy compact worker stage events from each proof result into the bundle
  summary;
- record the last worker stage and execution-attempted state per proof;
- surface stdout/stderr paths in the result card;
- add bundle-level timeout counts, including `rby1m_config_import` timeouts;
- update tests and checker coverage.

## Result

Completed in code and tests. This is a report/diagnostic slice only; generated
fallback proof success and cleanup primitive promotion remain blocked until a
future local runtime slice gets past `rby1m_config_import`.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
