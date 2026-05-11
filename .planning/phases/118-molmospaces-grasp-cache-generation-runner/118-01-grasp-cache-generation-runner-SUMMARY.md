# Phase 118 Summary: MolmoSpaces Grasp Cache Generation Runner

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `118-01-grasp-cache-generation-runner-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Run the real upstream `Bread_1` rigid grasp-generation path through a reusable
Roboclaws wrapper, validate generated output, and install only a non-empty cache.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Completed on 2026-05-10. Candidate generation succeeds, but perturbation
filtering saves an empty `Bread_1_grasps_filtered.npz` with zero transforms.
The loader cache remains blocked by an upstream zero-success filtering result.

## Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_cache_generation.py tests/test_grasp_cache_generation.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_cache_generation.py tests/test_grasp_cache_generation.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_cache_generation.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py`
- `scripts/run_molmospaces_grasp_cache_generation.py` run into
  `output/debug-phase118-grasp-cache-generation-min/generation_result.json`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
