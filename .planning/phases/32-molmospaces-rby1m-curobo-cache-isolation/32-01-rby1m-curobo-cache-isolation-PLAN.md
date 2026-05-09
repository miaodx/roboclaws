# 32-01 RBY1M CuRobo Cache Isolation Plan

## Goal

Make the RBY1M/CuRobo warmup retry independent of stale global Torch extension
cache state and record extension-cache evidence in the planner probe artifact.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Add a planner probe option for an explicit `TORCH_EXTENSIONS_DIR`.
3. [x] Record CuRobo extension cache diagnostics for known CUDA extensions.
4. [x] Render cache diagnostics in planner probe reports and checker/test it.
5. [x] Rerun local RBY1M/CuRobo config-import with an output-local cache and a
   longer timeout; if it passes, attempt execute mode and strict readiness.

## Acceptance

- Runtime diagnostics record the effective Torch extension cache directory.
- `run_result.json` records known CuRobo extension `.so` and lock state.
- `report.html` renders a `CuRobo Extension Cache` section when cache
  diagnostics are present.
- Blocked mode remains explicit and checker-gated.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  evidence.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo isolated-cache artifact under
  `output/molmo-planner-rby1m-curobo-cache-isolation/`.

## Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed.
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed with 22 tests.
- The first isolated-cache config-import run compiled the CuRobo extensions and
  reached `rby1m_policy_class` in 388 seconds.
- The warm isolated-cache config-import rerun under
  `output/molmo-planner-rby1m-curobo-cache-isolation/` reached
  `rby1m_policy_class` in about 15 seconds and records 5/5 known CuRobo
  extension `.so` files with 0 locks.
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache output/molmo-planner-rby1m-curobo-cache-isolation/run_result.json`
  passed.
- Execute mode under
  `output/molmo-planner-rby1m-curobo-cache-isolation-execute/` reached
  `execute_policy_construct` but failed with `AttributeError: module 'warp' has
  no attribute 'torch'`.
- The execute artifact renders `CuRobo Extension Cache`,
  `Worker Stage Timeline`, and `RBY1M CuRobo Gate`, with 5/5 known extension
  `.so` files and 0 locks.
- Strict readiness with `--require-rby1m-curobo-ready` rejected the execute
  artifact, as intended, because no planner-backed robot-state movement was
  produced.

## Risks

- A clean isolated cache may spend many minutes compiling CuRobo extensions.
  That should be reported as warmup evidence, not as cleanup primitive proof.
- Execute mode may still fail after config import; that remains a blocker for
  actual cleanup primitive replacement.
