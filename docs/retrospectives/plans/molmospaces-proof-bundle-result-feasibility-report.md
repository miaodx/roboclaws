# MolmoSpaces Proof Bundle Result Feasibility Report

## Goal

Make executed proof-bundle runner reports show per-proof result evidence,
cleanup binding status, task-feasibility blockers, and planner view artifacts
in the same report that already shows commands and cleanup rerun artifacts.

## Scope

- Add a proof-result summary to proof-bundle runner manifests.
- Classify proof results into reviewable feasibility statuses.
- Render proof statuses, blockers, cleanup binding promotion, exact task config,
  proof report links, and planner view images in `report.html`.
- Validate the new section in the proof-bundle runner checker.
- Keep strict per-proof validation separate; the bundle summary does not make a
  blocked proof planner-backed.

## Acceptance

- Dry-run manifests explicitly show that proofs have not run.
- Executed manifests summarize generated proof outputs when `run_result.json`
  exists.
- A blocked exact-scene proof with `HouseInvalidForTask` is classified as task
  feasibility blocked.
- Planner view image artifacts are rendered when present; probes that block
  before views are labeled as having no views recorded.
- Focused tests cover summary construction, report rendering, runner behavior,
  and checker validation.

## Out Of Scope

- Selecting alternate feasible cleanup objects or targets.
- Making `HouseInvalidForTask` pass.
- Treating bundle-level summary as strict planner-backed cleanup evidence.
