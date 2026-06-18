---
plan_scope: b1-map12-two-map-alignment-blocker
status: Active P0-only plan; geometry/navigation proof completed, robot-facing consumer exposure and B1_floor2_slow visual-route selection remain
created: 2026-06-17
last_reviewed: 2026-06-18
implementation_allowed: true
source:
  - user request to make two-map alignment the blocking issue for usable digital twin
  - user decision that Map12 agibot and navigation_memory are the fixed baseline
  - user decision to use 2rd_floor_seperated first for registration
  - user decision on 2026-06-18 to evaluate B1_floor2_slow in P0 as the preferred visual/render route when verified
related_context:
  - STATUS.md
  - docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md
  - docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md
  - docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md
  - vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot
  - vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json
  - data/robot-data-lab/scene-engine/data/2rd_floor_seperated/
  - data/robot-data-lab/scene-engine/data/B1_floor2_slow/
  - assets/maps/b1-map12-scene-correspondences.json
---

# B1 / Map 12 Two-Map Alignment Blocker

## Problem

The B1 digital twin is only partially usable as a robot-consumable asset. The
Gaussian/scene asset frame is now aligned to the Map12 navigation frame, and
preview-grade residual-backed robot pose application has passed. The remaining
P0 problem is making that verified B1 map context reach robot-facing consumers
in the same strict shape as simulator Runtime Map Prior input, and selecting an
honest visual/render scene route for Gaussian observation evidence. Unreviewed
room/object semantics stay blocked and are tracked separately in
`docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md`.

Map12 already has two mutually consistent baseline inputs:

```text
vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot
vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json
```

Completed execution status: the reviewed global transform exists and the first
Map12 -> B1 robot-consumption proof passes. The residual artifact at
`output/b1-map12/alignment/alignment_residuals.json` is `global_verified`.
`output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json`
applies two residual-backed Map12 navigation-memory points as B1 scene robot
poses and captures same-pose Isaac FPV/Chase evidence. Operator preview
promotion from that artifact succeeds under
`output/b1-map12/operator-preview-residual-overlay/`.

Remaining P0 execution status: compiled B1 bundles expose
`digital_twin_capabilities` in `semantics.json`,
`runtime_map_prior_snapshot.json`, `runtime_map_prior_targets.json`, and
`b1_robot_consumption_manifest.json`, but the agent-visible MCP/runtime map
consumer path still needs a focused proof that the robot/agent sees
`robot_navigation_supported=true` plus blocked room/object/manipulation status
from the explicitly supplied prior. P0 should also evaluate whether
`B1_floor2_slow/` can be registered to the same Map12 frame as a
photorealistic visual/render route. If both `2rd_floor_seperated/` and
`B1_floor2_slow/` are verified for the required same-pose render evidence,
prefer `B1_floor2_slow/` for navigation/open-task visual rendering by default.
If it is missing, malformed, or unverified, publish an explicit blocked status;
do not silently fall back while claiming it is selected.

Room/object projection still needs separate semantic anchors and is not part of
P0. `scripts/maps/build_b1_map12_semantic_projection.py` must continue to fail
with `accepted semantic anchors are required before projecting room labels` for
the current alignment-only manifest, and object projection stays blocked instead
of inferring object labels from room anchors.

## Confirmed Target

The target is not just static alignment. The B1 / Map12 digital twin should
behave like a simulator scene from the robot/agent point of view:

- **Navigation layer**: a robot can use Map12 map context, choose a public
  Map12 waypoint or explicit `map_xy/yaw`, convert it through the verified
  alignment, and move/apply the corresponding B1 scene pose on demand.
- **Render/observation layer**: after applying that pose, the runtime can render
  Gaussian/digital-twin views such as FPV, Chase, topdown, and any future
  task-required camera view so open-ended tasks can inspect the asset from the
  robot's current pose. P0 should try `B1_floor2_slow/` as the preferred
  photorealistic render scene once it is registered to the verified Map12 frame;
  `2rd_floor_seperated/` remains the registration/semantic-label source unless
  a later plan proves otherwise.
- **Agent consumption layer**: the map, navigation capability, render
  capability, and blocked semantic/manipulation status are exposed through the
  same explicit runtime-prior / MCP / agent-visible context style as simulator
  assets, not through hidden scripts, stale generated outputs, or silent
  fallback.

Room/object semantic alignment improves open-ended task quality, but it is not
a hard prerequisite for Map12-driven navigation plus Gaussian rendering.
Semantic projection remains blocked until accepted semantic anchors exist.

## Completed Work Split

Completed prerequisite evidence now lives in
`docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md`. Treat that
file as evidence-only unless anchor lifecycle, residual thresholds, or readiness
semantics change.

Completed in this active plan:

- B1 topdown/review/fitter path for `2rd_floor_seperated`.
- Seven accepted `anchor_role=alignment` geometry anchors.
- Residual-backed Map12 waypoint or `map_xy/yaw` to B1 scene pose request path.
- Isaac same-pose FPV/Chase navigation smoke for two Map12 points.
- Operator preview promotion from accepted runtime camera evidence.
- Explicit B1 product/operator-console proof artifact requirements.
- B1 robot-consumption manifest and canonical runtime-prior wrapper exports.

Still active here:

- Preserve and expose B1 capability status through the robot-facing MCP/runtime
  map consumer path.
- Name and expose render/observation capability status for same-pose
  FPV/Chase/topdown evidence.
- Evaluate and select `B1_floor2_slow/` as the default visual/render route when
  it is verified against the same Map12 frame and same-pose evidence contract.
- Keep room/object semantics blocked in P0; semantic follow-ups live in
  `docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md`.

## Decision

Use the existing labels. Do not manually relabel everything.

Use `2rd_floor_seperated/` first because it has split room/partition/object
labels. Use those labels as scene-frame evidence and anchor hints. After a
reviewed transform exists, project labels into Map12 as candidates.

Keep `B1_floor2_slow/` out of the first semantic registration loop. It is more
photorealistic, but lacks the same split object labels. In P0, bring it back as
a visual/render route candidate only: register it to the already verified
Map12/B1 frame, prove same-pose render evidence, and select it as the default
visual route only when that proof passes. Do not use it to infer room labels,
object labels, or accepted semantics.

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

- This document is the current execution source for the remaining work needed
  to make B1 / Map 12 consumable like a simulator scene: expose verified B1
  capability status through the robot-facing runtime-prior/MCP consumer path,
  then add reviewed room/object semantic projection when human-accepted
  semantic anchors exist.
- The preview-grade robot pose application path has already passed:
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

Completed prerequisite criteria:

- The B1 topdown diagnostic and two-map review path exist for
  `2rd_floor_seperated`.
- Seven accepted `anchor_role=alignment` anchors are committed and use
  `scene_xyz`.
- The residual artifact reports rigid/similarity candidates, residual metrics,
  and `global_verified` status.
- Empty, seed-derived, bbox-fit, and proposed-only correspondences do not verify
  alignment.
- Residual-backed pose requests record input waypoint id or `map_xy/yaw`,
  coverage decision, transform source/artifact, and output B1 scene pose.
- Unsupported or unverified points block loudly with artifacts instead of
  falling back to another transform, point, or camera source.
- B1 FPV/Chase preview promotion requires same-waypoint, residual-backed,
  `isaac_runtime_*` evidence.

Remaining criteria:

- Agent-visible MCP/runtime map context exposes the B1 capability status from an
  explicitly supplied `runtime_map_prior`.
- The exposed capability context proves `robot_navigation_supported=true` for
  the verified B1 bundle while room semantics, object semantics, manipulation,
  planner-backed navigation, and physical-robot support remain blocked or out
  of scope.
- The exposed capability context names render/observation readiness for
  same-pose Gaussian/digital-twin FPV, Chase, and topdown evidence.
- `B1_floor2_slow/` is either verified and selected as the default
  photorealistic visual/render route, or explicitly blocked with a reason. A
  missing or unverified `B1_floor2_slow/` route must not silently fall back to
  `2rd_floor_seperated/` while claiming the slow route is selected.
- No runtime consumer path auto-discovers generated `output/**` artifacts or
  silently substitutes missing/malformed B1 proof inputs.
- The current seven alignment anchors never become room/object semantics.
- Strict room semantic projection and object semantic projection remain blocked
  in P0. Follow-up work lives in
  `docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md`.

## Non-Goals

- Do not make a fused Gaussian semantic map artifact.
- Do not use `B1_floor2_slow` for first-pass registration.
- Do not use affine transform as production truth. Affine is diagnostic only.
- Do not claim object/receptacle USD bindings or manipulation readiness.
- Do not change public `household-world` command grammar or MCP tools.
- Do not block P0 on human room semantic review.

## Implementation Slice

Completed slices:

- Topdown diagnostic, two-map review/export, Z-up `x,y` correspondence policy,
  fitter residuals, readiness/report wiring, pose request artifacts, B1
  navigation smoke, operator-preview camera promotion, explicit proof artifact
  requirements, robot-consumption manifest, and canonical runtime-prior wrapper
  exports.

Active P0:

- Preserve B1 digital-twin capability status from an explicitly supplied
  `runtime_map_prior` when `RealWorldCleanupContract` initializes runtime prior
  state.
- Expose that status through the agent-visible `runtime_metric_map` or adjacent
  map-context payload used by MCP/server artifacts.
- Name render/observation capability status in the existing
  `digital_twin_capabilities` / `capability_summary` surface. Prefer a sibling
  proof field such as `render_observation_proof` instead of overloading
  `robot_consumption_proof`.
- Prove the existing MCP flow sees the status:
  `metric_map -> navigate_to_waypoint -> observe`.
- Evaluate `B1_floor2_slow/` as the P0 photorealistic visual route. Select it
  by default only if it is registered to the same verified Map12 frame and
  produces same-pose render evidence; otherwise expose an explicit blocked
  visual-route status.
- Add focused tests proving the agent can see verified B1 navigation capability
  and blocked room/object/manipulation status without accepting semantics.

Out of scope for this P0 plan:

- Human room-semantic anchor review.
- Room semantic projection.
- Object-level semantic anchors/projection proof.
- Object/receptacle USD binding.
- Public absolute `map_xy/yaw` MCP navigation tool.

Those follow-ups are tracked in
`docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md`.

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

Preflight status: DRAFT

Task source: user request to merge/split completed B1 plans and preflight the
unfinished work; active plan path; completed prerequisite evidence contract.

Canonical source: `docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`

Route: durable `$intuitive-flow` after approval. Main session can implement the
first P0 slice directly if the diff stays narrow; use a delegated worker only
for isolated read-only review or long local proof.

Goal: Make the verified B1 / Map12 Gaussian asset behave like a simulator scene
for robot-facing consumers: Map12-driven on-demand navigation/pose application,
Gaussian multi-view rendering from the applied pose, and explicit
agent-visible runtime map capability status, while keeping unaccepted
room/object semantics blocked.

Scope:

- P0: expose existing B1 `digital_twin_capabilities` / `capability_summary`
  from an explicitly supplied `runtime_map_prior` into agent-visible
  MCP/runtime map context.
- P0: add focused tests proving the agent-visible context reports verified B1
  robot navigation and blocked room/object/manipulation status.
- P0: ensure the agent-visible contract names the currently proven render
  surface: residual-backed B1 pose application can produce same-pose
  Gaussian/digital-twin FPV, Chase, and topdown evidence without implying
  planner-backed or physical robot navigation.
- P0: evaluate `B1_floor2_slow/` as the photorealistic visual/render route and
  make it the default for navigation/open-task rendering only if its same-frame,
  same-pose render proof passes. Otherwise expose a blocked status and keep the
  verified P0 route honest.

Non-goals: redo geometry alignment, rerun topdown/anchor review unless evidence
is stale, auto-align maps, auto-accept semantic anchors, infer room/object labels
from geometry anchors, human-review room semantic anchors, project room/object
semantics, commit generated `output/**`, add fallback/autodiscovery, change
public command grammar, add a public MCP navigation tool, claim planner backing,
claim physical robot support, or implement manipulation/object USD binding.

Entity budget: reuse=`runtime_map_prior_snapshot_v1`,
`runtime_map_prior_targets.json`, `b1_robot_consumption_manifest.json`,
`RealWorldCleanupContract.agent_view_payload()`, existing MCP live artifact
writers, existing B1 render/navigation proof artifacts; remove/merge=do not keep
`2026-06-16` as a second active implementation plan; new=at most a small helper
for extracting/summarizing prior capabilities if needed to avoid duplicated
payload logic, plus a minimal visual-route status field for `B1_floor2_slow`
selection if the existing capability surface cannot express it; expansion
triggers=new artifact schema beyond capability fields, public tool/command,
compatibility shim, semantic auto-promotion, manipulation/planner support.

Context: must-read=`README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`,
`CLAUDE.md`, this plan,
`docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md`,
`docs/status/active/b1-map12-verified-map-scene-alignment.md`,
`roboclaws/household/realworld_contract_init.py`,
`roboclaws/household/realworld_contract_payloads.py`,
`roboclaws/household/realworld_runtime_map_contract.py`,
`roboclaws/household/realworld_mcp_server.py`,
`roboclaws/maps/runtime_prior_snapshot.py`; useful=focused tests under
`tests/contract/molmo_cleanup/` and `tests/contract/maps/`;
avoid-unless-needed=large `output/**`, historical retrospectives, old merged B1
bundle artifacts, broad UI rewrites.

Acceptance:

- SUCCESS: an agent-visible MCP/runtime map payload built from an explicit B1
  runtime prior contains B1 capability status showing
  `robot_navigation_supported=true`, a render/observation capability statement
  for same-pose Gaussian/digital-twin FPV/Chase/topdown evidence, and blocked
  room/object/manipulation status; tests prove this without accepting semantic
  anchors or reading generated fallback paths.
- SUCCESS: `B1_floor2_slow/` has a documented visual-route status. If verified,
  it is selected as the default photorealistic render route for
  navigation/open-task views; if not verified, it is explicitly blocked and P0
  does not claim it as selected.
- BLOCKED_NEEDS_LOCAL_VALIDATION: full product proof that depends on local Isaac
  or operator-console browser review remains local/manual if changed behavior
  reaches those surfaces.
- No regressions: no silent fallback, no backwards compatibility shim for old
  artifact names or call shapes, no `output/**` autodiscovery, geometry anchors
  remain geometry-only, semantic projection fails loudly until accepted semantic
  anchors exist.

Verification: deterministic=`ruff check` and `ruff format --check` on touched
files plus focused pytest for runtime prior snapshot, B1 bundle,
realworld contract/MCP server, and checker/console paths touched by the change;
integration=compile/convert B1 bundle with explicit alignment/navigation proof
artifacts when P0 changes prior consumption; MCP proof=exercise or test the
existing `metric_map -> navigate_to_waypoint -> observe` path against an
explicit B1 runtime prior; visual-route proof=verify `B1_floor2_slow/` status
and default selection or explicit blocked reason; product-run=B1 product/open
task or operator-console route with explicit `b1_alignment_artifact` and
`b1_navigation_artifact` when route behavior changes; local-live-manual=Isaac
navigation smoke and browser/operator-console review only if execution changes
pose/camera/console behavior.

Execution: main=own scope, code changes, focused verification, commit, and final
complete/blocked judgment; worker=none by default; worker-goal=none.

To execute: `/goal execute docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md with intuitive-flow`

Optional tracking: none

Approval: `LGTM`, `approve`, or `go ahead` approves this preflight; edits
request revision.

## Stop Condition

For the approved P0 slice, stop after the agent-visible MCP/runtime map context
exposes B1 capability status from an explicitly supplied runtime prior and
focused tests prove navigation-ready plus room/object/manipulation-blocked
status without fallback or semantic promotion. Also stop after
`B1_floor2_slow/` has an explicit P0 visual-route status: selected only if
verified, otherwise blocked with reason.

Do not broaden into public MCP tools, planner-backed navigation, physical robot
support, manipulation, room/object semantic projection, or fused semantic-map
authoring without a new plan update.

## Implementation Status

2026-06-18 planning-loop update:

- The agent planning loop concluded this 2026-06-17 plan owns the runtime
  application contract: residual-backed Map12 waypoint ids or on-demand
  `map_xy/yaw` points become B1 scene robot poses, Isaac pose applications, and
  same-pose visual evidence only inside verified coverage.
- `docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md` remains the
  prerequisite alignment/residual evidence source; this plan owns the newer
  Z-up `x,y` policy and runtime proof contract.
- The accepted geometry anchors, residuals, and local Isaac pose/camera proof
  now exist. The active implementation blocker is narrower: B1 capability status
  from the explicit runtime prior must still be exposed to the robot-facing
  MCP/runtime map consumer, and room/object semantics remain blocked until
  separate semantic anchors are accepted.
- Internal pose request contract is implemented:
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
- The compiled bundle writes `b1_robot_consumption_manifest.json` as the thin
  robot-consumer status packet. It summarizes navigation readiness, room/object
  semantic readiness, blocked capabilities, required bundle files, and the
  no-autodiscovery policy without adding another fallback path.
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
- The B1 product/open-task route now exports the compiled bundle into
  `runtime_map_prior_snapshot.json` and
  `runtime_map_prior_targets.json` beside the run output, and copies
  `b1_robot_consumption_manifest.json` to the run root. The export is an
  explicit visible artifact from the freshly compiled bundle; it does not
  auto-discover older generated `output/` files or silently change the default
  `runtime_map_prior` input.
- Operator-console state also lists those wrapper-level artifacts, so B1 runs
  launched from the console can expose the canonical prior and robot-consumer
  manifest even when the active live-attempt evidence is nested under a
  timestamp/seed directory.
- The B1 / Isaac checker path now uses
  `--require-b1-robot-consumption-proof`, which validates the run-local copied
  `map_bundle/semantics.json` for a verified
  `digital_twin_capabilities.robot_consumption_proof` and requires the run-root
  `b1_robot_consumption_manifest.json` to match the verified navigation proof.
  It intentionally does
  not reuse the older RBY1M `--require-real-robot-alignment` gate.
- When that gate is active, B1 product/open-task routes fail before launch
  unless both `b1_alignment_artifact` and `b1_navigation_artifact` are passed
  explicitly. Missing proof input is a blocker, not permission to auto-discover
  generated `output/` files.
- Operator-console B1 / Map 12 launch readiness follows the same rule and
  requires explicit readable JSON paths for both proof artifacts before Start
  Agent Run can become ready.
- `python scripts/maps/build_b1_map12_semantic_projection.py --correspondences assets/maps/b1-map12-scene-correspondences.json --review-manifest assets/maps/b1-map12-alignment-review.json --output output/b1-map12/semantic-projection/semantic_projection.json`
  currently exits non-zero with `accepted semantic anchors are required before
  projecting room labels`. This is expected until human-accepted
  `anchor_role=semantic` room-interior anchors are promoted.

Next implementation slice:

- Preserve and expose B1 `digital_twin_capabilities` / `capability_summary`
  from an explicitly supplied `runtime_map_prior` into the agent-visible
  MCP/runtime map context.
- Name render/observation readiness in that capability surface for same-pose
  Gaussian/digital-twin FPV, Chase, and topdown evidence.
- Prove the existing MCP path sees the B1 status through
  `metric_map -> navigate_to_waypoint -> observe`.
- Evaluate `B1_floor2_slow/` as the P0 photorealistic visual/render route. If
  it is registered to the same verified Map12 frame and produces same-pose
  render evidence, select it by default for navigation/open-task views. If not,
  expose a blocked visual-route status and do not claim it as selected.
- For product/open-task runs that need the robot-consumption proof inside the
  map bundle, pass explicit `b1_alignment_artifact=...` and
  `b1_navigation_artifact=...` overrides rather than relying on generated
  `output/` discovery.
- Do not human-review room semantic anchors or run semantic projection in this
  P0 slice. Those follow-ups live in
  `docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md`.

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

## Fresh Context Handoff

Paused on 2026-06-18 at the user's request so the remaining work can resume in
a fresh context.

Current proven state:

- Geometry alignment is accepted through seven committed
  `anchor_role=alignment` anchors in
  `assets/maps/b1-map12-scene-correspondences.json`.
- The official residual artifact is
  `output/b1-map12/alignment/alignment_residuals.json`; it is
  `global_verified` with `selected_transform_type=rigid_2d`, mean residual
  `0.352908 m`, p90 `0.491765 m`, and max `0.502064 m`.
- The first preview-grade robot-consumption proof passes through
  `output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json`.
  It applies two residual-backed Map12 navigation-memory points as B1 scene
  robot poses and records same-pose Isaac FPV/Chase evidence.
- Product and operator-console routes require explicit
  `b1_alignment_artifact=...` and `b1_navigation_artifact=...` paths before
  B1 proof consumption. They must not auto-discover generated `output/`
  artifacts.
- Compiled B1 runtime bundles write `b1_robot_consumption_manifest.json`,
  `runtime_map_prior_snapshot.json`, and `runtime_map_prior_targets.json`.
  `runtime_map_prior_targets.json` includes `digital_twin_capabilities` and
  `capability_summary`.

Known incomplete state:

- Room semantic projection is still blocked. The current committed
  correspondence manifest contains geometry anchors only.
- `docs/status/active/b1-map12-semantic-anchor-review-packet.json` is review
  input only. It is not accepted semantic truth.
- Object semantic projection and object/receptacle binding remain blocked.
- Manipulation, planner-backed navigation, physical robot navigation, and new
  public MCP navigation tools remain out of scope for this plan.
- `B1_floor2_slow/` has not yet been verified as the selected P0
  photorealistic visual/render route.
- A narrow consumer-chain gap was found just before pausing: the compiled B1
  prior carries `digital_twin_capabilities`, but
  `RealWorldCleanupContract` currently extracts prior observed objects,
  anchors, and rooms without preserving that capability status in the
  agent-visible MCP/runtime map payload. The next context should verify and fix
  that strict consumer path without promoting unreviewed semantics.

Recommended first slice for the new context:

1. Inspect `roboclaws/household/realworld_contract_init.py`,
   `roboclaws/household/realworld_contract_payloads.py`,
   `roboclaws/household/realworld_runtime_map_contract.py`, and
   `roboclaws/household/realworld_mcp_server.py`.
2. Expose existing B1 `digital_twin_capabilities` / `capability_summary` from
   an explicitly supplied `runtime_map_prior` into the agent-visible
   `runtime_metric_map` or adjacent map-context payload.
3. Add render/observation readiness to the same capability surface and cover it
   in focused tests.
4. Evaluate `B1_floor2_slow/` as the default visual/render route, with explicit
   selected or blocked status.
5. Add focused contract/MCP tests proving the agent can see
   `robot_navigation_supported=true` while room/object/manipulation capability
   status remains blocked.
6. Do not touch generated `output/**`, do not add fallback/autodiscovery, and do
   not infer room or object labels from the seven alignment anchors.
