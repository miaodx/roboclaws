# MolmoSpaces RBY1M CuRobo Memory Profile

**Status:** Planned for GSD Phase 35 on 2026-05-09
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
- `.planning/phases/35-molmospaces-rby1m-curobo-memory-profile/35-01-rby1m-curobo-memory-profile-PLAN.md`.
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
