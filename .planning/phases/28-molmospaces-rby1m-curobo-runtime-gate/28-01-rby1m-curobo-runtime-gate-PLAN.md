# 28-01 RBY1M CuRobo Runtime Gate Plan

## Goal

Create a first-class RBY1M/CuRobo readiness gate so later planner-backed
cleanup primitive replacement cannot accidentally depend on standalone Franka
proof or generic planner diagnostics.

## Status

Planned 2026-05-09.

## Tasks

1. Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. Add an RBY1M/CuRobo gate builder that derives readiness from planner probe
   artifacts.
3. Render the gate in the shared planner probe report.
4. Add checker modes:
   - accept explicit blocked-capability evidence for missing CuRobo/current
     RBY1M blockers;
   - require strict RBY1M/CuRobo readiness for future cleanup primitive
     replacement.
5. Add focused tests and generate/validate a local RBY1M artifact.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_rby1m_curobo_gate.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py`
- `.venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-gate --embodiment rby1m --probe-mode config_import --steps 2 --timeout-s 120`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked output/molmo-planner-rby1m-curobo-gate/run_result.json`
- Strict gate should reject the same artifact with
  `--require-rby1m-curobo-ready` unless the local runtime genuinely has RBY1M
  CuRobo planner execution.

## Risks

- This can be mistaken for installing CuRobo. It is only a gate and artifact
  boundary.
- If CuRobo becomes available locally, the strict path must still require
  execution and nonzero robot-state movement, not just import success.
