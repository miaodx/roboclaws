# MolmoSpaces Planner-Backed Manipulation Proof Gate

**Status:** Completed 2026-05-09 under GSD Phase 23
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0009, ADR-0014, Phase 22 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

The MolmoSpaces demos now share a visual cleanup report underlay, enforce the
semantic `nav -> pick -> nav -> open? -> place` cleanup loop, and can produce
ADR-0003 real-world-style artifacts. They still do not prove low-level
planner-backed manipulation. Current cleanup effects are `api_semantic`
state/object updates in the fake backend or real MuJoCo subprocess worker.

The broader discussion explicitly calls planner-backed RBY1M/Franka
manipulation separate from cleanup decision/search realism. The next step is to
make that boundary testable so future work cannot accidentally claim real
manipulation from semantic state edits.

## Decision

Implement ADR-0014 as a provenance gate and probe slice.

This phase should:

- keep existing cleanup execution labeled `api_semantic`;
- add shared manipulation-provenance metadata to cleanup artifacts;
- render a `Manipulation Provenance` report section through
  `roboclaws/molmo_cleanup/report.py`;
- add a standalone MolmoSpaces planner manipulation probe artifact and report;
- distinguish planner class/config availability from actual planner-backed
  execution;
- add a checker that can accept honest `blocked_capability` evidence but only
  passes `--require-planner-backed` when a real planner policy executed and
  moved robot state;
- document local blockers such as missing CuRobo or simulator crashes without
  faking cleanup success.

## Non-Goals

- Do not relabel existing cleanup pick/place/open primitives as real robot
  manipulation.
- Do not require a live VLM or OpenClaw Gateway.
- Do not clone the cleanup report renderer.
- Do not make planner-backed manipulation part of the default ADR-0003 cleanup
  success gate yet.

## Deliverables

- ADR-0014 and this source plan.
- `.planning/milestones/v1.98-phases/23-molmospaces-planner-backed-manipulation-proof/23-01-planner-backed-manipulation-proof-PLAN.md`.
- Shared manipulation provenance helpers.
- Report support for `Manipulation Provenance` and a planner probe report.
- Planner probe CLI and checker CLI.
- Harness/verify recipes for the probe gate.
- Tests proving `api_semantic` cannot satisfy planner-backed proof.

## Acceptance Criteria

- Existing cleanup reports include an explicit `Manipulation Provenance` panel
  when provenance metadata is present.
- Existing cleanup runs still record `primitive_provenance=api_semantic`.
- The planner probe writes `run_result.json`, stdout/stderr artifacts, and a
  shared-underlay `report.html`.
- The checker accepts a blocked-capability probe only when explicitly allowed.
- The checker rejects `api_semantic` evidence for `--require-planner-backed`.
- The checker can require planner-backed proof using execution evidence fields:
  planner policy class, nonzero robot-state delta, no blockers, and no semantic
  state-edit fallback.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmo_manipulation_provenance.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just verify::molmo-planner-manipulation-probe`

## Completion Evidence

- Existing cleanup artifacts now include `manipulation_evidence` that labels
  current cleanup effects as `api_semantic` and not strict planner proof.
- The shared cleanup report renderer now renders `Manipulation Provenance` and
  the standalone planner probe report.
- `scripts/run_molmo_planner_manipulation_probe.py` writes a probe
  `run_result.json`, stdout/stderr artifacts, and `report.html`.
- `scripts/check_molmo_planner_manipulation_probe.py` accepts
  blocked-capability evidence only with `--accept-blocked-capability` and
  rejects `api_semantic` for `--require-planner-backed`.
- `just verify::molmo-planner-manipulation-probe` passed and produced an
  explicit blocked-capability artifact: planner class
  `PickAndPlacePlannerPolicy` is available, but execution proof was not
  attempted by the default safe gate.
