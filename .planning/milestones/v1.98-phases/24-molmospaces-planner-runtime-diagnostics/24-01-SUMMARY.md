# Phase 24-01 Summary: Planner Runtime Diagnostics

## Status

Completed 2026-05-09.

## What Changed

- Enabled `faulthandler` for MolmoSpaces planner-probe worker subprocesses and set
  `PYTHONFAULTHANDLER=1` in the parent launcher.
- Added worker runtime diagnostics for Python executable/version/platform and
  planner-relevant module availability: `molmo_spaces`, `mujoco`, `jax`,
  `jaxlib`, `curobo`, `warp`, `mujoco_warp`, and `mlspaces_tests`.
- Emitted diagnostics as an early worker stdout JSON line so native crashes can
  still leave dependency evidence before the final worker payload is lost.
- Persisted diagnostics into `manipulation_evidence.runtime_diagnostics` in
  `run_result.json`.
- Rendered a `Runtime Diagnostics` panel through the shared Molmo cleanup report
  renderer, not a second planner-only report implementation.
- Tightened the planner-probe checker so reports must contain `Runtime
  Diagnostics` whenever the evidence contains runtime diagnostics.

## Evidence

- Default probe:
  `output/molmo-planner-manipulation-probe-harness/run_result.json`
  reports `status=blocked_capability`, `runtime_diagnostics` present,
  `faulthandler_enabled=true`, and `curobo.available=false`.
- Default report:
  `output/molmo-planner-manipulation-probe-harness/report.html` renders
  `Runtime Diagnostics`, `Capability Blockers`, and `Manipulation Provenance`.
- Franka execute-mode probe:
  `output/molmo-planner-manipulation-probe-execute/run_result.json` reports
  blocker `process_signal` / `SIGSEGV` with runtime diagnostics preserved from
  the early stdout event.
- Franka execute stderr:
  `output/molmo-planner-manipulation-probe-execute/planner_probe_stderr.txt`
  now contains a faulthandler stack showing the crash in `glfw.create_window`
  during MolmoSpaces `sample_task()`.
- RBY1M config-import probe:
  `output/molmo-planner-manipulation-probe-rby1m/run_result.json` reports
  blocker `ModuleNotFoundError: No module named 'curobo'` and diagnostics with
  `curobo.available=false`.

## Boundary

This phase did not claim planner-backed cleanup execution. The strict proof
gate from ADR-0014 still required a passing `--require-planner-backed` probe
with real planner execution, nonzero robot-state movement, and no blockers.

Follow-up: Phase 25 later produced a passing standalone Franka strict planner
proof. Cleanup-loop integration remains separate.
