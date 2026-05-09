# 35-01 RBY1M CuRobo Memory Profile Plan

## Goal

Retry target RBY1M/CuRobo execute mode with a visible, probe-local low-memory
planning profile before deciding whether cleanup primitive replacement is
blocked on planner tuning or hardware.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Add probe CLI/profile support for RBY1M CuRobo low-memory settings.
3. [x] Record requested/effective profile settings in runtime evidence.
4. [x] Render/checker/test `CuRobo Memory Profile` report evidence.
5. [x] Rerun local RBY1M/CuRobo execute mode with the low-memory profile and
   record whether the blocker changes or strict target proof passes.

## Acceptance

- No-profile probes keep current default behavior.
- Low-memory profile overrides are visible in `run_result.json` and
  `report.html`.
- The default low-memory profile keeps collision avoidance enabled.
- Blocked mode remains explicit and checker-gated.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  robot-state movement.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo execute artifact under
  `output/molmo-planner-rby1m-curobo-memory-profile-execute/`.

## Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed.
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed with 28 tests.
- `output/molmo-planner-rby1m-curobo-memory-profile-execute/run_result.json`
  records `status=planner_backed`, `steps_executed=2`, and
  `max_abs_qpos_delta=0.04167305757535879`.
- The strict checker passed with `--require-planner-backed`,
  `--require-rby1m-curobo-ready`, `--require-curobo-extension-cache`,
  `--require-warp-compatibility`, `--require-cuda-memory`, and
  `--require-curobo-memory-profile`.
- The artifact renders `Planner Probe Views`, `CUDA Memory Headroom`,
  `CuRobo Memory Profile`, `Warp Compatibility`, `CuRobo Extension Cache`, and
  `RBY1M CuRobo Gate`.
- The low-memory profile kept `enable_collision_avoidance=true` while reducing
  policy batch/attempt counts and planner seed/timestep counts.

## Risks

- Lower-memory settings may reduce plan quality and move the blocker from OOM
  to no-trajectory-found.
- A tuned successful probe is still standalone target-runtime proof, not
  cleanup-loop primitive replacement.
