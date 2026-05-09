# 44-01 Planner Proof Bundle Cleanup Plan

## Goal

Let ADR-0003 cleanup artifacts use multiple bound planner proofs so every
cleaned object can be matched to its own proof-backed primitive executor.

## Status

Planned 2026-05-10.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add a proof-bundle schema/helper for multiple strict planner proof
   attachments.
3. [ ] Preserve backward-compatible single-proof attachment behavior.
4. [ ] Extend the cleanup harness to accept/select multiple proof attachments
   by observed handle and target fixture.
5. [ ] Render multiple attached proof views in the shared Cleanup Artifact
   Report.
6. [ ] Update checker/bridge validation so full proof coverage can pass the
   existing cleanup primitive and planner bridge gates.
7. [ ] Add focused tests for full coverage, partial coverage, mismatches, and
   report rendering.
8. [ ] Run focused verification gates.

## Acceptance

- Default ADR-0003 cleanup runs remain `api_semantic`.
- Existing single `--planner-proof-run-result` artifacts remain accepted.
- Multiple strict bound proofs can be attached to one cleanup run.
- The harness uses only the proof whose binding matches the current observed
  handle and target fixture.
- A full synthetic cleanup with matching proof coverage for every cleaned object
  passes `require_planner_backed_cleanup_primitives` and
  `require_planner_cleanup_bridge_ready`.
- Partial or mismatched proof bundles leave uncovered objects on
  `api_semantic` and keep the bridge blocked.
- The report keeps one shared visual underlay and shows every attached proof's
  initial/final views.

## Verification

- `uv run ruff check` on changed Python/tests.
- `uv run ruff format --check` on changed Python/tests.
- Focused pytest for proof bundle helpers, cleanup harness, checker, planner
  bridge, and report coverage.
- Current real visual artifact checker in blocked mode.

## Risks

- Treating a proof bundle as blanket target readiness could hide a missing
  object binding. Bundle readiness must require each selected proof to remain
  strict and object/target-bound.
- Changing single-proof fields could break existing artifacts and checker
  gates. Keep the single-proof path backward compatible.
