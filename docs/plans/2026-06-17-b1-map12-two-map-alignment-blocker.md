---
plan_scope: b1-map12-two-map-alignment-blocker
status: First residual-backed robot-consumption proof passed; room/object semantic anchors remain later work
created: 2026-06-17
last_reviewed: 2026-06-18
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

Current execution status: the reviewed global transform exists and the first
Map12 -> B1 robot-consumption proof passes. The residual artifact at
`output/b1-map12/alignment/alignment_residuals.json` is `global_verified`.
`output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json`
applies two residual-backed Map12 navigation-memory points as B1 scene robot
poses and captures same-pose Isaac FPV/Chase evidence. Operator preview
promotion from that artifact succeeds under
`output/b1-map12/operator-preview-residual-overlay/`. Room/object projection
still needs separate semantic anchors and is not part of this proof.
`scripts/maps/build_b1_map12_semantic_projection.py` is the strict room-label
projection gate: with the current alignment-only manifest it must fail with
`accepted semantic anchors are required before projecting room labels`, and it
keeps object projection blocked instead of inferring object labels from room
anchors.

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

On-demand Map12 navigation point contract:

- Accepted input is either an existing public Map12 inspection waypoint id or an
  explicit `map_xy` plus optional yaw in the Map12/source-map frame.
- The request first runs a residual-backed coverage check. Coverage may be a
  verified global transform or an explicitly verified local area transform.
- A supported request emits a B1 scene robot pose packet with frame id, `x/y/z`,
  yaw, transform source, alignment artifact, input id or point, and coverage
  decision.
- An unsupported, uncovered, malformed, or unverified request emits a blocked
  artifact with the reason. It must not substitute another point, use the bbox
  seed, or publish fake camera proof.
- This contract is an internal runtime/artifact path for digital-twin preview.
  It does not imply planner-backed navigation, collision-free path planning,
  physical robot navigation, a new MCP tool, or a public `household-world`
  surface change.

Planning-loop scope clarification:

- This document is the current execution source for making the B1 / Map 12
  asset usable like a simulator scene for preview-grade robot pose application:
  `Map12 waypoint id or map_xy/yaw -> residual-backed coverage check -> B1 scene
  robot pose -> Isaac pose application -> same-pose FPV, Chase, and topdown
  evidence`.
- `docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md` remains the
  prerequisite evidence contract. It owns reviewed correspondences, real
  `navigation_area_id` / `asset_partition_id` semantics, residual thresholds,
  and readiness status. This plan consumes only a passing residual artifact from
  that contract.
- "Arbitrary Map12 point" means an operator-supplied waypoint id or `map_xy/yaw`
  inside verified global coverage or an explicitly verified local area. It does
  not mean every coordinate in the map, a planner-backed path, obstacle
  avoidance, manipulation readiness, physical robot support, or a public MCP
  navigation tool.
- Unsupported or unverified points must emit blocked artifacts with explicit
  reasons. They must not fall back to bbox seeds, nearest known points, synthetic
  manual-draft ids, scene-probe cameras, or stale cached previews.

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
anchor_role=alignment|semantic
evidence note
review_status=accepted
```

For the current seven corner/edge picks, use `anchor_role=alignment`. They are
geometry anchors only and do not need `asset_partition_id` /
`navigation_area_id`. Add separate `anchor_role=semantic` room-interior points
before projecting room names or object labels into Map12; those semantic points
must carry real `asset_partition_id` and `navigation_area_id` values.

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
   - Build a transform-aware B1 waypoint/pose request path that accepts either
     an existing Map12 public inspection waypoint or an on-demand Map12
     `map_xy/yaw` point.
   - Convert the request into a B1 scene robot pose only when it is inside
     verified global coverage or an explicitly verified local area.
   - Apply that robot pose in Isaac and capture same-pose FPV, Chase, topdown,
     map, and report/verify evidence.
   - Record the alignment artifact, selected transform type, input waypoint id
     or point, map-frame pose, B1 scene pose, coverage decision, and
     `robot_pose_applied` status.
   - Stop with a blocked artifact on unsupported point, failed pose
     application, missing camera evidence, or any attempt to use bbox/seed
     transforms.

   Current evidence: this step passes for the navigation-memory points
   `plastic_bottle_table_1` and `long_table` under
   `output/b1-map12/navigation-smoke/residual-overlay/`. A separate attempt
   using two accepted alignment-corner anchors generated valid B1 pose requests
   but remained blocked because both FPV captures had too little visual detail;
   those anchors are geometry evidence, not good smoke viewpoints.

8. Promote the runtime camera artifact into operator-console preview assets.
   - Reuse `scripts/operator_console/render_scene_previews.py
     --b1-camera-artifact ...`.
   - Publish `b1-map12-fpv.png` and `b1-map12-chase.png` only when both views
     come from the same accepted waypoint evidence row.
   - Preserve the current no-camera static preview behavior when no accepted
     runtime camera artifact exists.

   Current evidence: promotion succeeds from
   `output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json`.
   The generated preview metadata uses `waypoint_id=b1_aligned_long_table` for
   both FPV and Chase, references
   `output/b1-map12/alignment/alignment_residuals.json`, records
   `alignment_transform_source=reviewed_correspondence_fit`, and keeps
   `isaac_runtime_*` provenance.

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
- On-demand point requests record input waypoint id or `map_xy/yaw`, coverage
  decision, transform source/artifact, and output B1 scene pose.
- Unsupported or unverified points block loudly with an artifact instead of
  falling back to another transform, point, or camera source.
- Multiple verified Map12 points can be converted and applied as B1 scene poses;
  at least one same-pose FPV/Chase pair is required before preview promotion.
- The on-demand pose path does not lower navigation proof thresholds or imply
  planner-backed, collision-free, physical, MCP, or public-surface support.
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
- Project accepted room labels only after residuals pass and the promoted
  correspondence manifest contains accepted `anchor_role=semantic` anchors with
  real semantic ids. Keep object labels blocked until their own reviewed
  semantic anchors exist.
- Add an internal on-demand Map12 navigation point to B1 pose request artifact:
  `Map12 waypoint id or map_xy/yaw -> residual-backed coverage check -> B1 pose`.
- Make `run_b1_map12_navigation_smoke.py` or a narrow sibling script consume the
  residual-backed pose request artifact instead of bbox candidates when
  producing preview-grade waypoint evidence.
- Preserve at least two distinct waypoint or point evidence rows before claiming
  `robot_navigation_supported=true`; a single pose/camera proof is preview
  evidence only.
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
python scripts/maps/render_b1_scene_gaussian_topdown.py \
  --scene-xy-bounds=-22.7833251953125,-13.112351417541504,8.074257850646973,7.298900469562338 \
  --output-dir output/b1-map12/scene-gaussian-topdown \
  --capture

.venv-isaaclab/bin/python scripts/maps/render_b1_scene_topdown_diagnostic.py \
  --scene-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  --scene-topdown-render output/b1-map12/scene-gaussian-topdown/scene_gaussian_topdown.json \
  --output-dir output/b1-map12/scene-topdown-label-overlay

python scripts/maps/render_b1_map12_correspondence_review.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --scene-topdown-render output/b1-map12/scene-gaussian-topdown/scene_gaussian_topdown.json \
  --output-dir output/b1-map12/correspondence-review
# expected before review: manifest_needs_fix or review_pending, accepted_anchor_count=0
```

After accepted anchors exist, run:

```bash
python scripts/maps/check_robot_map12_consistency.py vendors/agibot_sdk/artifacts/maps/robot_map_12

python scripts/maps/render_b1_map12_correspondence_review.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --scene-topdown-render output/b1-map12/scene-gaussian-topdown/scene_gaussian_topdown.json \
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

python scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py \
  --alignment-artifact output/b1-map12/alignment/alignment_residuals.json \
  --points output/b1-map12/navigation-smoke/map12_points.json \
  --output output/b1-map12/navigation-smoke/waypoint_pose_requests.json

python scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py \
  --readiness-artifact output/b1-map12/readiness/readiness.aligned.json \
  --waypoint-pose-requests output/b1-map12/navigation-smoke/waypoint_pose_requests.json \
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

Preflight status: APPROVED on 2026-06-18 by user `LGTM`; refreshed after
agent-planning-loop scout review.

Task source: user prompt, this active plan, the 2026-06-17 reduce-entropy
packet, and the 2026-06-18 agent planning loop.

Canonical source: `docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`

Route: durable `$intuitive-flow`

Goal: Make B1 / Map 12 usable enough for MolmoSpaces-like digital-twin preview
and on-demand Map12 navigation point application by producing an honest two-map
alignment diagnostic/review path, fitting residual-backed Map12-to-B1
transforms, converting verified Map12 waypoint ids or `map_xy/yaw` requests into
B1 scene robot poses, applying those poses in Isaac, and promoting B1 robot-view
previews only from residual-backed Isaac runtime pose evidence.

Scope:

- P0: topdown diagnostic for `2rd_floor_seperated`; two-map anchor review/export;
  Z-up `x,y` correspondence/fitter/test contract; vendor Map12 loading.
- P1: residual integration into readiness/report paths; an internal on-demand
  Map12 navigation point to B1 pose request artifact; transform-aware B1
  waypoint/point robot-view capture; operator-console camera preview promotion
  with residual-backed provenance checks.
- P1 acceptance uses multiple point rows: at least two distinct verified Map12
  points should convert/apply as B1 pose evidence before claiming navigation
  support, while one same-pose FPV/Chase pair is the minimum preview-promotion
  proof.
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
- Required prerequisite:
  `docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md` owns
  human/operator accepted anchors, residual thresholds, and readiness status.
  This plan may not create runtime pose/camera proof from draft anchors, bbox
  seeds, or proposed-only review packets. Room/area label projection additionally
  needs accepted `anchor_role=semantic` anchors with real semantic ids.
- Avoid unless needed: broad `output/**`, historical retrospectives, and old
  B1 merged-bundle artifacts.

Acceptance:

- SUCCESS: residual-backed global or local B1 / Map 12 alignment exists, or the
  scene diagnostic honestly blocks alignment. If alignment passes, a reusable
  on-demand Map12 waypoint or `map_xy/yaw` to B1 scene pose conversion/apply
  contract exists, verified and unsupported point rows are both auditable, at
  least two distinct verified point rows are exercised before navigation support
  is claimed, and at least one same-pose FPV/Chase preview pair is promoted from
  residual-backed Isaac runtime robot pose evidence.
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
- Deterministic artifact tests must include verified point conversion rows,
  unsupported/unverified point blocked artifacts, and no fallback from failed
  point conversion to bbox, nearest-point, scene-probe, or stale camera preview
  evidence.
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

- a reusable on-demand Map12 waypoint or `map_xy/yaw` conversion/apply contract
  exists, at least two distinct verified points are handled as pose/evidence
  rows where possible, and at least one same-pose B1 FPV/Chase preview pair has
  been generated and promoted into the operator-console preview metadata; or
- the diagnostic proves the scene labels are not self-consistent enough to align.

Do not broaden into semantic-map authoring until this blocker is closed.

## Implementation Status

2026-06-18 planning-loop update:

- The agent planning loop concluded this 2026-06-17 plan owns the runtime
  application contract: residual-backed Map12 waypoint ids or on-demand
  `map_xy/yaw` points become B1 scene robot poses, Isaac pose applications, and
  same-pose visual evidence only inside verified coverage.
- `docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md` remains the
  prerequisite alignment/residual evidence source; this plan owns the newer
  Z-up `x,y` policy and runtime proof contract.
- Implementation is still blocked until accepted anchors/residuals exist and
  local Isaac evidence proves the pose/camera path. Unsupported points must
  produce blocked artifacts, not fallback output.
- P1 internal pose request contract is implemented:
  `scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py` writes
  `b1_map12_waypoint_pose_requests_v1` artifacts from on-demand Map12
  waypoint ids or `map_xy/yaw` points. Globally verified residual-backed
  alignment produces B1 pose rows with coverage decisions; unverified
  alignment, malformed points, or missing coverage produce blocked rows.
- Explicit local-area coverage is supported only when the point names a
  `navigation_area_id` that has a verified independent area transform in the
  residual artifact. Missing or unknown local area ids block loudly; no global
  fallback is inferred for area-only alignment.
- `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py` can consume the
  pose request artifact through `--waypoint-pose-requests`. A blocked request
  artifact blocks smoke capture, and missing/seed-derived readiness waypoints
  no longer act as a silent fallback.
- Navigation smoke now requires at least two distinct applied B1 scene poses
  before it can set `robot_navigation_supported=true`; duplicate-pose camera
  rows remain blocked even if two images exist.
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py` can include
  `waypoint_pose_requests.json`, showing ready and blocked conversion rows so
  coverage decisions are auditable even before Isaac robot-view capture passes.
- `scripts/maps/promote_b1_map12_semantic_review_packet.py` implements the
  strict reviewed-anchor promotion gate owned by the 2026-06-16 alignment plan.
  It writes the committed correspondence manifest only from human-accepted
  anchors with explicit `anchor_role`, rejects proposed-only rows, fewer than
  six accepted anchors, bbox/seed coordinate sources, and auto-accepted
  suggestions, and requires real ids only for accepted `anchor_role=semantic`
  anchors. Its `--check` mode validates the same gate without writing the
  committed asset, and write mode strips review-only suggestion metadata from
  promoted anchors.
- The same promotion gate now also rejects self-inconsistent review-packet
  metadata: top-level accepted/proposed counts must match actual anchor
  statuses, `accepted_manifest_mutated` must be false, and policy must keep
  `auto_accept=false` plus `review_required=true`.
- The semantic suggestion command now also emits
  `output/b1-map12/manual-draft-anchor-semantic-review.html`, a read-only table
  for the human/operator to review candidate ids before editing the JSON packet.
- `scripts/maps/check_b1_map12_semantic_review_packet_fit.py` can validate a
  human-edited packet and run the residual fitter against a promoted preview
  manifest under `output/` without writing the committed correspondence asset.

2026-06-17 update:

- P0 review/fitter safety is implemented for the pre-anchor state.
  `scripts/maps/render_b1_scene_gaussian_topdown.py` writes the required
  `scene_gaussian_topdown.json` contract and, with `--capture`, renders the B1
  rebuilt Gaussian scene `top2down.png` through the Isaac scene-camera path. It
  requires explicit scene XY bounds and records camera height/FOV plus
  ray-plane `scene_xyz` mapping; it does not infer bounds or fall back to label
  inventory.
- `scripts/maps/render_b1_scene_topdown_diagnostic.py --scene-topdown-render ...`
  can draw `2rd_floor_seperated` scene USD room/object labels and top-level
  object bounds onto a captured Gaussian topdown. The packet is explicitly
  `alignment_scope=scene_self_check_only` and
  `map_projection_status=not_projected_to_map12`; it is not accepted as a
  correspondence picker input or Map12 semantic projection.
- `scripts/maps/render_b1_map12_correspondence_review.py` now loads the vendor
  Map12 bundle directly from `nav2.yaml` / `occupancy.pgm`, requires the
  rendered Gaussian top-down packet through `--scene-topdown-render`, and
  rejects label-inventory diagnostics. The HTML picker uses a browser-ready
  `map12_source_map.png` generated into the review output directory while
  preserving the vendor `occupancy.pgm` as packet provenance. The exported
  draft manifest contains paired `map_xy` plus ray-plane `scene_xyz` candidates
  from the rendered top-down packet.
- The correspondence fitter, tests, and draft/capsule artifacts use the Z-up
  `x,y` scene projection policy and reject legacy Y-up `x,z` policy for
  accepted-anchor evidence.
- B1 static preview generation still publishes only `map` and `topdown` before
  residual-backed Isaac runtime camera evidence; FPV/Chase promotion remains
  guarded by same-waypoint, residual-backed, `robot_pose_applied` provenance.
- Operator-console B1 camera preview promotion now rejects generic
  `robot_view_steps` unless they include an explicit camera-control contract
  proving the FPV source is robot-mounted or a head-camera equivalent and not a
  scene-probe or bbox source. Dedicated B1 navigation-smoke waypoint evidence
  remains accepted because the smoke artifact already represents pose-driven
  runtime waypoint capture.
- The same preview promotion gate also rejects camera artifacts that omit the
  waypoint id or mix FPV/Chase files from different view labels, so promoted
  FPV and Chase metadata always describe one same-waypoint evidence row.
- `--skip-existing` for B1 previews now reuses camera preview metadata only
  when it still carries the matching camera artifact path, same waypoint id,
  residual alignment artifact, and `reviewed_correspondence_fit` transform
  source. Incomplete stale camera metadata is rewritten to static map/topdown
  preview and stale FPV/Chase files are removed.

Current gate:

- `assets/maps/b1-map12-scene-correspondences.json` now contains seven accepted
  `anchor_role=alignment` geometry anchors from
  `docs/status/active/b1-map12-alignment-accepted-review-packet.json`.
- `python scripts/maps/fit_b1_map12_scene_alignment.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/alignment`
  writes `global_alignment_status=verified`, `selected_transform_type=rigid_2d`,
  mean residual `0.352908 m`, p90 `0.491765 m`, and max `0.502064 m`.
- The internal pose-request artifact and report-audit path consume that
  residual artifact. The default navigation-smoke harness now passes with two
  residual-backed Map12 navigation-memory points and same-pose Isaac FPV/Chase
  evidence.
- `scripts/maps/compile_b1_map12_runtime_bundle.py` can now consume explicit
  verified alignment and navigation artifacts and write
  `digital_twin_capabilities.robot_consumption_proof` into `semantics.json`.
  With the accepted residual/navigation smoke artifacts, the compiled runtime
  bundle validates and reports `robot_navigation_supported=true`. The compiler
  does not auto-discover `output/` artifacts; callers must pass explicit paths,
  and missing, invalid, or mismatched artifacts fail loudly.
- The same compiler can now consume an explicit verified semantic projection
  artifact and write
  `digital_twin_capabilities.room_semantic_projection_proof` into
  `semantics.json`. This only promotes room semantics when the projection
  artifact itself was produced from accepted semantic anchors. The default route
  does not auto-discover semantic projection output, and object projection stays
  `blocked_until_object_semantic_anchors`.
- A compiled B1/Nav2 cleanup bundle can now be converted into the same
  `runtime_map_prior_snapshot_v1` contract used by sim map-build output via
  `runtime_prior_snapshot_from_nav2_cleanup_bundle(...)` or
  `scripts/maps/convert_nav2_cleanup_bundle.py`. This gives downstream robot
  consumers one canonical prior shape for online sim maps, Agibot
  `navigation_memory.json`, and compiled B1 digital-twin bundles.
- `python scripts/maps/build_b1_map12_semantic_projection.py --correspondences assets/maps/b1-map12-scene-correspondences.json --review-manifest assets/maps/b1-map12-alignment-review.json --output output/b1-map12/semantic-projection/semantic_projection.json`
  currently exits non-zero with `accepted semantic anchors are required before
  projecting room labels`. This is expected until human-accepted
  `anchor_role=semantic` room-interior anchors are promoted.

Next implementation slice:

- Human-review `docs/status/active/b1-map12-semantic-anchor-review-packet.json`.
  If selected room-interior points are valid, promote them through
  `scripts/maps/promote_b1_map12_semantic_review_packet.py`, then run the
  strict semantic projection script. Do not use the verification-only manifest,
  bbox seed, proposed-only packet, or current alignment-only manifest as room
  semantics.
- For product/open-task runs that need the robot-consumption proof inside the
  map bundle, pass explicit `b1_alignment_artifact=...` and
  `b1_navigation_artifact=...` overrides rather than relying on generated
  `output/` discovery.
- After the strict semantic projection artifact exists, product/open-task runs
  may also pass explicit `b1_semantic_projection_artifact=...` to carry verified
  room semantics in the runtime bundle. Do not pass proposed-only packets or
  current alignment-only manifests as room semantics.
- Export `runtime_map_prior_snapshot.json` from the compiled B1 runtime bundle
  when downstream cleanup/open-task consumers need the same map-prior contract
  as simulator map-build output.
- Add separate object-level semantic anchors later before projecting object
  labels.

Latest deterministic evidence:

```bash
ruff check scripts/maps/render_b1_scene_gaussian_topdown.py scripts/maps/render_b1_map12_correspondence_review.py scripts/maps/fit_b1_map12_scene_alignment.py scripts/isaac_lab_cleanup/check_b1_map12_readiness.py scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py scripts/operator_console/render_scene_previews.py tests/contract/maps/test_b1_scene_gaussian_topdown.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py
ruff format --check scripts/maps/render_b1_scene_gaussian_topdown.py scripts/maps/render_b1_map12_correspondence_review.py scripts/maps/fit_b1_map12_scene_alignment.py scripts/isaac_lab_cleanup/check_b1_map12_readiness.py scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py scripts/operator_console/render_scene_previews.py tests/contract/maps/test_b1_scene_gaussian_topdown.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_scene_gaussian_topdown.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py -q
ruff check scripts/maps/render_b1_scene_topdown_diagnostic.py tests/contract/maps/test_b1_scene_topdown_diagnostic.py
ruff format --check scripts/maps/render_b1_scene_topdown_diagnostic.py tests/contract/maps/test_b1_scene_topdown_diagnostic.py
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_scene_topdown_diagnostic.py -q
ruff check scripts/isaac_lab_cleanup/check_b1_map12_readiness.py scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py tests/contract/maps/test_b1_map12_verified_alignment.py
ruff format --check scripts/isaac_lab_cleanup/check_b1_map12_readiness.py scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py tests/contract/maps/test_b1_map12_verified_alignment.py
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_digital_twin_readiness.py tests/contract/maps/test_b1_map12_navigation_report.py tests/unit/operator_console/test_render_scene_previews.py -q
ruff check scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py tests/contract/maps/test_b1_map12_verified_alignment.py
ruff format --check scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py tests/contract/maps/test_b1_map12_verified_alignment.py
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py -q
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_digital_twin_readiness.py tests/contract/maps/test_b1_map12_navigation_report.py -q
ruff check scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py tests/contract/maps/test_b1_map12_navigation_report.py
ruff format --check scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py tests/contract/maps/test_b1_map12_navigation_report.py
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_navigation_report.py -q
ruff check scripts/operator_console/render_scene_previews.py tests/unit/operator_console/test_render_scene_previews.py
ruff format --check scripts/operator_console/render_scene_previews.py tests/unit/operator_console/test_render_scene_previews.py
./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console/test_render_scene_previews.py -q
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_navigation_report.py tests/unit/operator_console/test_render_scene_previews.py -q
.venv-isaaclab/bin/python scripts/maps/render_b1_scene_topdown_diagnostic.py --scene-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated --scene-topdown-render output/b1-map12/scene-gaussian-topdown-crop-z1p8/scene_gaussian_topdown.json --output-dir output/b1-map12/scene-topdown-label-overlay
python scripts/maps/render_b1_map12_correspondence_review.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --scene-topdown-render output/b1-map12/scene-gaussian-topdown/scene_gaussian_topdown.json --output-dir output/b1-map12/correspondence-review
python scripts/maps/fit_b1_map12_scene_alignment.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/alignment
python scripts/operator_console/render_scene_previews.py --world b1-map12 --output-dir output/b1-map12/static-preview-proof
```
