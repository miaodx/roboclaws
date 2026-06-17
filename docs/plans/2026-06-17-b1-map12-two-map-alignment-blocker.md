---
plan_scope: b1-map12-two-map-alignment-blocker
status: Partially implemented
created: 2026-06-17
last_reviewed: 2026-06-17
implementation_allowed: true
source:
  - user request to make two-map alignment the blocking issue for usable digital twin
  - user decision that Map12 agibot and navigation_memory are the fixed baseline
  - user decision to use 2rd_floor_seperated first for registration and B1_floor2_slow later for visual/open tasks
related_context:
  - STATUS.md
  - docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md
  - docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md
  - vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot
  - vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json
  - data/robot-data-lab/scene-engine/data/2rd_floor_seperated/
  - data/robot-data-lab/scene-engine/data/B1_floor2_slow/
  - assets/maps/b1-map12-scene-correspondences.json
---

# B1 / Map 12 Two-Map Alignment Blocker

## Problem

The B1 digital twin is not usable until the Gaussian/scene asset frame can be
aligned to the Map12 navigation frame. Map12 already has two mutually consistent
baseline inputs:

```text
vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot
vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json
```

The missing piece is the reviewed transform between the Map12 navigation frame
and the B1 scene/Gaussian frame. The first runtime direction is Map12 -> B1
scene, because digital-twin waypoint previews must start from Map12 waypoints
and place the robot in Isaac at the corresponding B1 scene pose. The inverse
direction is still needed before scene labels or object labels can become Map12
navigation labels or object locations.

## Decision

Use the existing labels. Do not manually relabel everything.

Use `2rd_floor_seperated/` first because it has split room/partition/object
labels. Use those labels as scene-frame evidence and anchor hints. After a
reviewed transform exists, project labels into Map12 as candidates.

Keep `B1_floor2_slow/` out of the first registration loop. It is more
photorealistic, but lacks the same split object labels. Bring it back after
`2rd_floor_seperated` establishes the Map12 alignment, mainly for visual/open
task background evidence.

Coordinate contract for the first pass:

- `2rd_floor_seperated` is Z-up.
- Scene topdown uses horizontal axes `x,y`.
- Accepted anchors are stored as `scene_xyz`, even when the UI captures a 2D
  topdown point. A 2D pick is exported as `[x, y, 0]` unless the review surface
  can provide a better Z value.
- Do not mix this with the old Y-up / `x,z` convention. Update fitter tests and
  correspondence fixtures before accepting anchors.
- The fitter, review packet, area/local fit path, leave-one-out diagnostics,
  and preview images must all use the manifest's `scene_projection_policy`.
  They must not silently fall back to the old `x,z` / Y-up policy for
  `2rd_floor_seperated` accepted-anchor evidence.

Diagnostic contract:

- Generate the best topdown possible from available assets.
- Add dependencies such as OpenUSD/`pxr`, `trimesh`, or `open3d` if they are the
  shortest reliable path to extract bounds or render useful diagnostics.
- If full geometry extraction is unavailable, still emit an honest inventory
  diagnostic with partition names, object label counts, asset files, and a clear
  `geometry_status` value. Do not pretend that label-only inventory is a
  geometric topdown.
- The exact diagnostic backend is intentionally flexible. Try the shortest
  reliable route first, such as OpenUSD bounds, OBJ/mesh bounds, `trimesh`, or a
  label-only inventory fallback. Change implementation details as evidence
  warrants, but preserve the diagnostic packet fields and failure honesty.

Preview parity contract:

- The digital-twin operator preview should match the sim preview semantics:
  `public waypoint -> robot pose -> FPV + Chase + topdown`.
- B1 may not publish FPV or Chase from scene-probe cameras, bbox-fit captures, or
  any other fallback that is not an Isaac runtime robot pose capture.
- The only acceptable B1 FPV/Chase preview source is a residual-backed Map12
  waypoint transformed into a B1 scene robot pose, applied in Isaac, and captured
  as the same-pose robot-mounted FPV plus report chase camera.
- Static B1 preview generation must continue to publish only `map` and `topdown`
  until such a runtime camera artifact exists.

## Minimal Path

1. Render a `2rd_floor_seperated` topdown diagnostic.
   - Show room partitions.
   - Show object labels or counts.
   - Show scene-frame bounds/centers when available. Add a dependency if that
     is the shortest reliable path.
   - Record whether geometry was rendered, extracted as bounds, or unavailable.
   - Do not project into Map12 yet.

2. Check scene self-consistency.
   - Room labels should match visible regions.
   - Object labels should sit in the expected partition.
   - Obvious conflicts such as mislabeled rooms, swapped axes, duplicated areas,
     or labels outside the floor plan block alignment.

3. Build a two-map alignment review surface.
   - Left: Map12 source map plus navigation memory.
   - Right: `2rd_floor_seperated` topdown diagnostic.
   - User picks explicit corresponding anchors, not freeform semantic labels.
   - The minimal acceptable surface may be a standalone HTML pick tool, a small
     served review tool, or a CLI-assisted review packet plus explicit JSON
     export, but it must be separate from the Map12 room-label editor and must
     produce paired `map_xy` + `scene_xyz` picks.

4. Store reviewed anchors in:

```text
assets/maps/b1-map12-scene-correspondences.json
```

Each accepted anchor needs explicit:

```text
map_xy
scene_xyz
asset_partition_id
navigation_area_id
evidence note
review_status=accepted
```

5. Reuse the existing fitter:

```bash
python scripts/maps/fit_b1_map12_scene_alignment.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/alignment
```

6. Promote only what residuals support.
   - Global pass: scene labels can become Map12 candidate semantics globally.
   - Local pass only: only those areas become usable.
   - Fail: keep all scene labels as evidence only.

7. Generate B1 waypoint robot-view evidence only after residuals pass.
   - Select at least one Map12 public inspection waypoint in a verified global
     area or an explicitly verified local area.
   - Convert the waypoint into a B1 scene robot pose using the residual-backed
     transform, never the bbox seed.
   - Apply that robot pose in Isaac and capture FPV, Chase, map, and verify
     images from the same pose.
   - Record the alignment artifact, selected transform type, waypoint id,
     map-frame pose, B1 scene pose, and `robot_pose_applied` status.
   - If the first capture path cannot apply the pose in Isaac, stop with a
     blocked artifact instead of publishing FPV/Chase previews.

8. Promote the runtime camera artifact into operator-console preview assets.
   - Reuse `scripts/operator_console/render_scene_previews.py
     --b1-camera-artifact ...`.
   - Publish `b1-map12-fpv.png` and `b1-map12-chase.png` only when both views
     come from the same accepted waypoint evidence row.
   - Preserve the current no-camera static preview behavior when no accepted
     runtime camera artifact exists.

## Acceptance Criteria

- A topdown diagnostic exists for `2rd_floor_seperated`.
- The diagnostic lists all scene partitions and high-signal object labels.
- The diagnostic records `up_axis=z`, `horizontal_axes=[x,y]`, and
  `geometry_status`.
- At least six accepted anchors exist across at least three scene partitions or
  navigation areas.
- Accepted anchors use `scene_xyz`; UI-only 2D picks are normalized to
  `scene_xyz=[x,y,0]`.
- The residual artifact reports rigid/similarity candidates, residual metrics,
  and pass/fail status.
- No code path treats empty or seed-derived correspondences as verified.
- The label tool or alignment tool never projects Gaussian/scene objects into
  Map12 without a residual-backed transform.
- Before a residual-backed robot-view artifact exists, `b1-map12-preview.json`
  contains no `views.fpv` or `views.chase`, and the corresponding static preview
  files are absent.
- After residual-backed waypoint capture, B1 FPV and Chase preview metadata share
  the same `waypoint_id`, reference the same alignment artifact or transform
  source, and use `isaac_runtime_*` provenance.
- B1 FPV is a robot-mounted/head-camera-equivalent Isaac runtime view, not a
  scene-probe camera. Chase is report evidence from the same applied robot pose,
  not agent-facing policy input.
- Preview promotion rejects bbox-fit, scene-probe, missing-pose, mixed-waypoint,
  blank, or low-detail camera artifacts.
- Preview promotion requires residual-backed alignment provenance in the camera
  artifact before stamping `isaac_runtime_*` metadata. Image quality alone is
  not enough.

## Non-Goals

- Do not make a fused Gaussian semantic map artifact.
- Do not use `B1_floor2_slow` for first-pass registration.
- Do not use affine transform as production truth. Affine is diagnostic only.
- Do not claim object/receptacle USD bindings or manipulation readiness.
- Do not change public `household-world` command grammar or MCP tools.

## Implementation Slice

P0:

- Add a small topdown diagnostic generator for `2rd_floor_seperated`.
- Use a separate minimal alignment tool for two-map anchor picking. Do not hide
  alignment inside the Map12 room-label editor.
- Export accepted anchors to the existing correspondence schema.
- Make the correspondence schema/fitter/tests agree on Z-up, `x,y` topdown, and
  `scene_xyz` anchor storage.
- Make all fitter/report branches consume the manifest projection policy,
  including independent area transforms, inherited area residuals, alignment
  previews, and leave-one-out diagnostics.
- Make the review UI load vendor Map12 from `nav2.yaml` / `occupancy.pgm`
  directly.

P1:

- Run the fitter and wire its residual output into readiness/report previews.
- Project accepted room/object labels as candidate Map12 semantics only after
  residuals pass.
- Add or update a transform-aware B1 waypoint robot-view capture path:
  `Map12 waypoint -> residual-backed B1 pose -> Isaac robot views`.
- Make `run_b1_map12_navigation_smoke.py` or a narrow sibling script consume the
  reviewed alignment artifact instead of the known-poor bbox candidate when
  producing preview-grade waypoint evidence.
- Promote the accepted runtime camera artifact into operator-console static
  previews with `--b1-camera-artifact`, preserving no-camera static previews as
  the default before runtime evidence exists.
- Add tests that reject B1 FPV/Chase preview metadata unless both views are
  same-waypoint, same-pose, residual-backed `isaac_runtime_*` artifacts.
- Add tests that reject camera artifacts without an alignment artifact or
  transform source, without applied B1 scene robot pose metadata, or derived
  from bbox-fit / scene-probe sources.

P2:

- Register `B1_floor2_slow` to the same frame for photorealistic visual/open
  tasks.

## Verification

Before anchors exist, expected status is blocked, not green:

```bash
python scripts/maps/render_b1_map12_correspondence_review.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/correspondence-review
# expected before review: manifest_needs_fix or review_pending, accepted_anchor_count=0
```

After accepted anchors exist, run:

```bash
python scripts/maps/check_robot_map12_consistency.py vendors/agibot_sdk/artifacts/maps/robot_map_12

python scripts/maps/render_b1_map12_correspondence_review.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/correspondence-review

python scripts/maps/fit_b1_map12_scene_alignment.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/alignment

# exact command name may change during implementation; the invariant is that
# preview-grade waypoint evidence consumes residual-backed alignment, not the bbox seed
python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py \
  --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  --alignment-artifact output/b1-map12/alignment/alignment_residuals.json \
  --output output/b1-map12/readiness/readiness.aligned.json

python scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py \
  --readiness-artifact output/b1-map12/readiness/readiness.aligned.json \
  --output-dir output/b1-map12/navigation-smoke \
  --accept-nvidia-eula

python scripts/operator_console/render_scene_previews.py \
  --world b1-map12 \
  --b1-camera-artifact output/b1-map12/navigation-smoke/navigation_smoke.json

./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_b1_map12_verified_alignment.py \
  tests/contract/maps/test_b1_map12_label_tool.py \
  tests/contract/maps/test_robot_map12_consistency.py \
  tests/unit/operator_console/test_render_scene_previews.py \
  tests/unit/operator_console/test_static_assets.py \
  -q
```

## Preflight Contract

Preflight status: DRAFT

Task source: user prompt plus this active plan and the 2026-06-17 reduce-entropy
packet.

Canonical source: `docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`

Route: durable `$intuitive-flow`

Goal: Make B1 / Map 12 usable enough for digital-twin preview by producing an
honest two-map alignment diagnostic/review path, fitting residual-backed
Map12-to-B1 transforms, and promoting B1 robot-view previews only from
residual-backed Isaac runtime pose evidence.

Scope:

- P0: topdown diagnostic for `2rd_floor_seperated`; two-map anchor review/export;
  Z-up `x,y` correspondence/fitter/test contract; vendor Map12 loading.
- P1: residual integration into readiness/report paths; transform-aware B1
  waypoint robot-view capture; operator-console camera preview promotion with
  residual-backed provenance checks.
- P2 only after P0/P1 pass: `B1_floor2_slow` visual registration for later
  photorealistic/open-task work.

Non-goals: fused Gaussian semantic map, `B1_floor2_slow` first-pass
registration, affine production truth, object/receptacle USD binding,
manipulation readiness, public `household-world` command or MCP changes.

Entity budget:

- Reuse: `assets/maps/b1-map12-scene-correspondences.json`,
  `scripts/maps/fit_b1_map12_scene_alignment.py`,
  `scripts/maps/render_b1_map12_correspondence_review.py`,
  `scripts/isaac_lab_cleanup/check_b1_map12_readiness.py`,
  `scripts/operator_console/render_scene_previews.py`.
- Remove/merge: old `x,z` / Y-up assumptions from current B1 / Map 12
  correspondence fixtures and fitter branches for `2rd_floor_seperated`.
- New: a small scene topdown diagnostic artifact and the minimal anchor-picking
  surface/export path, because existing tools only render manifest status or
  edit Map12 label geometry.
- Expansion triggers: adding a new public command grammar, new MCP tool,
  fused semantic map artifact, manipulation support, or treating
  `B1_floor2_slow` as first-pass registration requires re-approval.

Context:

- Must-read: this plan, `STATUS.md`, `ARCHITECTURE.md`,
  `docs/human/domain.md`, `docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md`,
  `assets/maps/b1-map12-scene-correspondences.json`,
  `vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot`,
  `vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json`,
  `data/robot-data-lab/scene-engine/data/2rd_floor_seperated/`.
- Useful: `docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md`
  for historical context only; it contains older `x,z` / Y-up examples that
  must not override this plan.
- Avoid unless needed: broad `output/**`, historical retrospectives, and old
  B1 merged-bundle artifacts.

Acceptance:

- SUCCESS: residual-backed global or local B1 / Map 12 alignment exists, or the
  scene diagnostic honestly blocks alignment; if alignment passes, at least one
  same-waypoint FPV/Chase preview pair is promoted from residual-backed Isaac
  runtime robot pose evidence.
- BLOCKED_NEEDS_DECISION: none expected; implementation may try different
  diagnostic and review-tool approaches as long as the invariants above hold.
- BLOCKED_NEEDS_LOCAL_VALIDATION: Isaac runtime waypoint capture and camera
  proof require local Isaac/GPU/EULA availability.
- INTERMEDIATE_ONLY: acceptable only if P0 diagnostic/review/fitter gates pass
  but Isaac camera capture remains unavailable; mark B1 preview camera proof as
  blocked, not complete.
- No regressions: empty/seed correspondences stay blocked, bbox seed never
  verifies alignment, static B1 preview omits FPV/Chase before accepted runtime
  camera evidence, and existing Map12 consistency gates still pass.

Verification:

- Deterministic: run the focused pytest command in this plan plus any new
  tests for Z-up projection, review/export, residual gating, and preview
  provenance rejection.
- Integration: run the Map12 consistency, correspondence review, fitter, and
  readiness commands listed above.
- Product-run: run `scripts/operator_console/render_scene_previews.py --world
  b1-map12` before camera evidence and again with `--b1-camera-artifact` after
  accepted runtime evidence.
- Local-live-manual: run the Isaac waypoint capture/navigation smoke on a host
  with the required Isaac runtime and review the generated topdown/camera
  artifacts for nonblank, same-pose evidence.
- Optional: compare alternate diagnostic backends when geometry extraction is
  poor; keep the simplest one that produces honest review evidence.

Execution: main session supervises the plan, owns final complete/blocked
judgment, and updates this plan if implementation evidence changes details.
Worker: optional, only for isolated read-only scouting of scene diagnostic
backend choices or local artifact inspection.

To execute: `/goal execute docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md with intuitive-flow`

Approval: `LGTM`, `approve`, or `go ahead` approves this preflight; requested
edits revise this section before execution.

## Stop Condition

Stop after either:

- the first residual-backed transform is available and at least one
  same-waypoint B1 FPV/Chase preview pair has been generated and promoted into
  the operator-console preview metadata; or
- the diagnostic proves the scene labels are not self-consistent enough to align.

Do not broaden into semantic-map authoring until this blocker is closed.

## Implementation Status

2026-06-17 partial implementation:

- P0 diagnostic/review/fitter safety is implemented for the pre-anchor state.
  `scripts/maps/render_b1_scene_topdown_diagnostic.py` emits an honest
  `2rd_floor_seperated` diagnostic with `up_axis=z`,
  `horizontal_axes=["x","y"]`, `geometry_status=label_inventory_only`, six
  partitions, and high-signal label inventory.
- `scripts/maps/render_b1_map12_correspondence_review.py` now loads the vendor
  Map12 bundle directly from `nav2.yaml` / `occupancy.pgm`, loads the scene
  topdown diagnostic, and renders a separate two-map picker/export surface. The
  HTML picker uses a browser-ready `map12_source_map.png` generated into the
  review output directory while preserving the vendor `occupancy.pgm` as packet
  provenance. The exported draft manifest contains paired `map_xy` plus
  `scene_xyz` picks and labels label-inventory scene picks as non-metric review
  candidates.
- The correspondence fitter, tests, and draft/capsule artifacts use the Z-up
  `x,y` scene projection policy and reject legacy Y-up `x,z` policy for
  accepted-anchor evidence.
- B1 static preview generation still publishes only `map` and `topdown` before
  residual-backed Isaac runtime camera evidence; FPV/Chase promotion remains
  guarded by same-waypoint, residual-backed, `robot_pose_applied` provenance.

Current gate:

- `assets/maps/b1-map12-scene-correspondences.json` still has zero accepted
  anchors. This is the correct blocked state until a human/operator reviews at
  least six anchors across at least three areas/partitions.
- The residual-backed transform, Isaac waypoint camera proof, and FPV/Chase
  preview promotion remain unimplemented/unverified until reviewed anchors and
  local Isaac runtime evidence exist.

Latest deterministic evidence:

```bash
ruff check scripts/maps/render_b1_scene_topdown_diagnostic.py scripts/maps/render_b1_map12_correspondence_review.py scripts/maps/fit_b1_map12_scene_alignment.py scripts/isaac_lab_cleanup/check_b1_map12_readiness.py scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py scripts/operator_console/render_scene_previews.py tests/contract/maps/test_b1_scene_topdown_diagnostic.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py
ruff format --check scripts/maps/render_b1_scene_topdown_diagnostic.py scripts/maps/render_b1_map12_correspondence_review.py scripts/maps/fit_b1_map12_scene_alignment.py scripts/isaac_lab_cleanup/check_b1_map12_readiness.py scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py scripts/operator_console/render_scene_previews.py tests/contract/maps/test_b1_scene_topdown_diagnostic.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_scene_topdown_diagnostic.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py -q
python scripts/maps/render_b1_map12_correspondence_review.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --scene-diagnostic output/b1-map12/scene-topdown-diagnostic/scene_topdown_diagnostic.json --output-dir output/b1-map12/correspondence-review
python scripts/maps/fit_b1_map12_scene_alignment.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/alignment
python scripts/operator_console/render_scene_previews.py --world b1-map12 --output-dir output/b1-map12/static-preview-proof
```
