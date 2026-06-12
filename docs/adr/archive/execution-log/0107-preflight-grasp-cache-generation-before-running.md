# 0107. Preflight Grasp Cache Generation Before Running

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0105 showed that the installed droid `Bread_1` grasp cache exists but is
empty. The next functional mitigation is to generate or restore a non-empty
rigid grasp cache.

The upstream MolmoSpaces rigid generator has its own prerequisites: grasp
Python extras, a working `trimesh` collision backend (`python-fcl`), Manifold
mesh-processing executables, object XML inputs, and a post-generation install
step into the runtime loader cache target.

Running generation without checking those prerequisites would fail late and
produce another sparse local-dev artifact.

## Decision

Add a proof-bundle runner `Grasp Cache Generation Preflight` before attempting
rigid grasp generation.

The preflight records:

- the MolmoSpaces Python runtime, root, and assets dir;
- the exact object XML used for generation;
- the upstream `run_rigid.py` command shape;
- the generated NPZ path and final loader cache target path;
- Python prerequisite checks;
- Manifold `manifold` and `simplify` executable checks;
- blockers and recommendation.

The preflight is report-only and does not create or install grasps.

## Consequences

- Cache generation remains blocked until prerequisites are installed/built.
- The next local-dev step is explicit: install missing grasp-generation
  dependencies and build Manifold, then rerun the same report gate.
- We avoid treating source rotation or placeholder files as a cache fix.

## Evidence

Implemented in Phase 116 on 2026-05-10.

Artifact:

- `output/debug-phase116-grasp-cache-generation-preflight/proof_bundle_run_manifest.json`
- `output/debug-phase116-grasp-cache-generation-preflight/report.html`

Key blockers:

- `sklearn_missing`
- `python_fcl_missing`
- `manifold_executable_missing`
- `simplify_executable_missing`
