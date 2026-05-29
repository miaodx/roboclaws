# Project Status

Last updated: 2026-05-28

This is the human-facing dashboard for the repo. Keep it short: current state
and pointers only, not a changelog or execution ledger.

## Current Focus

Roboclaws is focused on the MolmoSpaces cleanup path: making household cleanup
artifacts visible, honest, and aligned with future real-robot backends.

The active follow-up is Isaac Lab backend support for MolmoSpaces cleanup,
running on the local GPU first rather than CI. The 2026-05-28 local pass loaded
`procthor-10k-val` scene `val_0` through Isaac Sim/Lab, indexed real
MolmoSpaces USD geometry prims from adjacent scene metadata, bound the selected
cleanup handles to USD prim paths, and passed one-object cleanup/report parity
with `primitive_provenance=isaac_semantic_pose`. A second local GPU pass on
`val_1` broadened scene-load/render/index/report coverage, but also showed that
cross-scene cleanup needed stricter semantics because public `mug_01` rebound to
a `sponge` USD prim by semantic fallback. The current slice blocks that loose
generic-category object fallback, generates cleanup scenarios from the loaded
scene index when default selected handles do not bind, and now passes exact
one-object cleanup/report parity on `val_1` by preferring public USD
scene-index fixture candidates over stale map-bundle fixture ids. The
segmentation opt-in path is now wired so a segmentation-required cleanup probe
actually requests Isaac segmentation tensors. The latest local GPU data-type
probes show `semantic_segmentation` and `instance_segmentation_fast` return
tensors, but only full-frame `BACKGROUND` candidates with zero selected USD
matches; `instance_id_segmentation_fast` still aborts inside Isaac/Omniverse
with a CUDA illegal-address coredump before worker state is written, now
captured in the runtime-smoke artifact. A follow-up label-application probe
successfully applies scene-index semantic labels to 29 USD prims before camera
capture, but semantic and instance-fast annotators still return only
`BACKGROUND`. A targeted local USD reference install now maps missing
MolmoSpaces USD object references from the `val_1` state artifact to 22
`objects/thor` R2 archives and installs them under
`output/isaaclab/molmospaces-usd/objects/thor`; the follow-up probe confirms
selected Bowl/Sink geometry is renderable with no missing referenced assets. A
root-cause probe now shows the raw MolmoSpaces composed scene is the failing
layer for Isaac semantic AOV: flattening `val_1`, authoring semantic labels on
637 final renderable Gprims including 408 Mesh prims, and requesting
`semantic_filter=["usd_prim_path"]` produces selected Bowl/Sink segmentation
matches and passes the strict Isaac runtime-smoke segmentation gate. The same
prepared-scene path now passes strict cleanup smoke at
`output/isaaclab/cleanup-smoke/0529_val1_flattened_usdprimpath_cleanup_clean/` with
real Isaac runtime diagnostics, local scene USD loading, selected USD bindings,
robot-view/snapshot provenance, `candidate_bbox_count=24`,
`selected_usd_prim_match_count=2`, and `primitive_provenance=isaac_semantic_pose`.
Default segmentation-off cleanup still passes on `val_1`. The
visual-grounding GPU sidecar benchmark remains a separate active confidence
layer; Grounding DINO base-recall is still the current default real
`camera-labels` pipeline until a broader corpus changes that ranking.

The Agibot SDK runner backend boundary for `real_robot_cleanup_v1` remains a
separate confidence layer. Roboclaws keeps the cleanup-shaped public contract and
calls the SDK runner through a subprocess CLI; the SDK runner owns Agibot GDK
map, observation, navigation, and per-stage evidence.

For Agibot/MolmoSpaces confidence-layer distinctions, read root `CONTEXT.md`
before planning or implementation. Keep Agibot map visual dry runs, SDK dry
runs, MolmoSpaces semantic cleanup on Agibot-shaped map data, and MolmoSpaces
Agibot contract rehearsal separate.

## Next Action

Broaden prepared flattened-USD segmentation cleanup coverage beyond the current
`val_1` local GPU proof, and broaden scene-index cleanup coverage beyond the
current `val_0`/`val_1` local GPU proofs. Keep Grounding DINO base-recall as
the visual-grounding default until the broader corpus changes that ranking.

## Current Blocker

No hosted-CI Codex blocker remains. Hosted CI must not launch Codex, run Codex
provider smoke, or block on Codex acceptance artifacts. Local work-network runs
support Codex through repo-local `.env` mify or codex-env routes and support
Claude Code through repo-local `.env` MiMo/Kimi routes; local non-work-network
runs also support OpenClaw. The current Isaac blocker has narrowed from
"segmentation unavailable" to integration of the proven prep path:
MolmoSpaces USD RGB/robot-view and exact scene-index cleanup evidence passes
for `val_0` and `val_1`; raw composed `val_1` semantic AOV still collapses or
fails selected matching, but a flattened semantic USD with labels on final
renderable descendants and `semantic_filter=["usd_prim_path"]` produces usable
selected-prim segmentation evidence and passes strict cleanup smoke when used as
an explicit prepared scene. Missing selected USD object references are no longer
the active blocker for `val_1`; selected Bowl/Sink geometry now
resolves as renderable.

## Human Review Surface

- Project orientation: `README.md`
- Architecture and contracts: `ARCHITECTURE.md`
- Skill-first MCP design: `docs/human/mcp-skills-and-semantic-profiles.md`
- Active Nav2 cleanup status:
  `docs/status/active/real-robot-nav2-cleanup-pilot.md`
- Active Agibot plan/evidence: `docs/plans/agibot-g2-cleanup-support-pilot.md`
- Agibot robot_map_9 dry-run boundary:
  `docs/plans/agibot-robot-map-9-dry-run-rehearsal.md`
- Agibot robot_map_9 semantic actions:
  `docs/plans/agibot-robot-map-9-semantic-actions-rehearsal.md`
- MolmoSpaces Agibot contract rehearsal:
  `docs/plans/molmospaces-agibot-contract-rehearsal.md`
- Auto semantic map build:
  `docs/plans/auto-semantic-map-build.md`
- Isaac Lab MolmoSpaces backend support:
  `docs/plans/isaac-lab-molmospaces-backend-support.md`
- Visual grounding GPU sidecar benchmark:
  `docs/plans/visual-grounding-gpu-sidecar-benchmark.md`
- Current status: `STATUS.md`
- Human docs: `docs/human/`

## AI-Agent Sources

- GSD execution state: `.planning/STATE.md`
- Current phase details: follow the latest phase link in `.planning/STATE.md`
- Pre-GSD plans: `docs/plans/`
- Durable decisions: `docs/adr/`
- Shipped history: `docs/retrospectives/`
- Concurrent standalone work: `docs/status/active/`

## Recently Shipped

See `.planning/STATE.md` for the latest phase summary and
`docs/retrospectives/` for shipped history. Keep only current orientation here.

## Parked

- Queued implementation tasks live in `TODOS.md`.
- Scratch ideas and future directions live in `THOUGHTS.md`.
- GitHub issues track externally visible work for `MiaoDX/roboclaws`.

## Concurrent Work

Standalone task/refactor notes live in `docs/status/active/`.
Do not edit `STATUS.md` for routine per-task progress. Update this file only
when the repo-level current focus, latest phase, next action, or blocker
changes.

## Workflow Contract

Use the hybrid pipeline as the normal path:

`idea -> docs/plans/<slug>.md -> review/autoplan -> GSD plan/execute -> verify -> retrospective`

Rules:

- `STATUS.md` answers "what is happening now?"
- `docs/plans/` owns pre-GSD plans.
- `.planning/` is GSD-owned execution detail.
- `docs/human/` is the human-readable doc set; other `docs/` folders are
  primarily AI-agent evidence, generated planning detail, or history.
- `docs/adr/` records durable decisions, not progress.
- Root `PLAN.md` is a legacy compatibility pointer, not an active plan.
- `TODOS.md` and `THOUGHTS.md` are parked-work surfaces, not current status.
- Parallel terminals should use one task-owned file under `docs/status/active/`.
- At GSD closeout/verify/ship, update this file if current focus, latest phase,
  next action, or blocker changed.
