# MolmoSpaces RBY1M Warp Compatibility

**Status:** Completed under GSD Phase 33 on 2026-05-09
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0019, ADR-0023, ADR-0024, Phase 32 evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 32 removed stale CuRobo extension-cache ambiguity. The RBY1M target path
now reaches execute-mode policy construction, with all known CuRobo extension
`.so` files present and no locks. The remaining blocker is a Warp/CuRobo API
shape mismatch:

```text
AttributeError: module 'warp' has no attribute 'torch'
```

The installed Warp exposes top-level Torch bridge helpers but not the
`warp.torch` namespace expected by this CuRobo code path.

## Decision

Implement ADR-0024 as a runtime-compatibility phase.

This phase should:

- add Warp API-shape diagnostics to the planner probe runtime diagnostics;
- add a probe-local adapter that provides `warp.torch.device_from_torch` when
  the namespace is missing but top-level `warp.device_from_torch` exists;
- emit worker-stage events around the adapter;
- render a `Warp Compatibility` report section;
- checker/test the report evidence when requested;
- rerun RBY1M execute mode with the isolated CuRobo extension cache;
- keep strict RBY1M/CuRobo readiness unchanged.

## Non-Goals

- Do not pin or reinstall Warp in this phase.
- Do not patch files inside the MolmoSpaces, CuRobo, or Warp installations.
- Do not make a shimmed runtime satisfy strict readiness unless the planner
  actually executes and moves robot state.
- Do not replace cleanup primitives in this phase unless strict target
  readiness unexpectedly passes and a follow-up phase is planned.

## Deliverables

- ADR-0024 and this source plan.
- `.planning/milestones/v1.98-phases/33-molmospaces-rby1m-warp-compatibility/33-01-rby1m-warp-compatibility-PLAN.md`.
- Probe-local Warp compatibility adapter.
- Warp compatibility diagnostics in `run_result.json`.
- Planner probe report section for Warp compatibility.
- Focused tests and checker assertions.
- Local execute artifact under `output/molmo-planner-rby1m-warp-compatibility-execute/`.

## Acceptance Criteria

- Runtime diagnostics record Warp version/API shape.
- The report renders `Warp Compatibility` when diagnostics are present.
- Execute-mode artifacts record whether the adapter was applied.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  robot-state movement.
- A local execute-mode run either reaches strict RBY1M/CuRobo planner-backed
  execution or records the next precise blocked stage.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-warp-compatibility-execute --embodiment rby1m --probe-mode execute --torch-extensions-dir output/molmo-planner-rby1m-curobo-cache-isolation/torch_extensions --renderer-device-id 0 --steps 2 --timeout-s 600`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility output/molmo-planner-rby1m-warp-compatibility-execute/run_result.json`
- Strict readiness rejected the artifact with `--require-rby1m-curobo-ready`,
  as intended.

## Completion Evidence

Phase 33 completed as Warp compatibility and blocked execute evidence, not as
target runtime readiness.

The execute artifact records:

- `warp_compatibility.adapter.applied=true`;
- `warp.torch.device_from_torch` provided by the probe-local adapter;
- 5/5 known CuRobo extension `.so` files present with 0 locks;
- worker stages through `execute_policy_construct_done`,
  `execute_policy_reset_done`, and `execute_policy_run_start`;
- report sections for `Warp Compatibility`, `CuRobo Extension Cache`,
  `Worker Stage Timeline`, and `RBY1M CuRobo Gate`;
- blocker `OutOfMemoryError` during `execute_policy_run`, with GPU 0 reporting
  only about 285 MiB free.

Because execute mode did not produce planner-backed robot-state movement,
actual planner-backed cleanup primitive replacement remains gated.
