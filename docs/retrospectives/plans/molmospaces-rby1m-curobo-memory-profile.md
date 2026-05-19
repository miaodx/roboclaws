# MolmoSpaces RBY1M CuRobo Memory Profile

**Status:** Completed under GSD Phase 35 on 2026-05-09
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0019, ADR-0025, ADR-0026, Phase 34 evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 34 turned the RBY1M/CuRobo OOM into structured evidence. The target
execute path reaches `execute_policy_run_start` with about 9.1 GiB free, then
CuRobo trajectory planning reserves about 9.9 GiB and fails before robot-state
movement.

The next useful slice is not cleanup primitive replacement yet. The next slice
is a controlled retry mechanism for lower-memory CuRobo planning settings, with
all overrides visible in artifacts and reports.

## Decision

Implement ADR-0026 as a target-runtime retry phase.

This phase should:

- add a named RBY1M/CuRobo low-memory profile to the planner probe;
- expose explicit override flags for policy batch count and planner seed/step
  settings;
- apply those overrides only in the standalone probe worker;
- record requested/effective memory profile settings in `run_result.json`;
- render a `CuRobo Memory Profile` report section;
- add checker/test coverage for required memory-profile evidence;
- rerun RBY1M execute mode with isolated CuRobo extensions, Warp compatibility,
  CUDA memory evidence, and the low-memory profile;
- keep cleanup primitive replacement gated until target execute proof exists.

## Non-Goals

- Do not patch upstream MolmoSpaces/CuRobo source files.
- Do not disable collision avoidance in the default low-memory profile.
- Do not delete caches or kill GPU processes.
- Do not tune cleanup-loop primitives in this phase.

## Deliverables

- ADR-0026 and this source plan.
- `.planning/milestones/v1.98-phases/35-molmospaces-rby1m-curobo-memory-profile/35-01-rby1m-curobo-memory-profile-PLAN.md`.
- Probe-local memory-profile CLI flags.
- CuRobo memory-profile evidence in `run_result.json`.
- Planner probe report section for `CuRobo Memory Profile`.
- Checker flag for required memory-profile evidence.
- Focused tests.
- Local execute artifact under
  `output/molmo-planner-rby1m-curobo-memory-profile-execute/`.

## Acceptance Criteria

- The default probe behavior remains unchanged when no memory profile is
  requested.
- The low-memory profile records every applied override.
- The report renders `CuRobo Memory Profile` when profile evidence is present.
- The checker can require memory-profile evidence along with CUDA memory, Warp,
  and CuRobo extension-cache evidence.
- The local RBY1M execute run either produces planner-backed robot-state
  movement or records the next precise blocked stage with memory snapshots.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-memory-profile-execute --embodiment rby1m --probe-mode execute --torch-extensions-dir output/molmo-planner-rby1m-curobo-cache-isolation/torch_extensions --renderer-device-id 0 --rby1m-curobo-memory-profile low --steps 2 --timeout-s 600`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-curobo-memory-profile output/molmo-planner-rby1m-curobo-memory-profile-execute/run_result.json`

## Completion Evidence

Phase 35 completed as a strict target RBY1M/CuRobo standalone proof with visible
low-memory tuning.

The execute artifact records:

- `status=planner_backed`;
- `rby1m_curobo_gate.rby1m_curobo_ready=true`;
- upstream policy class `CuroboPickAndPlacePlannerPolicy`;
- 2 executed steps;
- `max_abs_qpos_delta=0.04167305757535879`;
- initial and final head-camera PNGs under `planner_views/`;
- `CuRobo Memory Profile`, `CUDA Memory Headroom`, `Warp Compatibility`,
  `CuRobo Extension Cache`, and `RBY1M CuRobo Gate` report sections.

The low-memory profile is visible and keeps collision avoidance enabled:

- policy `batch_size`: `4 -> 1`;
- policy `max_batch_plan_attempts`: `4 -> 1`;
- policy `enable_collision_avoidance`: `true -> true`;
- planner `num_trajopt_seeds`: `12 -> 1`;
- planner `num_ik_seeds`: `128 -> 16`;
- planner `max_attempts`: `15 -> 1`;
- planner `trajopt_tsteps`: `48 -> 24`;
- planner `enable_finetune_trajopt`: `true -> false`.

The memory profile changed the outcome from OOM to planner-backed execution:

- `execute_policy_run_start`: about 9.2 GiB free, 1.1 GiB PyTorch reserved;
- `execute_policy_run_done`: about 9.2 GiB free, 1.1 GiB PyTorch reserved;
- no capability blockers were recorded.

This proves standalone target RBY1M/CuRobo planner-backed manipulation under a
visible low-memory profile. It does not yet replace the ADR-0003 cleanup loop's
own `api_semantic` primitives; that remains the next implementation slice.
