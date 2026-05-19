# MolmoSpaces Planner Proof Bundle Execute Rerun

**Status:** Completed in GSD Phase 53 on 2026-05-10 with explicit local blocker
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0042, ADR-0043, ADR-0044
**Workflow:** `hybrid-phase-pipeline`

## Problem

The proof-bundle path is now repeatable as a dry run and can record cleanup
rerun artifacts, but the actual local execution path is still an operator-only
command. That leaves the final planner-backed cleanup primitive claim easy to
miss or under-check.

## Decision

Add a named local-dev proof-bundle execution gate.

This phase should:

- add `harness::molmo-planner-proof-bundle-execute-rerun`;
- add `verify::molmo-planner-proof-bundle-execute-rerun`;
- keep the existing dry-run gate unchanged and cheap;
- checker-gate proof outputs, cleanup rerun outputs, final cleanup primitive
  readiness, and planner cleanup bridge readiness;
- add recipe-shape tests so future edits do not collapse the local execution
  gate back into the dry-run gate.

## Non-Goals

- Do not add this local GPU gate to default CI.
- Do not weaken the strict cleanup primitive or bridge checkers.
- Do not commit generated proof artifacts under `output/`.

## Deliverables

- ADR-0044 and this source plan.
- `.planning/milestones/v1.98-phases/53-molmospaces-planner-proof-bundle-execute-rerun/53-01-planner-proof-bundle-execute-rerun-PLAN.md`.
- Local-dev harness and verify recipes.
- Focused recipe-shape tests.
- Local execution attempt when runtime conditions permit.

## Verification Plan

- `uv run ruff check tests/test_verify_just_recipes.py`
- `uv run ruff format --check tests/test_verify_just_recipes.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_verify_just_recipes.py`
- `just harness::molmo-planner-proof-bundle-execute-rerun` on a local
  CUDA/MolmoSpaces workstation.

## Completion

Completed in Phase 53.

The local-dev execute-rerun gate now exists and stays separate from the cheap
dry-run proof-bundle runner gate. The local attempt executed five RBY1M/CuRobo
proofs successfully and the runner artifact passed with required proof outputs
and cleanup rerun outputs.

The final strict cleanup checker failed, correctly, because none of the proof
artifacts promoted cleanup primitive binding. Each proof executed a sampled
upstream task whose `pickup_obj_name` and `place_receptacle_name` differed from
the requested cleanup object/target aliases. The final cleanup rerun therefore
remained `api_semantic`, with cleanup primitive and bridge gates still
`blocked_capability`.
