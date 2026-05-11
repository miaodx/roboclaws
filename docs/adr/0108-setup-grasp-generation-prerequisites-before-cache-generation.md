# 0108. Setup Grasp Generation Prerequisites Before Cache Generation

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0107 made rigid grasp generation report-visible and showed four local
blockers before a non-empty `Bread_1` cache can be generated: missing
`sklearn`, missing `python-fcl`, and missing Manifold `manifold` / `simplify`
executables.

The local MolmoSpaces checkout also exposed two setup details that should not
remain as hand-run tribal knowledge:

- the uv-created MolmoSpaces venv does not include `pip`;
- the checkout has `.gitmodules` for `external_src/Manifold`, but no tracked
  gitlink, so a path-specific `git submodule update` cannot initialize it.

## Decision

Add a reusable Roboclaws setup runner for local MolmoSpaces rigid grasp
generation prerequisites.

The runner:

- installs only the Python packages required by the currently exercised rigid
  path (`scikit-learn`, `python-fcl`) using `uv pip install --python` when
  available;
- initializes the official Manifold source from the upstream `.gitmodules`
  contract, falling back to cloning `https://github.com/hjwdzh/Manifold.git`
  when the checkout lacks a gitlink;
- configures and builds Manifold with CMake;
- can rerun the same `Grasp Cache Generation Preflight` as its acceptance gate.

Do not generate or install grasps in this phase. Cache generation remains a
separate, report-gated step.

## Consequences

- Future local-dev sessions can reproduce prerequisite setup through one
  checked-in script instead of copying shell fragments from a report.
- Phase 117 converts the generation preflight from `blocked` to `ready`, with
  zero report blockers.
- The next phase may run upstream `run_rigid.py` for `Bread_1`, validate that
  the generated NPZ has nonzero transforms, and install it into the droid cache
  target.

## Evidence

Implemented in Phase 117 on 2026-05-10.

Artifacts:

- `output/debug-phase117-grasp-generation-prereqs/setup_result.json`
- `output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json`
- `output/debug-phase117-grasp-generation-prereqs/report.html`

Key results:

- setup status: `ready`
- setup blockers: `0`
- generation preflight status: `ready`
- generation preflight blockers: `0`
