# 31-01 RBY1M CuRobo Warmup Readiness Plan

## Goal

Turn the current RBY1M/CuRobo timeout into precise staged evidence, then rerun
the target runtime gate with enough warmup time to determine whether execution
can be attempted.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Add worker-stage events to the planner probe around RBY1M config import,
   config construction, policy discovery, and execute-mode startup.
3. [x] Persist worker stage history and last observed stage into
   `run_result.json`, including timeout artifacts.
4. [x] Render worker stage history in planner probe reports and checker/test it.
5. [x] Rerun local RBY1M/CuRobo config-import with a longer timeout; if it
   passes, attempt execute mode and strict readiness.

## Acceptance

- Timeout artifacts identify the last worker stage.
- `report.html` renders a `Worker Stage Timeline` section when stage events are
  present.
- Blocked mode remains explicit and checker-gated.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  evidence.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- Local RBY1M/CuRobo warmup artifact under
  `output/molmo-planner-rby1m-curobo-warmup/`.

## Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
  passed.
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
  passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
  passed with 14 tests.
- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-warmup --embodiment rby1m --probe-mode config_import --steps 2 --timeout-s 300`
  produced `status=blocked_capability`.
- `output/molmo-planner-rby1m-curobo-warmup/run_result.json` records
  `last_worker_stage=rby1m_config_import`, CuRobo available, CUDA Torch
  available, `execution_attempted=false`, and gate blockers
  `timeout`, `rby1m_execution_not_attempted`, and `rby1m_planner_not_backed`.
- `output/molmo-planner-rby1m-curobo-warmup/report.html` renders
  `Worker Stage Timeline` with three events: `worker_start`,
  `runtime_diagnostics`, and `rby1m_config_import_start`.
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked output/molmo-planner-rby1m-curobo-warmup/run_result.json`
  passed.
- Strict readiness with `--require-rby1m-curobo-ready` rejected the artifact, as
  intended, because config import did not finish and execute mode was not
  attempted.

## Risks

- First-time CuRobo CUDA extension JIT can be slow. The phase should record
  that as blocked evidence rather than hiding it behind a sparse timeout.
- Execute mode may still fail after config import; that must remain a blocker
  for actual cleanup primitive replacement.
