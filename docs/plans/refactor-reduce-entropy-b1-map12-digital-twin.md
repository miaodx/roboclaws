---
refactor_scope: b1-map12-digital-twin-navigation-readiness
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-10
---

# Refactor: B1 Map 12 Digital Twin Navigation Readiness

**Status:** DONE - accepted checklist complete and local navigation evidence passed
**Created:** 2026-06-10
**Source:** `intuitive-reduce-entropy` / `intuitive-preflight` audit after reviewing
`data/robot-data-lab/scene-engine/data/2rd_floor_seperated` against Agibot
`robot_map_12` and the current Isaac Lab backend gates.
**Workflow:** Keep this as the canonical preflight contract for the B1 /
Map 12 digital-twin navigation seam. Execute through `intuitive-flow` after
approval.

## Current Finding

The B1 asset folder is useful for a Digital Twin rehearsal, and this execution
contract should stop only when the repo can support a robot navigation smoke in
that B1 / Map 12 scene. Geometry readiness and Map 12 overlay are required
subproofs, not the final stopping point.

Static evidence from the audit:

- `storey_1/scene_gs.usda` is the current default loaded scene layer for the
  rebuilt second-floor asset. It references `storey_1/scene.usd` and records
  Gaussian/scene overlay provenance.
- `storey_1/scene.usd` and the room-level `*/scene.usd` files contain the
  rebuilt mesh scene partitions. They are suitable as geometry/navigation
  context, not as object/receptacle semantic truth.
- The existing Isaac scene indexer can load a caller-supplied
  `--scene-usd-path`, but it currently recognizes object/receptacle candidates
  through MolmoSpaces `scene_metadata.json` or path conventions such as
  `/Objects` and `/Receptacles`.
- The current B1 scene has coarse meshes and has not been object-level or
  fixture-level segmented yet. Therefore the current indexer returns zero
  object candidates and zero receptacle candidates for the loaded scene unless
  a separate segmentation/manifest exists.
- Map 12 and B1 bounds overlap strongly enough to justify a transform/overlay
  probe, but not enough to claim a verified shared frame without anchor
  residuals.

## Accepted Boundary

Do not make object/receptacle USD binding or manipulation part of this target.

The target is:

```text
B1 coarse geometry
  + robot_map_12 occupancy/navigation memory
  -> static geometry readiness report
  -> candidate Map 12 overlay / transform report
  -> B1 navigation scene/harness input
  -> robot navigates between overlay waypoints in the B1 scene
  -> robot-view/report evidence for the navigation smoke
  -> explicit statement that semantic anchors are overlays, not USD prim truth
```

This keeps review honest:

- `geometry twin usable` means the coarse scene geometry can be loaded,
  bounded, rendered, and compared against Map 12.
- `semantic overlay usable` means Map 12 navigation-memory anchors can be
  projected into the B1 frame with provenance.
- `navigation usable` means a robot can be placed in the loaded B1 scene and
  moved between B1/Map12 overlay waypoints while producing changing robot-view
  evidence and a reportable trace.
- `semantic USD index usable` remains blocked until mesh segmentation or a
  human-authored/derived B1 scene manifest exists.
- `operation twin usable` for pick/place remains blocked until object/receptacle
  prim bindings, support surfaces, and interaction semantics exist.

## Preflight Contract

### Goal

Make the repo support a B1 / Map 12 Digital Twin navigation smoke where a robot
can move around the loaded B1 scene using Map 12 overlay waypoints, while
honestly distinguishing navigation evidence from blocked manipulation and
blocked USD object/receptacle semantics.

### Scope

- Add a static readiness script for
  `data/robot-data-lab/scene-engine/data/2rd_floor_seperated`.
- Inventory B1 USD/OBJ/Gaussian geometry without launching Isaac Sim or
  `SimulationApp` as the deterministic precheck.
- Read Map 12 Nav2 metadata and navigation-memory anchors.
- Attempt a Map 12 to B1 overlay/transform assessment during execution, using
  available bounds and anchors.
- Record overlay status as `candidate`, `verified`, or `blocked` based on the
  evidence discovered during execution.
- Preserve provenance: semantic anchors come from
  `robot_map_12_navigation_memory_overlay`, not USD segmentation.
- Add a B1 navigation smoke path that loads the B1 scene, places/imports the
  robot, drives it through at least two B1/Map12 overlay waypoints, captures
  robot-view images after movement, and writes a reportable navigation artifact.
- Add focused contract tests for the readiness artifact, navigation artifact,
  and blocked semantic/manipulation claims.

### Non-Goals

- Do not split or segment B1 meshes in this slice.
- Do not generate fake object/receptacle bindings from coarse mesh names.
- Do not make `selected USD bindings` pass for B1.
- Do not claim pick/place, support-surface extraction, segmentation evidence,
  or manipulation-level Digital Twin readiness.
- Do not claim planner-backed Nav2, collision-complete autonomy, or physical G2
  parity unless a separate planner/hardware acceptance gate is added and passed.
- Do not add a new public `surface` / `intent`; keep this as a maintainer
  confidence layer behind the current household-world direction.

### Target Output

Create a readiness/navigation artifact with at least these fields once the full
contract has passed:

```json
{
  "schema": "b1_map12_digital_twin_readiness_v1",
  "b1_geometry_loaded": true,
  "b1_geometry_source": "rebuilt_scene_engine_usd_meshes",
  "usd_object_index_ready": false,
  "usd_receptacle_index_ready": false,
  "reason": "B1 assets are currently coarse meshes without object-level segmentation",
  "map12_overlay_status": "candidate",
  "map12_to_b1_usd_transform_status": "unverified",
  "semantic_source": "robot_map_12_navigation_memory_overlay",
  "semantic_usd_binding_status": "blocked_until_segmentation_or_manifest",
  "robot_navigation_supported": true,
  "robot_navigation_provenance": "isaac_b1_map12_navigation_smoke",
  "navigation_waypoint_count": 2,
  "robot_view_evidence_status": "available",
  "manipulation_supported": false
}
```

The implementation may add more fields when useful, but these fields are the
minimum contract. The important invariant is that navigation support can become
true, while semantic USD readiness and manipulation remain false/blocked while
B1 remains coarse and unsegmented.

The static geometry precheck must not claim navigation success by itself. Before
the local Isaac navigation smoke passes, `robot_navigation_supported` must remain
`false` or absent, with an explicit pending/blocked reason. Only the combined
final artifact or the navigation-smoke artifact may set
`robot_navigation_supported=true`.

### Required Checks

- Open the B1 candidate USD with `.venv-isaaclab/bin/python` and `pxr.Usd`
  without launching Isaac Sim / `SimulationApp`.
- Record stage metadata: default prim, `metersPerUnit`, up axis, prim count,
  mesh count, local referenced layers, and world bounds where available.
- Record rebuilt Gaussian scene layer and room/partition USD inventory
  separately from mesh-scene geometry bounds.
- Read Map 12 Nav2 metadata from
  `vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot/nav2.yaml`.
- Read Map 12 semantic anchors from
  `vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json`.
- Produce a candidate overlay report without claiming verified frame parity
  unless at least three anchors can be matched with residuals.
- Run a B1 navigation smoke in a real Isaac runtime when claiming
  `robot_navigation_supported=true`.
- Capture robot-view evidence from at least two distinct robot poses in the B1
  scene.
- Record whether navigation is kinematic/pose-driven, planner-backed, or
  blocked. Kinematic navigation is acceptable for this plan if it is labeled
  honestly and produces real scene/robot-view evidence.

### Suggested Proof

```bash
.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py \
  --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  --output output/b1-map12/readiness/readiness.json

just harness::b1-map12-navigation-smoke \
  b1_root=data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  map12_root=vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  output_dir=output/b1-map12/navigation-smoke

./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_b1_map12_digital_twin_readiness.py -q
```

The script, harness recipe, and test names are proposed targets; they do not
exist yet.

### Definition Of Done

SUCCESS only if:

- the readiness script writes a JSON artifact matching
  `b1_map12_digital_twin_readiness_v1`;
- the artifact proves B1 coarse geometry can be inspected statically;
- the artifact records Map 12 bounds and semantic-anchor inventory;
- the artifact records overlay/transform status with provenance and, when
  available, residual evidence;
- the static readiness artifact does not claim robot navigation support before
  the local navigation smoke has actually run;
- a B1 navigation smoke places/imports a robot in the loaded B1 scene and moves
  it through at least two overlay waypoints;
- the navigation smoke writes robot-view evidence from distinct poses and a
  reportable navigation artifact;
- the navigation artifact explicitly states navigation provenance, such as
  `kinematic`, `planner_backed`, or `blocked`;
- tests fail if the artifact claims USD object/receptacle readiness while B1 is
  still coarse and unsegmented;
- tests fail if semantic anchors are presented as USD segmentation or USD prim
  truth;
- tests fail if a static-only artifact claims
  `robot_navigation_supported=true`;
- tests fail if manipulation is presented as supported.

BLOCKED_NEEDS_DECISION if:

- a verified transform requires human-owned anchor matches that cannot be
  inferred from local files;
- the desired readiness claim expands from navigation to manipulation,
  planner-backed Nav2, physical G2 parity, or semantic USD binding.

BLOCKED_NEEDS_LOCAL_VALIDATION if:

- execution cannot run the required local GPU/Isaac navigation smoke needed to
  prove `robot_navigation_supported=true`.

INTERMEDIATE_ONLY if explicitly approved:

- static geometry and overlay artifacts exist, but the local Isaac navigation
  smoke cannot be run yet.

Must not regress:

- existing MolmoSpaces prepared-USD Isaac gates and segmentation gates;
- existing Map 12 / Agibot navigation-memory conversion contracts;
- public `household-world` surface and cleanup/map-build intents.

## Architecture Packet

### Zoom-Out Map

- `vendors/agibot_sdk/artifacts/maps/robot_map_12` owns the Map 12 Nav2 map,
  occupancy grid, raw map snapshot, and navigation-memory anchors.
- `data/robot-data-lab/scene-engine/data/2rd_floor_seperated` owns the current
  rebuilt B1 second-floor Gaussian, USD, room-partition, and local asset
  payloads.
- `roboclaws/household/isaac_lab_backend.py` passes optional
  `scene_usd_path` into the worker without importing Isaac in the core process.
- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` owns USD loading,
  scene indexing, selected binding diagnostics, robot-view capture, and
  segmentation diagnostics.
- `just/harness.just` owns local-only Isaac smoke gates. Existing gates are
  strict for renderer proof and selected USD bindings, which is correct for
  MolmoSpaces prepared scenes but too strong for B1 coarse geometry today.

### Eng-Review Recommendation

Execute this as one bounded slice. During implementation, discover how far the
Map 12 overlay can honestly go and then use the best available overlay waypoints
for a robot navigation smoke. Stop or mark the artifact blocked when local
evidence is insufficient rather than inventing semantic bindings or navigation
proof.

### Public Contract / Boundary

B1 navigation readiness is a maintainer/local-dev confidence layer, not a new
public `surface` or cleanup `intent`. Keep the public household-world contract
unchanged until the B1 path can produce a stable report shape without ambiguous
provenance.

### Data Flow

```text
B1 USD/OBJ/Gaussian assets
  -> static geometry inventory
  -> B1 bounds and load diagnostics

Map 12 Nav2 + navigation_memory
  -> map bounds and semantic anchor inventory
  -> candidate overlay / transform report

geometry inventory + overlay report
  -> B1 navigation harness input
  -> local Isaac robot navigation smoke
  -> readiness + navigation artifact
```

### Rejected Alternatives

- Rejected: force B1 coarse meshes into object/receptacle bindings.
  Reason: it creates false confidence before segmentation exists.
- Rejected: start with a full Isaac GPU cleanup smoke.
  Reason: renderer proof would not prove semantic or Map 12 parity.
- Rejected: add a public task/surface now.
  Reason: this is still a backend/readiness confidence layer.
- Rejected: require planner-backed Nav2 as the first navigation proof.
  Reason: the useful first proof is that the robot can be controlled around the
  B1 scene with visible pose/camera evidence; planner-backed autonomy can be a
  later strengthening gate.

## Verification

Deterministic gates:

```bash
./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_b1_map12_digital_twin_readiness.py -q

ruff check scripts/isaac_lab_cleanup/check_b1_map12_readiness.py \
  tests/contract/maps/test_b1_map12_digital_twin_readiness.py
```

Integration gates:

```bash
.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py \
  --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  --output output/b1-map12/readiness/readiness.json
```

Product run gates:

```bash
just harness::b1-map12-navigation-smoke \
  b1_root=data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  map12_root=vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  output_dir=output/b1-map12/navigation-smoke
```

Local/live/manual gates:

- Required for SUCCESS: local Isaac/GPU navigation smoke must pass if the plan
  claims robot navigation support.
- If local Isaac/GPU cannot run in the current environment, close as
  `BLOCKED_NEEDS_LOCAL_VALIDATION`, not SUCCESS.
- No physical G2 hardware gate is required for this plan.

Optional exploratory gates:

- Generate an overlay preview image or short navigation GIF for human review if
  the JSON evidence is hard to inspect, but do not make it a required gate
  unless implementation depends on it.

## Stop Condition

Mark this plan done when:

- a static readiness artifact is produced;
- the artifact distinguishes geometry readiness from semantic/operation
  readiness;
- Map 12 overlay status is `candidate`, `verified`, or `blocked` with a concrete
  reason;
- robot navigation support is proven by a local B1 navigation smoke with
  changing robot pose/camera evidence, or the plan is closed as
  `BLOCKED_NEEDS_LOCAL_VALIDATION`;
- tests reject any artifact that claims USD object/receptacle readiness while
  B1 remains coarse and unsegmented;
- tests reject any artifact that claims manipulation support.

## Execution Log

### 2026-06-11 - Rebuilt Scene Asset Refresh

Status: current default asset updated.

- Replaced the old `B1_floor2_slow` default asset root with
  `data/robot-data-lab/scene-engine/data/2rd_floor_seperated`.
- The launch/default smoke scene now uses `storey_1/scene_gs.usda`, with
  `storey_1/scene.usd` retained in readiness evidence as the mesh scene.
- Readiness evidence now inventories the rebuilt scene-engine partitions and
  room-level `scene_gs.usda` layers instead of assuming the old
  `usda/livingroom` / `usda/F2_all` layout.

### 2026-06-10 - Implemented And Verified

Status: DONE.

Implemented:

- Added `scripts/isaac_lab_cleanup/check_b1_map12_readiness.py` to write
  `b1_map12_digital_twin_readiness_v1`.
- Added `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py` to write
  `b1_map12_navigation_smoke_v1`.
- Added contract tests for static readiness, navigation-smoke validation,
  readiness/navigation merge behavior, and blocked semantic/manipulation
  claims.
- Added `just harness::b1-map12-navigation-smoke` as a maintainer-only local
  confidence layer.
- Added `agent::harness b1-map12-navigation-smoke` dispatch coverage so the
  maintainer wrapper can route to the recipe without invoking Isaac during
  contract tests.

Evidence:

- Static readiness artifact:
  `output/b1-map12/readiness/readiness.json`.
- Local Isaac navigation smoke:
  `output/b1-map12/navigation-smoke/codex_probe2/navigation_smoke.json`.
- Merged readiness/navigation artifact:
  `output/b1-map12/navigation-smoke/codex_probe2/readiness_with_navigation.json`.
- Navigation smoke result: `status=passed`,
  `robot_navigation_supported=true`, `navigation_waypoint_count=2`,
  `robot_view_evidence_status=available`, validation errors empty.
- Merged readiness result: `readiness_status=navigation_ready`,
  `map12_overlay_status=candidate`, `robot_navigation_supported=true`,
  `navigation_waypoint_count=2`, validation errors empty.

Verification:

```bash
./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_b1_map12_digital_twin_readiness.py -q

./scripts/dev/run_pytest_standalone.sh \
  tests/contract/dev_tools/test_isaac_runtime_preflight_just_recipe.py -q

.venv/bin/ruff check \
  scripts/isaac_lab_cleanup/check_b1_map12_readiness.py \
  scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py \
  tests/contract/maps/test_b1_map12_digital_twin_readiness.py \
  tests/contract/dev_tools/test_isaac_runtime_preflight_just_recipe.py

just --list harness | rg b1-map12
```

Documentation alignment:

- Checked `README.md`, `ARCHITECTURE.md`, `STATUS.md`, and `docs/human/**`
  for public-surface drift.
- Left them unchanged because this remains a maintainer-only harness confidence
  layer, not a new public `surface`, cleanup `intent`, reusable profile, or
  repo-level current focus.
- Rechecked domain/context vocabulary in `docs/human/domain.md` and
  `CONTEXT.md`; no durable term change was needed.

## Execution Surface

- Main session: supervise scope, review diff, run deterministic/static gates,
  and decide final status.
- Worker: none by default. Use a worker only if static USD probing becomes
  long-running or needs isolated logs.
- Worker-local goal: none.

## To Execute

```text
/goal execute docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md with intuitive-flow
```

## Parked Items

- Build a B1 scene manifest once object-level or fixture-level segmentation is
  available.
- Promote the B1 route from maintainer harness to a public surface/intent only
  after the navigation-smoke report shape and provenance are stable.
- Investigate using `F2_all` Gaussian as a visual background layer behind
  coarse or segmented geometry.
