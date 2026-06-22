# Visual Grounding Results

Last updated: 2026-06-18

Current status: the active camera-labeling sidecar contract is detector-only
per ADR-0138. Hosted refiner and direct-producer routes are historical benchmark
evidence only and are not active camera labelers.

## Current Recommendation

Use `camera_labeler=grounding-dino` as the default camera labeler for
`evidence_lane=camera-grounded-labels`.

Recommended real sidecar configuration:

```bash
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base
VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25
VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20
```

Keep `world-public-labels` as the deterministic structured-label baseline for
CI and smoke work. Keep `yoloe`, `yolo-world`, and `omdet-turbo` as comparison
lanes until benchmark and cleanup evidence justify changing the default.

## Current Command Shapes

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
just agent::harness molmo-visual-grounding-benchmark pipeline=grounding-dino
```

## Evidence Policy

- Detector-only sidecar rows may be promoted into current run guidance.
- Hosted refiner/direct-producer rows stay historical unless a fresh plan
  reintroduces them for a bounded offline/on-demand labeling use case.
- Benchmark artifacts live under `output/visual-grounding-benchmark/` and
  should be summarized here only when they change the current default or a
  blocked/experimental lane.

## Source Docs

- [ADR-0138](../adr/0138-use-detector-only-visual-grounding-sidecar.md)
- [MolmoSpaces settings](molmospaces-settings.md)
