# Phase 119 Summary: 119-01 Grasp Filter Diagnostics

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `119-01-grasp-filter-diagnostics-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Make the `Bread_1` zero-success perturbation-filter blocker reproducible and
visible without installing fake or empty loader cache data.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

The source plan contains checked tasks and embedded evidence, but no dedicated Status or Result section was found.

## Evidence

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_filter_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_filter_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --output-dir output/debug-phase119-grasp-filter-diagnostics --output output/debug-phase119-grasp-filter-diagnostics/filter_diagnostics_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --sample-size 24 --num-samples 256 --num-workers 4 --approach-steps 30 --shake-steps 10 --timeout-s 600`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
