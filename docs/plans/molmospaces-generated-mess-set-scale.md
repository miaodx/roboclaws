# MolmoSpaces Generated Mess Set Scale

**Status:** Accepted for execution 2026-05-09 under GSD Phase 15
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0005, Phase 14 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 14 implemented the ADR-0003 public/private cleanup boundary and restored
visual report parity, but it intentionally kept the inherited
`generated_mess_count=5`. That leaves a direct `CONTEXT.md` gap: v1 should use a
hidden Generated Mess Set of roughly 10-20 objects, and the Scorer should
evaluate the set as a set rather than only the first few selected objects.

## Decision

Implement ADR-0005 as the next incremental MolmoSpaces cleanup phase:

- make the MolmoSpaces subprocess target selector accept a requested
  `generated_mess_count`;
- default the ADR-0003 real-world harness CLI/recipe to 10 generated objects;
- derive the private success threshold from the actual generated count using
  the existing 70% restoration rule;
- keep the Generated Mess Set, hidden count, target receptacles, and acceptable
  destinations out of Agent View;
- preserve the shared semantic timeline and robot-view visual report surfaces
  introduced in Phase 14.

## Non-Goals

- Do not switch to model-agent/OpenClaw policies yet.
- Do not claim planner-backed RBY1M/Franka manipulation; primitives remain
  `api_semantic`.
- Do not remove the five-object synthetic fixture used by fast tests.
- Do not expose a global movable-object inventory to the ADR-0003 Cleanup
  Agent.

## Deliverables

- ADR-0005 and this source plan.
- `.planning/phases/15-molmospaces-generated-mess-set-scale/15-01-generated-mess-set-scale-PLAN.md`.
- Configurable generated mess count through the real MolmoSpaces subprocess
  worker/backend and ADR-0003 harness CLI.
- Report/checker support for requested and actual generated counts.
- Focused tests covering the configuration and checker behavior.
- Real MolmoSpaces one-seed evidence with all Phase 14 visual report views and
  at least 10 generated objects.

## Acceptance Criteria

- `just harness::molmo-realworld-cleanup` requests 10 generated objects by
  default.
- The worker fails clearly if a requested count cannot be satisfied by the
  selected scene.
- `run_result.json` records both `requested_generated_mess_count` and
  `generated_mess_count`.
- `private_evaluation.generated_mess_count >= 10` for the real evidence run.
- `scripts/check_molmo_realworld_cleanup_result.py` can enforce a minimum
  generated count.
- `report.html` still includes Agent View, Private Evaluation, Final Result,
  Cleanup Trace, and Robot View Timeline sections.
