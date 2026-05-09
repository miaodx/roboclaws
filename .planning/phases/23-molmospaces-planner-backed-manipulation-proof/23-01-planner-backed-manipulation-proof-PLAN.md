# 23-01 Planner-Backed Manipulation Proof Gate Plan

## Goal

Add a concrete artifact, report, and checker boundary for MolmoSpaces
planner-backed manipulation so `api_semantic` cleanup effects cannot be confused
with real RBY1M/Franka planner execution.

## Status

Planned 2026-05-09.

## Tasks

1. Add ADR/source-plan documentation and update roadmap/state/context
   references for Phase 23.
2. Add shared manipulation provenance helpers that describe `api_semantic`,
   blocked capability, and planner-backed execution states.
3. Attach manipulation provenance to existing cleanup run results without
   changing their primitive behavior.
4. Render `Manipulation Provenance` and planner probe reports through the
   shared cleanup report underlay.
5. Add a MolmoSpaces planner manipulation probe CLI plus checker CLI.
6. Add harness/verify recipes, tests, summary, and verification docs.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmo_manipulation_provenance.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py`
- `ruff check` / `ruff format --check` on changed Python files.
- `just verify::molmo-planner-manipulation-probe`

## Risks

- A planner class import can be mistaken for planner-backed execution. The
  checker must keep those states separate.
- The local MolmoSpaces planner runtime may be blocked by missing CuRobo, GPU,
  JAX, or simulator crashes. Blocked evidence is useful, but must not pass the
  real proof gate.
- Report additions must reuse `roboclaws/molmo_cleanup/report.py`; a second
  report path would reintroduce the report parity gap.
