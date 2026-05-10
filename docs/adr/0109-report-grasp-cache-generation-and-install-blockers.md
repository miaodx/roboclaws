# 0109. Report Grasp Cache Generation And Install Blockers

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0108 made the local MolmoSpaces rigid grasp-generation prerequisites pass.
The next step was to run upstream `run_rigid.py` for `Bread_1`, validate a
non-empty generated NPZ, and install it into the runtime droid loader cache.

Running that manually would hide several important runtime details:

- the upstream object list must use `Bread_1_mesh.xml`, not `Bread_1.xml`,
  because the default XML only has primitive colliders and `combine_meshes.py`
  only combines mesh colliders;
- the upstream floating Robotiq XML resolves mesh paths through
  `../../../assets`, which requires an assets symlink at the checkout root;
- `run_rigid.py` can exit `0` even when filtering saves zero successful grasps.

## Decision

Add a reusable generation/install runner and shared-style HTML report for
MolmoSpaces rigid grasp cache generation attempts.

The runner:

- consumes a ready `Grasp Cache Generation Preflight`;
- writes the rigid object-list JSON, preferring sibling `*_mesh.xml` inputs
  when present;
- ensures the MolmoSpaces checkout-root `assets` symlink points at the resolved
  `ASSETS_DIR`;
- runs upstream `run_rigid.py`;
- validates the generated NPZ with the same nonzero-transform rule used by the
  availability preflight;
- installs only valid non-empty generated NPZ files into the loader cache;
- renders a report showing command output, transform counts, install status,
  and blockers.

## Consequences

- The generation path is now reproducible and reviewable, even when upstream
  exits successfully but produces an empty filtered cache.
- Phase 118 does not install a fake or empty cache.
- The next blocker is the upstream `Bread_1` perturbation/filter behavior:
  candidate generation produces `Bread_1_grasps.json`, but filtering records
  `0` successful grasps.

## Evidence

Implemented in Phase 118 on 2026-05-10.

Artifacts:

- `output/debug-phase118-grasp-cache-generation-min/generation_result.json`
- `output/debug-phase118-grasp-cache-generation-min/report.html`

Key results:

- candidate grasp JSON exists for `Bread_1`;
- filtered generated NPZ status: `empty`;
- filtered generated transform count: `0`;
- install status: not installed;
- generation result status: `blocked`.
