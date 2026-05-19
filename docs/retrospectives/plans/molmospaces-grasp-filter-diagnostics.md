# MolmoSpaces Grasp Filter Diagnostics

**Status:** Completed under GSD Phase 119 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0110
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 118 proved that `Bread_1` rigid grasp candidate generation can run, but
upstream perturbation filtering saves an empty NPZ and deletes the intermediate
evidence needed to diagnose why. The next slice needs to preserve those
intermediates and make filter-stage behavior visible before any cache install is
attempted.

## Decision

Add `scripts/run_molmospaces_grasp_filter_diagnostics.py` and supporting
`roboclaws.molmo_cleanup.grasp_filter_diagnostics`.

The runner records:

- preserved combine/Manifold/simplify/candidate generation artifacts;
- bounded candidate subset path and counts;
- three filter variants: `initial_contact`, `translation_shake`, and
  `upstream_like`;
- per-variant NPZ validation and output tails;
- report-visible blockers.

## Non-Goals

- Do not install any generated cache file.
- Do not treat unfiltered candidate JSON as loader-ready cache data.
- Do not claim the full 21k-candidate upstream filter is fixed.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_filter_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_filter_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --output-dir output/debug-phase119-grasp-filter-diagnostics --output output/debug-phase119-grasp-filter-diagnostics/filter_diagnostics_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --sample-size 24 --num-samples 256 --num-workers 4 --approach-steps 30 --shake-steps 10 --timeout-s 600`

## Result

The bounded local diagnostic produced 24 valid generated candidates and kept the
intermediate artifacts under
`output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/`.
All three perturbation-filter variants saved zero transforms, including the
no-shake/no-rotate `initial_contact` variant. The next blocker is therefore the
initial contact/pose path inside upstream perturbation testing, not cache
installation or Manifold setup.
