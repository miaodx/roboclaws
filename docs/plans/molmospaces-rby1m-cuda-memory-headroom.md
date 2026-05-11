# MolmoSpaces RBY1M CUDA Memory Headroom

**Status:** Completed under GSD Phase 34 on 2026-05-09
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0019, ADR-0024, ADR-0025, Phase 33 evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 33 proved the probe-local Warp adapter is enough to reach RBY1M/CuRobo
policy execution. The remaining execute-mode blocker is now CUDA memory
pressure during CuRobo trajectory planning.

The existing artifact captures the `OutOfMemoryError` traceback, but it does
not make GPU headroom reviewable in the report. A future tuning or hardware
decision needs structured memory evidence: free/total device memory, PyTorch
allocated/reserved bytes, allocator settings, visible devices, and snapshots
near each worker stage.

## Decision

Implement ADR-0025 as a runtime-evidence phase.

This phase should:

- add CUDA/PyTorch memory diagnostics to planner probe runtime diagnostics;
- record stage-local memory snapshots around RBY1M execute stages;
- include memory evidence in blocked payloads and final diagnostics;
- render a `CUDA Memory Headroom` report section;
- add checker/test coverage for the report evidence;
- rerun RBY1M execute mode with the existing isolated CuRobo extension cache
  and Warp adapter;
- keep strict RBY1M/CuRobo readiness unchanged.

## Non-Goals

- Do not kill or reset GPU processes.
- Do not delete extension caches.
- Do not tune CuRobo planner batch sizes or environment allocator knobs in this
  phase.
- Do not replace cleanup primitives in this phase unless strict target
  readiness unexpectedly passes and a follow-up phase is planned.

## Deliverables

- ADR-0025 and this source plan.
- `.planning/phases/34-molmospaces-rby1m-cuda-memory-headroom/34-01-rby1m-cuda-memory-headroom-PLAN.md`.
- CUDA memory diagnostics in `run_result.json`.
- Planner probe report section for CUDA memory headroom.
- Checker flag for required CUDA memory evidence.
- Focused tests.
- Local execute artifact under
  `output/molmo-planner-rby1m-cuda-memory-headroom-execute/`.

## Acceptance Criteria

- Runtime diagnostics record CUDA availability, selected device, visible
  devices, allocator config, free/total memory, and PyTorch allocated/reserved
  memory when CUDA is available.
- RBY1M execute artifacts record stage-local memory snapshots through at least
  policy construction, reset, run start, and final/exception paths.
- `report.html` renders `CUDA Memory Headroom` when diagnostics are present.
- The checker can require CUDA memory evidence without requiring strict
  RBY1M/CuRobo readiness.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  robot-state movement.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-cuda-memory-headroom-execute --embodiment rby1m --probe-mode execute --torch-extensions-dir output/molmo-planner-rby1m-curobo-cache-isolation/torch_extensions --renderer-device-id 0 --steps 2 --timeout-s 600`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory output/molmo-planner-rby1m-cuda-memory-headroom-execute/run_result.json`

## Completion Evidence

Phase 34 completed as CUDA memory-headroom evidence, not as target runtime
readiness.

The execute artifact records:

- `CUDA Memory Headroom` in `report.html`;
- 7 stage-local memory snapshots, including policy construction, reset, run
  start, and exception;
- 5/5 known CuRobo extension `.so` files present with 0 locks;
- `warp_compatibility.adapter.applied=true`;
- worker stages through `execute_policy_run_start`;
- blocker `OutOfMemoryError` during CuRobo trajectory planning.

The memory profile is now explicit:

- worker start: about 11.4 GiB free, 0 PyTorch reserved;
- `execute_policy_construct_before`: about 10.2 GiB free, 2.0 MiB PyTorch
  reserved;
- `execute_policy_construct_after`: about 9.1 GiB free, 1.1 GiB PyTorch
  reserved;
- `execute_policy_run_start`: about 9.1 GiB free, 1.1 GiB PyTorch reserved;
- `worker_exception`: about 284.7 MiB free, 9.7 GiB PyTorch allocated, and
  9.9 GiB PyTorch reserved.

Because execute mode still did not produce planner-backed robot-state movement,
actual planner-backed cleanup primitive replacement remains gated. The next
phase should decide whether to tune CuRobo planner memory shape, allocator
configuration, task complexity, or hardware requirements.
