# MolmoSpaces Planner Runtime Diagnostics

**Status:** Completed under GSD Phase 24
**Created:** 2026-05-09
**Source:** ADR-0014, ADR-0015, Phase 23 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

The Phase 23 planner-backed manipulation proof gate correctly refuses to treat
`api_semantic` cleanup as real manipulation. The first strict local probes did
not pass:

- Franka execute mode terminated by `SIGSEGV`.
- RBY1M config import failed because `curobo` is missing.

The next useful slice is not to claim planner execution, but to make those
blockers reproducible and actionable in the same report system.

## Decision

Add runtime diagnostics to the planner manipulation probe.

This phase should:

- enable Python faulthandler for the MolmoSpaces worker subprocess;
- record module availability and package versions for planner-relevant
  dependencies;
- include diagnostics in `run_result.json`;
- render a `Runtime Diagnostics` report section through the shared report
  renderer;
- keep strict planner-backed proof semantics unchanged.

## Non-Goals

- Do not install CuRobo or GPU packages automatically.
- Do not make `blocked_capability` pass `--require-planner-backed`.
- Do not add another report implementation.

## Deliverables

- ADR-0015 and this source plan.
- `.planning/phases/24-molmospaces-planner-runtime-diagnostics/24-01-planner-runtime-diagnostics-PLAN.md`.
- Planner probe diagnostics in run results and reports.
- Tests proving diagnostics render and do not alter strict proof semantics.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_manipulation_provenance.py`
- `ruff check` / `ruff format --check` on changed Python files.
- `just verify::molmo-planner-manipulation-probe`

## Completion Evidence

Completed 2026-05-09.

- Focused pytest passed with `10 passed`.
- `uv run ruff check` and `uv run ruff format --check` passed on changed
  Python files.
- `just verify::molmo-planner-manipulation-probe` passed and produced
  `output/molmo-planner-manipulation-probe-harness/run_result.json` plus a
  shared-underlay `report.html` with `Runtime Diagnostics`.
- Franka execute-mode probe produced accepted `blocked_capability` evidence at
  `output/molmo-planner-manipulation-probe-execute/run_result.json`; stderr now
  includes a faulthandler stack for the `SIGSEGV` in MuJoCo/GLFW window
  creation during task sampling.
- RBY1M config-import probe produced accepted `blocked_capability` evidence at
  `output/molmo-planner-manipulation-probe-rby1m/run_result.json` with
  `curobo.available=false`.

Strict planner-backed cleanup execution remains separate until a probe passes
the ADR-0014 `--require-planner-backed` gate.
