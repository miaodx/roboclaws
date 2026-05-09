# 42-01 Observed Handle Planner Binding Plan

## Goal

Bridge ADR-0003 observed handles to planner-facing sampled task names so
planner probe proof can match upstream task aliases while cleanup primitive
binding still matches the public cleanup subphase request.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add an observed-handle planner binding helper/schema.
3. [ ] Add backend runtime planner-name binding for semantic and MolmoSpaces
   subprocess backends.
4. [ ] Extend planner probe cleanup binding requests with planner-facing object
   and target aliases.
5. [ ] Ensure promoted cleanup primitive binding keeps public observed handle
   IDs for executor matching.
6. [ ] Render/check planner alias binding evidence in reports.
7. [ ] Add focused tests and run verification gates.

## Acceptance

- Observed handles resolve only after public observation registered the handle.
- Planner alias fields can match sampled upstream task names without replacing
  the cleanup-facing object/target IDs.
- Probe-backed executor accepts a promoted binding whose `object_id` is the
  observed handle and whose alias evidence matched the sampled planner task.
- Planner aliases remain artifact/private runtime evidence and are not added to
  Agent View.
- Generic Phase 41 no-alias behavior remains backward compatible.

## Verification

- `uv run ruff check` on changed Python/tests.
- `uv run ruff format --check` on changed Python/tests.
- Focused pytest for real-world contract binding, planner probe binding,
  probe-backed executor, report/checker coverage.

## Risks

- Leaking planner aliases through public ADR-0003 tool responses would violate
  the Agent View boundary.
- Treating a planner alias match as cleanup execution would overclaim. This
  phase should only make a proof consumable by the executor; the actual shared
  loop remains blocked until a later slice wires the executor into cleanup
  subphases.
