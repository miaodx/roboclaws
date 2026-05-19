# MolmoSpaces RBY1M CuRobo Runtime Gate

**Status:** Completed under GSD Phase 28 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0014, ADR-0015, ADR-0016, ADR-0018, ADR-0019
**Workflow:** `hybrid-phase-pipeline`

## Problem

The cleanup report now shows both attached strict Franka planner proof and a
per-subphase cleanup primitive gate. Actual cleanup primitive replacement still
depends on the target robot path, RBY1M with CuRobo. Existing artifacts can
diagnose missing CuRobo, but there is no first-class gate that says "this
artifact proves the target RBY1M planner runtime is ready."

## Decision

Add a dedicated RBY1M/CuRobo runtime gate to the planner probe underlay.

This phase should:

- derive an `rby1m_curobo_gate` block from planner probe `run_result.json`;
- render the gate in planner probe reports;
- add checker flags for explicit blocked-capability acceptance and strict
  RBY1M/CuRobo readiness;
- keep Franka strict proof valid for standalone planner proof, but invalid for
  the RBY1M/CuRobo readiness claim;
- generate a local RBY1M blocked artifact if CuRobo or the RBY1M runtime remains
  unavailable.

## Non-Goals

- Do not install CuRobo automatically.
- Do not replace cleanup primitives.
- Do not make Franka proof satisfy RBY1M readiness.
- Do not weaken ADR-0018 cleanup primitive strictness.

## Deliverables

- ADR-0019 and this source plan.
- `.planning/milestones/v1.98-phases/28-molmospaces-rby1m-curobo-runtime-gate/28-01-rby1m-curobo-runtime-gate-PLAN.md`.
- Shared RBY1M/CuRobo gate builder and validator.
- Planner probe report and checker support for blocked and strict modes.
- Local artifact showing the current RBY1M/CuRobo state.

## Completion Result

Phase 28 implemented the target-runtime gate without changing cleanup primitive
execution. Planner probe artifacts now include `rby1m_curobo_gate`, and the
shared planner probe report renders `RBY1M CuRobo Gate`.

The local artifact
`output/molmo-planner-rby1m-curobo-gate/report.html` shows the current RBY1M
state as explicit `blocked_capability`: after installing the pinned CuRobo
extra and CUDA PyTorch into the isolated MolmoSpaces runtime, CuRobo is
importable, but the RBY1M config-import probe still times out during CuRobo
CUDA-extension JIT warmup before planner execution is attempted. The strict
checker mode rejects the same artifact until RBY1M/CuRobo planner execution is
genuinely available.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- Focused pytest for the new gate, planner report, and planner probe checker.
- Generate an RBY1M planner probe artifact:
  `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-gate --embodiment rby1m --probe-mode config_import --steps 2 --timeout-s 60`
- Run the checker in accepted blocked-capability mode and confirm strict
  RBY1M/CuRobo readiness rejects the current artifact unless CuRobo and RBY1M
  planner execution are genuinely available.
