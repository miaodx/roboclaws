---
phase: 119
plan: 119-01
status: completed
created: 2026-05-10
completed: 2026-05-10
workflow: hybrid-phase-pipeline
adr: docs/adr/0110-preserve-grasp-filter-intermediates-and-variant-diagnostics.md
plan_doc: docs/retrospectives/plans/molmospaces-grasp-filter-diagnostics.md
---

# 119-01 Grasp Filter Diagnostics

## Goal

Make the `Bread_1` zero-success perturbation-filter blocker reproducible and
visible without installing fake or empty loader cache data.

## Scope

- Add a reusable diagnostic module and CLI for bounded perturbation-filter
  probes.
- Preserve mesh and candidate intermediates under the selected output dir.
- Run explicit filter variants:
  `initial_contact`, `translation_shake`, and `upstream_like`.
- Render the diagnostic as shared-style `report.html`.
- Record the result in CONTEXT, ADR, plan docs, and STATE.

## Acceptance Criteria

- The CLI writes JSON and `report.html`.
- The report includes diagnostic artifacts, filter variants, and blockers.
- Focused unit tests cover dry-run, zero-success, and success classification.
- A local bounded diagnostic artifact exists for `Bread_1`.

## Verification

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_filter_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_filter_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --output-dir output/debug-phase119-grasp-filter-diagnostics --output output/debug-phase119-grasp-filter-diagnostics/filter_diagnostics_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --sample-size 24 --num-samples 256 --num-workers 4 --approach-steps 30 --shake-steps 10 --timeout-s 600`

## Outcome

Phase 119 is complete. The diagnostic generated 24 valid candidates and showed
zero successful transforms for all three variants, including `initial_contact`.
The next slice should inspect or replace the initial contact/pose path in
`perturbations_test.py`.
