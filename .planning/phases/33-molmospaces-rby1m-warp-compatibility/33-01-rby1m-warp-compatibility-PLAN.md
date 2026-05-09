# 33-01 RBY1M Warp Compatibility Plan

## Goal

Move the RBY1M/CuRobo execute probe past the known Warp API namespace mismatch
without patching installed dependencies or weakening strict readiness.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Add Warp API-shape diagnostics to planner probe runtime diagnostics.
3. [x] Add a probe-local `warp.torch.device_from_torch` compatibility adapter.
4. [x] Render/checker/test `Warp Compatibility` report evidence.
5. [x] Rerun local RBY1M/CuRobo execute mode with the isolated extension cache
   and strict readiness.

## Acceptance

- Runtime diagnostics record whether `warp.torch` and top-level Warp Torch
  bridge helpers exist.
- Execute artifacts record whether the compatibility adapter was applied.
- `report.html` renders a `Warp Compatibility` section when diagnostics are
  present.
- Blocked mode remains explicit and checker-gated.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  evidence.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo execute artifact under
  `output/molmo-planner-rby1m-warp-compatibility-execute/`.

## Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed.
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
  passed with 24 tests.
- `output/molmo-planner-rby1m-warp-compatibility-execute/run_result.json`
  records `warp_compatibility.adapter.applied=true` and
  `provided=["warp.torch.device_from_torch"]`.
- The execute artifact reached `execute_policy_construct_done`,
  `execute_policy_reset_done`, and `execute_policy_run_start`, proving the
  previous `warp.torch` blocker was passed.
- The artifact renders `Warp Compatibility`, `CuRobo Extension Cache`,
  `Worker Stage Timeline`, and `RBY1M CuRobo Gate`.
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility output/molmo-planner-rby1m-warp-compatibility-execute/run_result.json`
  passed.
- Strict readiness with `--require-rby1m-curobo-ready` rejected the artifact, as
  intended, because the planner run hit `OutOfMemoryError` before producing
  robot-state movement.

## Risks

- The adapter may only pass the first Warp namespace mismatch. Later planner
  execution may expose a deeper Warp/CuRobo incompatibility.
- A shimmed compatibility path must remain visible in reports and must not
  relabel cleanup-loop primitives as planner-backed.
