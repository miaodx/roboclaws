# 29-01 Camera Model Policy Cleanup Plan

## Goal

Close the unblocked ADR-0003 camera-only model-policy gap by deriving cleanup
candidates from public raw FPV observations, then reusing the existing semantic
cleanup loop and shared visual report underlay.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [ ] Add `camera_model_policy` mode and model-labelled candidate registration
   to `RealWorldCleanupContract`.
3. [ ] Wire the deterministic demo policy to use camera-model candidates while
   preserving existing default and raw-FPV behavior.
4. [ ] Render and checker-gate `Camera Model Policy` evidence through the shared
   cleanup report underlay.
5. [ ] Add focused tests, generate a local artifact, and validate it with the
   new checker flag.

## Acceptance

- Camera-model policy mode records raw FPV observations and model-derived
  observed handles with explicit model provenance.
- The Agent View and trace contain no private generated mess, target count,
  acceptable destinations, `is_misplaced`, or target receptacles.
- The report shows the same shared sections as the ADR-0003 clean artifacts,
  including semantic substeps and the camera-model policy panel.
- Strict planner-backed cleanup primitive mode still rejects `api_semantic`
  cleanup moves.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- Focused pytest for the realworld contract, report, checker, and demo path.
- Local artifact:
  `output/molmo-realworld-camera-model-policy/report.html`.

## Risks

- The deterministic camera model could be mistaken for real VLM inference. The
  schema, report, and checker must label this provenance explicitly.
- If object handles are registered too eagerly, the mode becomes another
  structured-detection shortcut. Keep the candidate source tied to the current
  raw FPV observation and public waypoint.
