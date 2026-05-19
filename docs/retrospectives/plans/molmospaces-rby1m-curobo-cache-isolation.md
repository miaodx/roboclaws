# MolmoSpaces RBY1M CuRobo Cache Isolation

**Status:** Completed under GSD Phase 32 on 2026-05-09
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0019, ADR-0022, ADR-0023, Phase 31 evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 31 proved the target runtime still blocks at `rby1m_config_import`, but
the local Torch extension cache now shows a narrower failure shape:
`lbfgs_step_cu` has compiled object files and a stale-looking zero-byte `lock`
without a final `.so`, while no compiler process is running.

Retrying against the same global cache could keep waiting on stale cache state.
Deleting the cache would be too broad for an execution phase. The next safe
step is an isolated-cache retry that records extension cache state in the
artifact.

## Decision

Implement ADR-0023 as a runtime-enablement phase.

This phase should:

- add a planner probe option for an explicit Torch extension cache directory;
- pass that directory into the worker through `TORCH_EXTENSIONS_DIR`;
- record CuRobo extension cache diagnostics for `geom_cu`,
  `kinematics_fused_cu`, `tensor_step_cu`, `lbfgs_step_cu`, and
  `line_search_cu`;
- render a `CuRobo Extension Cache` report section;
- add checker/test coverage for cache diagnostics when requested;
- rerun RBY1M config import with an output-local cache directory and a longer
  timeout;
- if config import succeeds, attempt execute mode and strict
  `--require-rby1m-curobo-ready`;
- if execution still cannot pass, keep the artifact explicitly blocked and do
  not replace cleanup primitives.

## Non-Goals

- Do not delete or mutate the global Torch extension cache.
- Do not make cache-preflight success satisfy planner-backed readiness.
- Do not weaken the strict RBY1M/CuRobo gate.
- Do not replace cleanup primitives in this phase unless execute-mode strict
  readiness unexpectedly passes and a follow-up phase is planned.

## Deliverables

- ADR-0023 and this source plan.
- `.planning/milestones/v1.98-phases/32-molmospaces-rby1m-curobo-cache-isolation/32-01-rby1m-curobo-cache-isolation-PLAN.md`.
- Planner probe option for an isolated Torch extension cache.
- CuRobo extension cache diagnostics in `run_result.json`.
- Planner probe report section for CuRobo extension cache state.
- Focused tests and checker assertions for cache diagnostics.
- Local artifacts under `output/molmo-planner-rby1m-curobo-cache-isolation/`.

## Acceptance Criteria

- A run can record the configured `TORCH_EXTENSIONS_DIR`.
- The artifact records each known CuRobo extension's directory, `.so` presence,
  lock presence, and files.
- The report renders `CuRobo Extension Cache` when diagnostics are present.
- Blocked-capability checker mode still accepts explicit blocked artifacts.
- Strict RBY1M/CuRobo readiness still rejects config-import-only and timeout
  artifacts.
- A local isolated-cache run either reaches strict RBY1M/CuRobo planner-backed
  execution or records a precise blocked stage without changing cleanup
  primitive claims.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-cache-isolation --embodiment rby1m --probe-mode config_import --torch-extensions-dir output/molmo-planner-rby1m-curobo-cache-isolation/torch_extensions --steps 2 --timeout-s 900`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache output/molmo-planner-rby1m-curobo-cache-isolation/run_result.json`
- Execute mode artifact:
  `output/molmo-planner-rby1m-curobo-cache-isolation-execute/run_result.json`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache output/molmo-planner-rby1m-curobo-cache-isolation-execute/run_result.json`
- Strict readiness rejected the execute artifact with
  `--require-rby1m-curobo-ready`, as intended.

## Completion Evidence

Phase 32 completed as cache-isolation and blocked execute evidence, not as
target runtime readiness.

The isolated-cache run records:

- configured `TORCH_EXTENSIONS_DIR` under
  `output/molmo-planner-rby1m-curobo-cache-isolation/torch_extensions`;
- 5/5 known CuRobo extension `.so` files present:
  `geom_cu`, `kinematics_fused_cu`, `tensor_step_cu`, `lbfgs_step_cu`, and
  `line_search_cu`;
- 0 extension lock files;
- config import reaching `rby1m_policy_class` with
  `CuroboPickAndPlacePlannerPolicy`;
- execute mode reaching `execute_policy_construct`;
- execute mode blocked by `AttributeError: module 'warp' has no attribute
  'torch'`;
- report sections for `CuRobo Extension Cache`, `Worker Stage Timeline`, and
  `RBY1M CuRobo Gate`.

Because execute mode did not produce planner-backed robot-state movement,
actual planner-backed cleanup primitive replacement remains gated.
