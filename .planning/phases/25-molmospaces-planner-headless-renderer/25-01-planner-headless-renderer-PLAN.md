# 25-01 Planner Headless Renderer Plan

## Goal

Make the standalone Franka planner manipulation probe run headlessly so the
strict ADR-0014 planner-backed proof gate can either pass or expose the next
real planner blocker after renderer setup.

## Status

Planned 2026-05-09.

## Tasks

1. Add ADR/source-plan documentation and update roadmap/state/context references.
2. Add a worker-only MolmoSpaces renderer adapter that passes `device_id=0` to
   `MjOpenGLRenderer` during execute-mode probes.
3. Set EGL environment variables for adapted execute-mode workers.
4. Record renderer override diagnostics in `runtime_diagnostics`.
5. Add focused tests and run the strict Franka execute-mode proof gate.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py`
- `.venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-manipulation-probe-headless --probe-mode execute --embodiment franka --steps 2 --timeout-s 180`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --require-planner-backed output/molmo-planner-manipulation-probe-headless/run_result.json`

## Risks

- The renderer adapter may reveal a later planner/policy blocker rather than a
  passing proof.
- CuRobo remains missing for RBY1M and is out of scope.
- The adapter must stay probe-local and must not mutate the upstream
  MolmoSpaces checkout.
