# Phase 117 Plan: MolmoSpaces Grasp Generation Prerequisites

## Goal

Make the local MolmoSpaces rigid grasp-generation environment report-ready
without generating or installing `Bread_1` grasps yet.

## Tasks

1. Add a reusable setup runner for rigid grasp-generation prerequisites.
2. Handle uv venvs without `pip` by using `uv pip install --python` when
   available.
3. Initialize/build Manifold, including the fallback clone path required by the
   current MolmoSpaces checkout.
4. Rerun the proof-bundle generation preflight and require status `ready`.
5. Update CONTEXT, ADR, plan, and GSD state.

## Acceptance Criteria

- Setup runner writes a JSON result with setup command status and blockers.
- `scikit-learn` and `python-fcl` are ready in the MolmoSpaces runtime.
- Manifold `manifold` and `simplify` executables are present and executable.
- Phase 117 proof-bundle runner report shows `Grasp Cache Generation Preflight`
  as `ready` with zero blockers.
- No grasp cache file is generated or installed in this phase.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_generation_setup.py scripts/setup_molmospaces_grasp_generation.py tests/test_grasp_generation_setup.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_generation_setup.py scripts/setup_molmospaces_grasp_generation.py tests/test_grasp_generation_setup.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_generation_setup.py`
- `scripts/setup_molmospaces_grasp_generation.py` run into
  `output/debug-phase117-grasp-generation-prereqs/setup_result.json`
- `scripts/check_molmo_planner_proof_bundle_runner_result.py` against
  `output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json`

## Result

Completed on 2026-05-10. Setup and generation preflight both report `ready`
with zero blockers. The next phase should generate `Bread_1` rigid grasps,
validate nonzero transforms, and install the NPZ into the droid loader cache.
