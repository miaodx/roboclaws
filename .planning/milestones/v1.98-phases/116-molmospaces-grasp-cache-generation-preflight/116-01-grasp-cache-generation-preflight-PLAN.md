# Phase 116-01: Grasp Cache Generation Preflight

## Goal

Make the local prerequisites for generating a valid rigid `Bread_1` grasp cache
visible before running the upstream MolmoSpaces generator.

## Tasks

- Add `grasp_cache_generation_preflight` to proof-bundle manifests.
- Preflight MolmoSpaces Python runtime, object XML, upstream generator scripts,
  `python-fcl` collision backend, `sklearn`, Manifold `manifold`/`simplify`,
  and floating Robotiq assets.
- Render a `Grasp Cache Generation Preflight` report section with generation
  assets, checks, blockers, and proposed command.
- Checker-gate the new manifest/report section.
- Regenerate the proof-bundle report against the Phase 114/109 evidence.

## Acceptance

- The Phase 116 report shows `Bread_1` object XML and loader cache target.
- The report records a proposed `run_rigid.py` generation command.
- The report is `blocked` with concrete missing prerequisites instead of
  failing invisibly or creating placeholder grasps.
- Focused ruff, pytest, and runner checker gates pass.

## Result

Completed on 2026-05-10. The Phase 116 dry-run report records the exact
generation route and blocks on missing `sklearn`, missing `python-fcl`, and
missing Manifold `manifold` / `simplify` executables.

Artifact:
`output/debug-phase116-grasp-cache-generation-preflight/report.html`.
