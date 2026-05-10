# MolmoSpaces Broader Bound Proof Cleanup Rerun

**Status:** Completed for Phase 91 on 2026-05-10
**Parent plan:** `docs/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0082-rerun-cleanup-with-broader-bound-proof.md`

## Goal

Rerun the broader ADR-0003 cleanup artifact with the Phase90 passing
`proof_008` bound planner proof and verify whether the matching cleanup object
uses planner-backed primitive evidence while unmatched objects remain honest.

## Problem

Phase90 proved one broader selected candidate, but proof execution alone does
not show the final cleanup artifact can consume the bound proof. The next slice
must feed the existing `proof_008` run result into the cleanup harness without
re-executing the proof bundle, then inspect the final cleanup report and
machine evidence.

## Scope

- Use the Phase89 broader cleanup source parameters.
- Attach the Phase90 `proof_008` planner-backed run result.
- Opt in to planner proof cleanup primitive execution.
- Record robot views and planner proof views in the cleanup report.
- Add a checker gate for the partial-bound state:
  `observed_008` / `stand_6bc09b7e2670723819cfaf03855284c1_1_0_3` must be
  planner-backed, while at least one unmatched object remains `api_semantic`.

## Non-Goals

- Do not re-execute the eight Phase90 proof probes.
- Do not claim full planner-backed cleanup readiness from one bound object.
- Do not expose private planner aliases to Agent View.
- Do not commit generated `output/` artifacts.

## Acceptance Criteria

- Cleanup rerun output exists under
  `output/debug-phase91-broader-bound-proof-cleanup-rerun/`.
- The cleanup report includes the shared visual core, robot view timeline,
  attached planner proof views, cleanup primitive gate, and planner cleanup
  bridge.
- The checker requires the bound object/target pair to be strict
  planner-backed.
- The checker requires mixed primitive evidence so unmatched objects remain
  `api_semantic` and the global cleanup bridge remains blocked.
- Focused tests cover the new checker gate.

## Result

Implemented.

The cleanup rerun at
`output/debug-phase91-broader-bound-proof-cleanup-rerun/` consumed the existing
Phase90 `proof_008` run result without re-executing the proof bundle.

The final cleanup artifact succeeded as an ADR-0003 cleanup run and produced
the required visual report surface:

- shared visual core and semantic `nav, pick, nav, open?, place` subphases;
- 44 robot timeline steps;
- 176 robot-view images;
- attached planner proof initial/final images in `planner_proof/`;
- cleanup primitive gate;
- planner cleanup bridge.

`observed_008` to
`stand_6bc09b7e2670723819cfaf03855284c1_1_0_3` is strict planner-backed for
`nav`, `pick`, `nav`, and `place`. The global primitive evidence remains mixed:
4 planner-backed subphases and 38 `api_semantic` subphases. That keeps the
overall cleanup primitive gate and planner cleanup bridge at
`blocked_capability`, which is the correct result until all cleanup objects
have matching proof.

Verification:

- Preflight dependency install passed.
- AI2-THOR import passed.
- The cleanup rerun completed with `cleanup_status=success`.
- The strengthened cleanup checker passed with required robot views, planner
  proof attachment, bound object evidence, mixed primitive evidence, and
  blocked bridge acceptance.
- Focused checker lint, format, and pytest coverage passed.
