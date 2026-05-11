# MolmoSpaces Grasp Cache Generation Runner

**Status:** Completed under GSD Phase 118 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0109
**Workflow:** `hybrid-phase-pipeline`

## Problem

After Phase 117, prerequisites are ready but `Bread_1` still has no valid
loader cache. The next local-dev step must generate and install a real non-empty
NPZ, or make the next blocker visible without treating placeholder data as
success.

## Decision

Add `scripts/run_molmospaces_grasp_cache_generation.py` and supporting
`roboclaws.molmo_cleanup.grasp_cache_generation`.

The runner records:

- object-list path and entries;
- upstream `run_rigid.py` command;
- checkout-root assets symlink used by the floating Robotiq XML;
- generated NPZ validation;
- install validation;
- availability preflight after install;
- report-visible blockers.

## Non-Goals

- Do not install empty generated NPZ files.
- Do not convert unfiltered candidate grasps into a fake loader cache.
- Do not claim exact planner proof is unblocked until the droid loader cache
  validates with nonzero transforms.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_cache_generation.py tests/test_grasp_cache_generation.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_cache_generation.py tests/test_grasp_cache_generation.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_cache_generation.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_cache_generation.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --output-dir output/debug-phase118-grasp-cache-generation-min --output output/debug-phase118-grasp-cache-generation-min/generation_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --max-successful-grasps 1 --num-workers 4 --approach-steps 30 --shake-steps 10 --timeout-s 600`

## Result

The wrapper gets past prerequisite, object-list, mesh-combine, Manifold, and
candidate-generation stages. The remaining blocker is filtering:
`perturbations_test.py` checks all 21,514 generated candidates and saves
`0` successful transforms. The report renders that as a blocked generation
artifact, and the empty NPZ is not installed into the loader cache.
