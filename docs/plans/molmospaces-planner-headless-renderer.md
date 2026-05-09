# MolmoSpaces Planner Headless Renderer

**Status:** Planned under GSD Phase 25
**Created:** 2026-05-09
**Source:** ADR-0015, ADR-0016, Phase 24 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 24 proved that the strict planner probe is blocked before planner proof:

- default Franka execute mode segfaults in GLFW window creation;
- EGL environment variables avoid that path but hit an upstream MolmoSpaces CGL
  import bug on Linux.

The next useful slice is to make the standalone Franka planner probe run
headlessly without mutating the upstream checkout. If it passes the strict
checker, Roboclaws can then plan real cleanup integration. If it reaches a new
planner blocker, that blocker becomes the next evidence-backed slice.

## Decision

Add a probe-local EGL renderer adapter for execute-mode probes.

This phase should:

- add an explicit renderer-device override to
  `scripts/run_molmo_planner_manipulation_probe.py`;
- patch the MolmoSpaces environment module only inside the worker process;
- set EGL environment variables for the adapted worker path;
- record the renderer override in `runtime_diagnostics`;
- run the Franka execute-mode probe through `--require-planner-backed`;
- keep blocked-capability semantics strict if execution still cannot prove
  nonzero robot-state movement.

## Non-Goals

- Do not install CuRobo or fix the RBY1M dependency path.
- Do not edit the upstream MolmoSpaces checkout in `/tmp`.
- Do not integrate planner-backed primitives into the cleanup MCP contract in
  this slice.
- Do not relax the strict proof checker.

## Deliverables

- ADR-0016 and this source plan.
- `.planning/phases/25-molmospaces-planner-headless-renderer/25-01-planner-headless-renderer-PLAN.md`.
- Probe-local renderer adapter with focused tests.
- Strict proof run result or an explicit next blocker.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py`
- `.venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-manipulation-probe-headless --probe-mode execute --embodiment franka --steps 2 --timeout-s 180`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --require-planner-backed output/molmo-planner-manipulation-probe-headless/run_result.json`
