# Phase 29 Summary: Camera Model Policy Cleanup

Completed: 2026-05-09
Backfilled: 2026-05-11
Source plan: `29-01-camera-model-policy-cleanup-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Close the unblocked ADR-0003 camera-only model-policy gap by deriving cleanup
candidates from public raw FPV observations, then reusing the existing semantic
cleanup loop and shared visual report underlay.

## Completed Tasks

- Add ADR/source-plan documentation and update roadmap/state/context references.
- Add `camera_model_policy` mode and model-labelled candidate registration to `RealWorldCleanupContract`.
- Wire the deterministic demo policy to use camera-model candidates while preserving existing default and raw-FPV behavior.
- Render and checker-gate `Camera Model Policy` evidence through the shared cleanup report underlay.
- Add focused tests, generate a local artifact, and validate it with the new checker flag.

## Recorded Status

Completed 2026-05-09.

## Evidence

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- Focused pytest for the realworld contract, report, checker, and demo path.
- Local artifact:
  `output/molmo-realworld-camera-model-policy/report.html`.
- Real visual artifact:
  `output/molmo-realworld-camera-model-policy-visual/report.html`.

Evidence:

- `output/molmo-realworld-camera-model-policy/run_result.json` passed
  `--require-camera-model-policy --accept-blocked-planner-cleanup-primitives`.
- `output/molmo-realworld-camera-model-policy-visual/run_result.json` passed
  `--require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives`.
- The real visual artifact records `backend=molmospaces_subprocess`,
  `policy=camera_model_policy_baseline`, `restored=2/2`, 14 raw FPV
  observations, 14 camera-model policy events, 2 model-derived candidates, 2
  semantic cleanup objects, and 24 robot-view timeline steps.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
