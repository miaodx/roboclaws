# Phase 25-01 Summary: Planner Headless Renderer

## Status

Completed 2026-05-09.

## What Changed

- Added an execute-mode renderer-device override to the standalone planner
  probe.
- For execute-mode workers, the parent and worker now set:
  `MUJOCO_GL=egl`, `PYOPENGL_PLATFORM=egl`, and
  `ROBOCLAWS_MOLMOSPACES_RENDERER_DEVICE_ID=0`.
- Added a probe-local renderer adapter that patches both MolmoSpaces renderer
  call sites used by the Franka probe:
  `molmo_spaces.env.env.MjOpenGLRenderer` and
  `molmo_spaces.utils.scene_maps.MjOpenGLRenderer`.
- Kept the adapter local to the worker process; no upstream MolmoSpaces files
  are modified.
- Recorded renderer adapter status in runtime diagnostics and rendered those
  values in the shared planner probe report.
- Hardened timeout artifact writing so `TimeoutExpired` byte output is decoded
  into stdout/stderr files instead of crashing the parent process.

## Evidence

- Strict Franka headless proof:
  `output/molmo-planner-manipulation-probe-headless/run_result.json`
  reports `status=planner_backed`, `primitive_provenance=planner_backed`,
  `strict_proof_eligible=true`, `execution_attempted=true`,
  `steps_executed=2`, and `max_abs_qpos_delta=0.01846538091255523`.
- Strict checker:
  `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --require-planner-backed output/molmo-planner-manipulation-probe-headless/run_result.json`
  passed.
- Planner probe views:
  `output/molmo-planner-manipulation-probe-headless/planner_views/initial_wrist_camera.png`
  and
  `output/molmo-planner-manipulation-probe-headless/planner_views/final_wrist_camera.png`.
- Shared report:
  `output/molmo-planner-manipulation-probe-headless/report.html` renders
  `Manipulation Provenance`, `Planner Probe Views`, and `Runtime Diagnostics`
  with `renderer_adapter=True`, `renderer_device=0`, `MUJOCO_GL=egl`, and
  `PYOPENGL_PLATFORM=egl`.
- Default blocked-capability gate:
  `just verify::molmo-planner-manipulation-probe` still passes and remains a
  safe CI-style capability check.

## Boundary

This phase proves standalone Franka planner-backed manipulation execution. It
does not yet integrate planner-backed manipulation into the ADR-0003 cleanup MCP
contract or into the full cleanup loop. RBY1M still reports CuRobo missing and
remains a separate blocker.
