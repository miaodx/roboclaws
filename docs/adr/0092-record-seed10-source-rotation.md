# 0092. Record Seed 10 Source Rotation

Date: 2026-05-10

## Status

Accepted

## Context

Phase 92 proved the current broader source was exhausted after excluding one
covered planner-backed proof and nine grasp-infeasible requests. Phase 94 made
generated-mess source rotation possible by seeding MolmoSpaces object
selection, and Phase 95 executed the selected seed 9 commands but found only
more grasp-feasibility blockers.

The next architectural question is whether source rotation can keep generating
new exact-scene proof candidates without duplicating already covered or
known-blocked work.

## Decision

Record a seed 10 cleanup source artifact and derive a prior-aware proof
selection dry-run from it before executing any new RBY1M/CuRobo proof commands.

The selection must:

- consume prior proof memory from the covered/seeded proof manifests;
- exclude prior task-feasibility and covered-proof results;
- preserve the same shared proof-bundle report underlay;
- leave proof execution for a separate local-dev phase.

## Consequences

- Seed rotation now has concrete evidence beyond seed 9.
- The new source artifact provides 10 ready proof requests and 44 semantic robot
  view steps.
- Prior-aware selection picks 5 commands from seed 10 and excludes 5 requests as
  prior task-feasibility blocked.
- No new planner-backed cleanup coverage is claimed until those selected
  commands execute.

## Evidence

Implemented in Phase 101 on 2026-05-10.

Artifacts:

- `output/debug-phase101-seeded-source-candidate-seed10/run_result.json`
- `output/debug-phase101-seeded-source-candidate-seed10/report.html`
- `output/debug-phase101-seeded-source-candidate-selection-dry-run/proof_bundle_run_manifest.json`
- `output/debug-phase101-seeded-source-candidate-selection-dry-run/report.html`

Key results:

- source cleanup status: `success`
- generated mess count: 10
- robot view step count: 44
- proof requests: 10 ready of 10
- dry-run selected commands: 5
- selected request IDs: `proof_001`, `proof_003`, `proof_005`, `proof_008`, `proof_010`
- excluded requests: 5 `prior_task_feasibility_blocked`
- fallback generation: not required

Verification:

- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase101-seeded-source-candidate-selection-dry-run/proof_bundle_run_manifest.json --min-selected-requests 0`
