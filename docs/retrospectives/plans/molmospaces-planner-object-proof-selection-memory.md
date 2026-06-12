# MolmoSpaces Planner-Object Proof Selection Memory

**Status:** Completed for Phase 89 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0080-scope-proof-selection-memory-by-planner-object.md`

## Goal

Select new exact-scene proof candidates from a broader ADR-0003 cleanup
artifact without retrying known grasp-infeasible internal planner object/target
pairs.

## Problem

The Phase88 carry-forward dry-run correctly filtered both source requests from
the current cleanup artifact, but that left no commands. A broader cleanup
artifact can provide more source requests, yet it also reuses local proof IDs
and public `observed_*` handles.

That means selection memory must avoid two opposite failures:

- excluding new requests only because their local `request_id` collides with a
  prior manifest;
- retrying an already blocked internal planner object because it now has a
  different public observed handle.

## Scope

- Generate a broader exact-scene source artifact with more generated mess
  objects and proof requests.
- Guard request-ID matches so local IDs are not treated as globally stable.
- Add private planner-object/public-target memory for prior blocker matching.
- Add regression coverage for colliding request IDs and changed observed
  handles.
- Validate a dry-run that selects new broader candidates and filters known
  blocked internal pairs.

## Non-Goals

- Do not execute the selected broader candidates in this slice.
- Do not expose planner aliases to Agent View.
- Do not create a new report renderer or diverge from the shared runner report
  path.
- Do not claim planner-backed cleanup readiness from selected commands alone.

## Acceptance Criteria

- A broader ADR-0003 source artifact emits more than the two exhausted source
  requests.
- Prior `request_id` collisions do not exclude unrelated current requests.
- Prior blockers still exclude requests that share the same internal planner
  object and public target.
- The proof-bundle dry-run selects at least one new exact-scene request and
  reports any excluded known blockers with `prior_result_match_kind`.
- Focused lint, format, pytest, and runner checker validation pass.

## Result

Implemented.

The broader source artifact at
`output/debug-phase89-broader-candidate-source/` produced 10 ready proof
requests, 10 semantic cleanup rows, and 176 robot-view images.

Before the selector fix, the dry-run incorrectly excluded new `proof_001` and
`proof_002` requests by local request-ID collision and selected two known
blocked internal pairs under new observed handles. After the fix, the dry-run
at `output/debug-phase89-planner-pair-selection-dry-run/` selected 8 new
commands:

`proof_001`, `proof_002`, `proof_003`, `proof_004`, `proof_005`, `proof_006`,
`proof_008`, and `proof_010`.

It excluded only `proof_007` and `proof_009` by
`prior_result_match_kind=planner_object_target`, preserving the known
`grasp_feasibility` blocker detail.

Verification:

- Focused ruff and format checks passed for the selector and test files.
- Focused pytest passed for the full proof-request selection test module.
- The broader source artifact passed the real-world cleanup checker.
- The Phase89 dry-run manifest passed the proof-bundle runner checker.
