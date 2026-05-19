# Phase 118 Plan: MolmoSpaces Grasp Cache Generation Runner

## Goal

Run the real upstream `Bread_1` rigid grasp-generation path through a reusable
Roboclaws wrapper, validate generated output, and install only a non-empty cache.

## Tasks

1. Add a generation/install runner that consumes the ready Phase 117 preflight.
2. Reuse the cache-file validation rule from the availability preflight.
3. Prefer `*_mesh.xml` object inputs when present.
4. Ensure the MolmoSpaces checkout-root `assets` symlink exists for floating
   Robotiq mesh resolution.
5. Render a shared-style generation report with command output, transform
   counts, install state, and blockers.
6. Run the local `Bread_1` generation attempt and record the actual blocker.

## Acceptance Criteria

- The runner writes `generation_result.json`.
- The runner writes `report.html`.
- Empty generated NPZ files are not installed.
- The result clearly distinguishes successful candidate generation from failed
  perturbation/filter validation.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_cache_generation.py tests/test_grasp_cache_generation.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/planner_task_feasibility.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_cache_generation.py tests/test_grasp_cache_generation.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_cache_generation.py tests/test_planner_task_feasibility.py tests/test_molmo_cleanup_report.py`
- `scripts/run_molmospaces_grasp_cache_generation.py` run into
  `output/debug-phase118-grasp-cache-generation-min/generation_result.json`

## Result

Completed on 2026-05-10. Candidate generation succeeds, but perturbation
filtering saves an empty `Bread_1_grasps_filtered.npz` with zero transforms.
The loader cache remains blocked by an upstream zero-success filtering result.
