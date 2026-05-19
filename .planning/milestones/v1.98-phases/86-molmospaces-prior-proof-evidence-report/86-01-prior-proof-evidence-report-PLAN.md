# Phase 86 Plan: MolmoSpaces Prior Proof Evidence Report

## Goal

Render normalized prior proof evidence as first-class visual report evidence in
the proof-bundle runner output.

## Tasks

1. Carry `prior_proof_result_summary` into runner manifests.
2. Add a `Prior Proof Evidence` report section before new proof commands.
3. Reuse proof result cards for prior diagnostic rows and view image artifacts.
4. Extend checker coverage for prior proof evidence in `report.html`.
5. Add focused tests for report rendering, standalone prior ingest, and checker
   validation.
6. Run a manual dry-run against Phase 81 standalone evidence.

## Acceptance Checks

- Focused ruff checks pass for changed implementation, checker, and tests.
- Focused format checks pass for changed Python files.
- Focused pytest covers the prior proof evidence report section.
- Manual runner dry-run report contains `Prior Proof Evidence`.
- Runner checker passes on the manual dry-run manifest.

## Result

Implemented.

Runner manifests now keep the merged prior proof result summary. The visual
runner report renders that summary before proof commands, preserving prior
status, blocker detail, proof paths, worker-stage evidence, and planner-view
images when present.

Focused validation passed:

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_ingests_standalone_prior_probe_run_result_by_cleanup_pair tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_partial_selection_with_exhausted_fallbacks`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase86-prior-proof-evidence-visual-report-dry-run/proof_bundle_run_manifest.json`

## Status

Complete.
