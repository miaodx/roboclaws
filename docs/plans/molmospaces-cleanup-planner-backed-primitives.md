# MolmoSpaces Cleanup Planner-Backed Primitives

**Status:** Completed under GSD Phase 27 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0014, ADR-0016, ADR-0017, ADR-0018
**Workflow:** `hybrid-phase-pipeline`

## Problem

ADR-0003 cleanup reports now show the full visual cleanup timeline and can
attach a strict standalone Franka planner proof. They still do not prove that
cleanup-loop subphases themselves are planner-backed. `pick`, `place`, and
`place_inside` remain `api_semantic` state edits; navigation and opening are
also semantic robot/object state updates rather than upstream planner
execution.

Before replacing those primitives, the repo needs a per-subphase evidence gate
that makes the target impossible to confuse with attached proof.

## Decision

Add a strict cleanup primitive gate for planner-backed cleanup execution.

This phase should:

- add a `cleanup_primitive_evidence` artifact derived from semantic substeps;
- render a report panel showing the provenance for each object-level
  `nav, pick, nav, open?, place` chain;
- add a checker flag that requires manipulation subphases to be
  `planner_backed`;
- add an accepted blocked-capability path for current artifacts that explicitly
  disclose that cleanup primitives are still `api_semantic`;
- keep `planner_backed_manipulation_proof` as attached evidence only.

## Non-Goals

- Do not relabel current `api_semantic` cleanup moves as planner-backed.
- Do not install CuRobo or claim RBY1M planner execution in this phase.
- Do not replace the standalone Franka proof checker.
- Do not remove the attached-proof report panel from ADR-0017.

## Deliverables

- ADR-0018 and this source plan.
- `.planning/phases/27-molmospaces-cleanup-planner-backed-primitives/27-01-cleanup-primitive-gate-PLAN.md`.
- Shared cleanup primitive evidence builder and validator.
- Cleanup report panel for the per-subphase provenance gate.
- Checker support for strict required and explicit blocked-capability modes.
- Local artifact showing the gate against the existing visual cleanup report.

## Completion Result

Phase 27 implemented the gate without changing cleanup-loop primitive behavior.
Generated cleanup artifacts now include `cleanup_primitive_evidence`, and the
shared report renders `Cleanup Primitive Gate` beside the existing visual views
and attached planner proof.

The local artifact
`output/molmo-realworld-cleanup-primitive-gate/report.html` shows the gate for a
MolmoSpaces/RBY1M cleanup run with robot views and an attached strict Franka
planner proof. Its cleanup primitive evidence is intentionally
`blocked_capability` because the actual cleanup subphases remain
`api_semantic`. The strict checker mode rejects the same artifact until those
subphases are replaced by real planner-backed execution.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- Generate a MolmoSpaces cleanup artifact with robot views and attached proof:
  `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-cleanup-primitive-gate --backend molmospaces_subprocess --include-robot --record-robot-views --generated-mess-count 2 --planner-proof-run-result output/molmo-planner-manipulation-probe-headless/run_result.json`
- Run the checker in accepted blocked-capability mode and confirm the strict
  planner-backed primitive requirement rejects current `api_semantic`
  primitives.
