# MolmoSpaces Planner Proof Bundle Cleanup

**Status:** Completed in GSD Phase 44 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0034, ADR-0035
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 43 proved one matching bound proof can drive one observed-handle cleanup
attempt through the probe-backed executor. The broader report and bridge still
remain blocked on multi-object cleanup because one proof only covers one
object/target binding while the rest of a normal ADR-0003 run stays
`api_semantic`.

## Decision

Add a proof-bundle slice that lets the ADR-0003 cleanup harness attach multiple
strict bound planner proofs and select the proof matching each cleanup object
and target fixture.

This phase should:

- add a `planner_backed_cleanup_proof_bundle_v1` representation;
- keep the existing single-proof attachment behavior backward compatible;
- allow the harness to receive multiple planner proof run results;
- select the matching proof per observed handle and target fixture;
- keep default and mismatched-proof cleanup on the normal semantic path;
- render multiple attached proof views in the existing Cleanup Artifact Report;
- prove a full synthetic ADR-0003 cleanup can pass the existing cleanup
  primitive gate and planner cleanup bridge when every object has a matching
  bound proof.

## Non-Goals

- Do not claim live multi-object CuRobo proof generation.
- Do not reuse one proof for multiple cleanup objects.
- Do not relax object/target/tool binding requirements.
- Do not add another report implementation.

## Deliverables

- ADR-0035 and this source plan.
- `.planning/milestones/v1.98-phases/44-molmospaces-planner-proof-bundle-cleanup/44-01-planner-proof-bundle-cleanup-PLAN.md`.
- Proof bundle helper/schema and validators.
- Harness wiring for multiple planner proof run results.
- Report and checker support for proof bundles.
- Tests for full proof coverage, partial coverage fallback, and visual report
  rendering.

## Verification Plan

- Passed unit tests for proof bundle attachment and validation.
- Passed focused harness/checker tests proving full synthetic cleanup gate
  readiness when every cleaned object has a matching bound proof.
- Existing single-proof and mismatched-proof tests continue to prove fallback
  behavior does not overclaim.
- Report tests show multiple proof views in the shared report underlay.
- Ruff check/format passed on changed Python/tests.
- Existing real visual artifact checker remains valid.

## Completion Notes

The new proof bundle is an artifact coverage mechanism, not a planner proof
generator. It lets a cleanup run attach and select one already-strict bound
proof per observed handle/target. The bridge becomes ready only when the
cleanup primitive gate is fully planner-backed and the attached proof bundle is
strict target-runtime evidence.
