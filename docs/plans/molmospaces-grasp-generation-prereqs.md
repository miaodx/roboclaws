# MolmoSpaces Grasp Generation Prerequisites

**Status:** Completed under GSD Phase 117 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0108
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 116 proved that `Bread_1` rigid cache generation is blocked before
`run_rigid.py` can be attempted. The blockers are environment setup gaps, not
proof-request selection gaps:

- `sklearn` is missing in the MolmoSpaces runtime;
- `python-fcl` is missing for `trimesh.collision.CollisionManager`;
- Manifold `manifold` and `simplify` executables are missing.

The local MolmoSpaces venv also lacks `pip`, and the clone has `.gitmodules`
but no tracked Manifold gitlink.

## Decision

Add and run a reusable setup runner:

```bash
.venv/bin/python scripts/setup_molmospaces_grasp_generation.py \
  --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python \
  --molmospaces-root /tmp/roboclaws-molmospaces-spike/molmospaces \
  --preflight-manifest output/debug-phase116-grasp-cache-generation-preflight/proof_bundle_run_manifest.json \
  --output-dir output/debug-phase117-grasp-generation-prereqs \
  --output output/debug-phase117-grasp-generation-prereqs/setup_result.json
```

The runner installs `scikit-learn` and `python-fcl`, initializes/builds
Manifold, and reruns the Phase 116 generation preflight.

## Non-Goals

- Do not run `run_rigid.py` in this phase.
- Do not copy generated grasp files into the loader cache in this phase.
- Do not weaken cache validity checks.
- Do not install broad unused extras such as visualization-only dependencies
  unless the rigid generation path actually requires them.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_generation_setup.py scripts/setup_molmospaces_grasp_generation.py tests/test_grasp_generation_setup.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_generation_setup.py scripts/setup_molmospaces_grasp_generation.py tests/test_grasp_generation_setup.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_generation_setup.py`
- `.venv/bin/python scripts/setup_molmospaces_grasp_generation.py --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --molmospaces-root /tmp/roboclaws-molmospaces-spike/molmospaces --preflight-manifest output/debug-phase116-grasp-cache-generation-preflight/proof_bundle_run_manifest.json --output-dir output/debug-phase117-grasp-generation-prereqs --output output/debug-phase117-grasp-generation-prereqs/setup_result.json --parallel-jobs 4 --command-timeout-s 1800 --preflight-timeout-s 60`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --output-dir output/debug-phase117-grasp-generation-prereqs --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --prior-planner-probe-run-result output/debug-phase109-grasp-collision-diagnostics/run_result.json --exclude-task-feasibility-blocked --generate-fallback-requests`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --min-selected-requests 9 --max-selected-requests 9`

## Result

The setup runner reports `status=ready` with zero blockers. The Phase 117
proof-bundle report renders `Grasp Cache Generation Preflight` as ready:
`python_module_sklearn`, `python_fcl_runtime`, `manifold_executable`, and
`simplify_executable` all pass.
