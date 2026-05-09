# MolmoSpaces RBY1M CuRobo Warmup Readiness

**Status:** Completed under GSD Phase 31 on 2026-05-09
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0019, ADR-0022, Phase 28 evidence, Phase 30 state
**Workflow:** `hybrid-phase-pipeline`

## Problem

Actual planner-backed cleanup primitive replacement remains blocked by the
target RBY1M/CuRobo runtime. Phase 28 made that blocker first-class, but the
artifact only says the subprocess exceeded 60 seconds while stderr shows CuRobo
CUDA extension JIT compile lines.

The next slice needs to answer a narrower question before changing cleanup
primitives: can this local runtime finish the RBY1M/CuRobo warmup and reach
planner execution, or is it still blocked at a precise stage?

## Decision

Implement ADR-0022 as a warmup-readiness phase.

This phase should:

- add staged worker progress events to
  `scripts/run_molmo_planner_manipulation_probe.py`;
- preserve the last observed worker stage and event history in
  `run_result.json`;
- render those worker stages in the shared planner probe report;
- add focused checker/test coverage for timeout artifacts that preserve stage
  evidence;
- rerun the local RBY1M config-import gate with a longer timeout;
- if config import passes, attempt execute mode and run the strict
  `--require-rby1m-curobo-ready` checker;
- if execution still cannot pass, keep the artifact explicitly blocked and do
  not replace cleanup primitives.

## Non-Goals

- Do not install new runtime packages automatically.
- Do not weaken the strict RBY1M/CuRobo readiness checker.
- Do not make a config-import-only artifact satisfy planner-backed cleanup
  primitive readiness.
- Do not replace cleanup primitives in this phase unless execute-mode strict
  readiness unexpectedly passes and a follow-up phase is planned.

## Deliverables

- ADR-0022 and this source plan.
- `.planning/phases/31-molmospaces-rby1m-curobo-warmup-readiness/31-01-rby1m-curobo-warmup-readiness-PLAN.md`.
- Worker-stage evidence in planner probe `run_result.json`.
- Planner probe report section for worker stages.
- Focused tests for timeout/stage evidence and report rendering.
- Local artifacts under `output/molmo-planner-rby1m-curobo-warmup/`.

## Acceptance Criteria

- A timeout artifact records the last worker stage before timeout.
- The report renders `Worker Stage Timeline` when worker events are present.
- Blocked-capability checker mode still accepts explicit blocked artifacts.
- Strict RBY1M/CuRobo readiness still rejects config-import-only and timeout
  artifacts.
- A local run either reaches strict RBY1M/CuRobo planner-backed execution or
  records a precise blocked stage without changing cleanup primitive claims.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-warmup --embodiment rby1m --probe-mode config_import --steps 2 --timeout-s 300`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked output/molmo-planner-rby1m-curobo-warmup/run_result.json`
- Strict readiness rejected the artifact with
  `--require-rby1m-curobo-ready`, as intended.

## Completion Evidence

Phase 31 completed as blocked-capability evidence, not as target runtime
readiness.

The 300-second local RBY1M/CuRobo warmup run records:

- `status=blocked_capability`;
- CuRobo importable and CUDA Torch available;
- `last_worker_stage=rby1m_config_import`;
- worker stage events for `worker_start`, `runtime_diagnostics`, and
  `rby1m_config_import_start`;
- `execution_attempted=false`;
- RBY1M/CuRobo gate blockers: `timeout`, `rby1m_execution_not_attempted`, and
  `rby1m_planner_not_backed`;
- a `Worker Stage Timeline` section in
  `output/molmo-planner-rby1m-curobo-warmup/report.html`.

Because config import did not finish, execute mode was not attempted and actual
planner-backed cleanup primitive replacement remains gated.
