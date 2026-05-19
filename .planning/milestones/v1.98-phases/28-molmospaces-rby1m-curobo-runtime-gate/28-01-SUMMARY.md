# Phase 28-01 Summary: RBY1M CuRobo Runtime Gate

Completed: 2026-05-09

## What Changed

- Added `rby1m_curobo_gate` for planner probe artifacts.
- Rendered `RBY1M CuRobo Gate` in the shared planner probe report.
- Added checker modes for explicit blocked-capability acceptance and strict
  RBY1M/CuRobo readiness.
- Kept standalone Franka strict proof separate from target RBY1M readiness.

## Evidence

- Local artifact:
  `output/molmo-planner-rby1m-curobo-gate/report.html`
- Run result:
  `output/molmo-planner-rby1m-curobo-gate/run_result.json`
- Current gate state:
  `status=blocked_capability`, `embodiment=rby1m`,
  `curobo_available=true`, `execution_attempted=false`.
- Local follow-up installed the pinned CuRobo extra and CUDA PyTorch in the
  isolated MolmoSpaces runtime, but config import still times out during CuRobo
  CUDA-extension JIT warmup before planner execution starts.
- Strict RBY1M/CuRobo readiness rejects the current artifact.

## Follow-Ups

- Resolve the CuRobo JIT/config-import timeout if the local workstation is
  expected to prove RBY1M planner execution.
- After RBY1M/CuRobo readiness passes, replace cleanup-loop `api_semantic`
  subphases with real planner-backed primitives.
- Keep camera-only model-policy cleanup as a separate phase.
