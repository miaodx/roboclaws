# 31-01 RBY1M CuRobo Warmup Readiness Plan

## Goal

Turn the current RBY1M/CuRobo timeout into precise staged evidence, then rerun
the target runtime gate with enough warmup time to determine whether execution
can be attempted.

## Status

Planned 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [ ] Add worker-stage events to the planner probe around RBY1M config import,
   config construction, policy discovery, and execute-mode startup.
3. [ ] Persist worker stage history and last observed stage into
   `run_result.json`, including timeout artifacts.
4. [ ] Render worker stage history in planner probe reports and checker/test it.
5. [ ] Rerun local RBY1M/CuRobo config-import with a longer timeout; if it
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

## Risks

- First-time CuRobo CUDA extension JIT can be slow. The phase should record
  that as blocked evidence rather than hiding it behind a sparse timeout.
- Execute mode may still fail after config import; that must remain a blocker
  for actual cleanup primitive replacement.
