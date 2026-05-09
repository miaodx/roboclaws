# 34-01 RBY1M CUDA Memory Headroom Plan

## Goal

Make RBY1M/CuRobo execute-mode CUDA memory pressure explicit in artifacts and
reports without changing strict planner-backed readiness.

## Status

Planned 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [ ] Add CUDA/PyTorch memory diagnostics to planner probe runtime diagnostics.
3. [ ] Add stage-local memory snapshots around RBY1M execute-mode worker stages.
4. [ ] Render/checker/test `CUDA Memory Headroom` report evidence.
5. [ ] Rerun local RBY1M/CuRobo execute mode with isolated extension cache and
   Warp compatibility, then record whether the next blocker remains OOM.

## Acceptance

- Runtime diagnostics record CUDA availability, device metadata, allocator
  configuration, and current free/total memory when CUDA is available.
- Execute artifacts include memory snapshots for policy construction, reset,
  run start, and final/exception paths.
- `report.html` renders a `CUDA Memory Headroom` section when diagnostics are
  present.
- Blocked mode remains explicit and checker-gated.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  robot-state movement.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo execute artifact under
  `output/molmo-planner-rby1m-cuda-memory-headroom-execute/`.

## Evidence

Pending implementation.

## Risks

- Memory pressure may be dominated by upstream planner defaults or GPU hardware
  size, so this phase may only convert an opaque blocker into structured
  evidence.
- CUDA diagnostics must tolerate CPU-only CI and missing Torch CUDA support.
