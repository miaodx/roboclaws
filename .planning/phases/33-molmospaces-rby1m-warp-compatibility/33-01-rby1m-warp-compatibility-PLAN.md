# 33-01 RBY1M Warp Compatibility Plan

## Goal

Move the RBY1M/CuRobo execute probe past the known Warp API namespace mismatch
without patching installed dependencies or weakening strict readiness.

## Status

Planned 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [ ] Add Warp API-shape diagnostics to planner probe runtime diagnostics.
3. [ ] Add a probe-local `warp.torch.device_from_torch` compatibility adapter.
4. [ ] Render/checker/test `Warp Compatibility` report evidence.
5. [ ] Rerun local RBY1M/CuRobo execute mode with the isolated extension cache
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

## Risks

- The adapter may only pass the first Warp namespace mismatch. Later planner
  execution may expose a deeper Warp/CuRobo incompatibility.
- A shimmed compatibility path must remain visible in reports and must not
  relabel cleanup-loop primitives as planner-backed.
