---
plan_scope: b1-map12-two-map-alignment-blocker
status: Active
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

The missing piece is the transform from the B1 scene/Gaussian frame into that
Map12 frame. Without this, scene labels and object labels are useful evidence,
but they cannot safely become robot navigation labels or object locations.

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

Diagnostic contract:

- Generate the best topdown possible from available assets.
- Add dependencies such as OpenUSD/`pxr`, `trimesh`, or `open3d` if they are the
  shortest reliable path to extract bounds or render useful diagnostics.
- If full geometry extraction is unavailable, still emit an honest inventory
  diagnostic with partition names, object label counts, asset files, and a clear
  `geometry_status` value. Do not pretend that label-only inventory is a
  geometric topdown.

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
- Make the review UI load vendor Map12 from `nav2.yaml` / `occupancy.pgm`
  directly.

P1:

- Run the fitter and wire its residual output into readiness/report previews.
- Project accepted room/object labels as candidate Map12 semantics only after
  residuals pass.

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

./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_b1_map12_verified_alignment.py \
  tests/contract/maps/test_b1_map12_label_tool.py \
  tests/contract/maps/test_robot_map12_consistency.py \
  -q
```

## Stop Condition

Stop after the first residual-backed transform is available or after the
diagnostic proves the scene labels are not self-consistent enough to align.
Do not broaden into semantic-map authoring until this blocker is closed.
