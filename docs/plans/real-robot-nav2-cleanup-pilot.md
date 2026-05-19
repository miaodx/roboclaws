# Real Robot Nav2 Cleanup Pilot

**Status:** Proposed source plan
**Created:** 2026-05-18
**Source:** grill-with-docs session on MolmoSpaces cleanup, Nav2 map parity, and
real robot deployment
**Workflow:** Pre-GSD plan. Ingest into `.planning/` before implementation.

## Problem

Roboclaws now has a real-world-style MolmoSpaces cleanup contract, but physical
robot deployment is still only a contract/readiness target. The next useful step
is not full physical cleanup; it is a Navigation + Perception Pilot that makes a
real robot consume the same public cleanup map/observation contract as the
simulator while keeping physical manipulation honestly blocked.

The simulator and hardware paths should differ by backend provenance and known
blocked capabilities, not by agent-facing task shape.

## Goal

Create one real-world-like cleanup contract shape shared by MolmoSpaces and a
future physical robot:

- MolmoSpaces consumes prebuilt Nav2-shaped map bundles for selected fixed
  scenes; map generation is an explicit preparation step, not a cleanup runtime
  side effect.
- Physical robots consume the same map bundle shape from prebuilt Nav2 maps.
- Agents use the same cleanup skill and MCP tool shape in sim and hardware.
- Reports distinguish `api_semantic`, `sim_planner`, `nav2_action`,
  `not_simulated`, and `blocked_capability`.
- The first hardware acceptance gate proves physical navigation plus observation,
  not physical manipulation.

## Decisions Locked

- Use direct ROS 2/Nav2 backend integration before ROSClaw or another OpenClaw
  bridge. See ADR-0127.
- Add `real_robot_cleanup_v1` instead of reusing `molmospaces_cleanup_v1` for
  hardware. See ADR-0128.
- Use Nav2 map artifacts for simulator/hardware parity. See ADR-0129.
- Runs do not switch scenes mid-run.
- Supported MolmoSpaces scenes must have map bundles generated before a run.
  Live cleanup runs fail fast when the selected prebuilt map bundle is missing
  or fails the map contract gate.
- Fixed MolmoSpaces scene + fixed source XML/seed/assets/parameters should
  produce deterministic, reusable map bundles.
- The first Molmo exporter should use existing MolmoSpaces worker/backend state
  metadata plus optional authored overrides rather than direct source XML
  parsing; add XML parsing later only if public scene metadata is missing
  required geometry.
- Static fixture/furniture footprints should be occupied in the generated
  occupancy map. Preferred inspection and manipulation waypoints should be
  nearby free poses, not inside the fixture footprint.
- A cleanup-capable map bundle requires `semantics.json`; `map.yaml` plus a raw
  occupancy image is insufficient because cleanup needs rooms, fixtures,
  affordances, waypoints, and frame metadata.
- The Nav2 map bundle is the static source of truth. `metric_map()` is an
  agent-facing JSON projection generated from the bundle, not an independent
  map source.
- Codex, Claude, and OpenClaw should not parse or plan over raw occupancy
  images directly. Agents plan over `metric_map()` / `fixture_hints`; backend
  code consumes the map/costmap artifacts below MCP.
- In Molmo simulation, "Nav2 map consumption" means static costmap route
  validation behind `navigate_to_waypoint`, not full ROS 2/Nav2 execution.
- Each run still snapshots the selected map bundle into `output/.../map_bundle/`
  for report immutability.
- Reusable map bundles live under `assets/maps/<environment_id>/`; run outputs
  contain only the immutable per-run snapshot.
- Supported Molmo demo bundles may be committed for deterministic harness/CI
  use. Physical robot map bundles may remain operator-provided local inputs.
- First costmap target is static global costmap plus inflation parity; runtime
  obstacle/voxel/local costmap simulation is out of scope.
- First `rby1m` defaults: `resolution_m=0.05`,
  `inflation_radius_m=0.45`, `cost_scaling_factor=3.0`,
  `occupied_threshold=0.65`, `free_threshold=0.25`, with robot footprint or
  radius stored in `profiles/rby1m.yaml`.
- Environment maps and robot profiles are separate. Start with
  `robot_profile=rby1m`, but leave room for `unitree_g1` and `agibot_g2`.
- Static inspection waypoints belong to the environment semantics; backend
  reachability checks decide whether they are usable at runtime.
- Map-layer acceptance is deterministic before live-agent proof. A map contract
  harness must validate a bundle and route semantics before any long Codex /
  Claude / OpenClaw cleanup run is treated as useful evidence.
- First-pilot physical `navigate_to_receptacle` is executable only as fixture
  preferred-waypoint navigation through Nav2. It does not require a held object
  and must report `manipulation_ready=false`.
- Navigation failures are explicit outcomes, not hidden retargeting.
- Agent drivers cannot directly control ROS topics, services, or actions.

## Contract Shape

Map bundle:

- `map.yaml` plus occupancy image for Nav2 compatibility.
- `semantics.json` for rooms, fixtures, affordances, inspection waypoints, frame
  ids, map/source provenance, and public static semantics.
- `robot_profile.yaml` for footprint, inflation radius, frames, camera pose, and
  navigation tolerances.
- `costmap_params.yaml` generated or assembled from the map bundle and selected
  robot profile.
- `metric_map()` returns a normalized JSON view and artifact paths.
- `metric_map()` is generated from the selected bundle snapshot. It contains
  rooms, driveable links, inspection waypoints, fixture references, artifact
  paths, frame ids, and route-validation metadata for agent planning.

Reusable bundle layout:

```text
assets/maps/<environment_id>/
  map.yaml
  map.pgm
  semantics.json
  profiles/
    rby1m.yaml
    unitree_g1.yaml
    agibot_g2.yaml
  costmaps/
    rby1m.costmap_params.yaml
```

First `rby1m` static costmap defaults:

```yaml
resolution_m: 0.05
inflation_radius_m: 0.45
cost_scaling_factor: 3.0
occupied_threshold: 0.65
free_threshold: 0.25
```

Tool behavior:

- `metric_map` and `fixture_hints` expose public static context only.
- `navigate_to_waypoint` returns `nav2_action` on hardware success,
  `sim_costmap_planner` or `sim_planner` in Molmo when static route validation
  is used, and `blocked_capability` with evidence on failure.
- Molmo `navigate_to_waypoint` should validate route feasibility against the
  selected static costmap bundle before reporting success. It should record
  goal pose, reachability, path length or failure type, and the navigation
  backend used.
- Hardware `navigate_to_receptacle` resolves fixture ids to preferred public
  waypoints and returns `nav2_action` or explicit `blocked_capability`; it does
  not imply manipulation readiness.
- `observe` returns camera-derived labels by default on hardware, with
  `camera-raw` as an optional profile.
- Hardware `pick`, `place`, `place_inside`, `open_receptacle`, and
  `close_receptacle` return structured `blocked_capability` in the first pilot.
- Molmo manipulation may remain `api_semantic` so simulation keeps a real cleanup
  demo path.

## Implementation Phases

1. **Generic Map Package Boundary**
   Move generic Nav2-shaped map bundle logic out of
   `roboclaws/molmo_cleanup/nav2_map_bundle.py` into a reusable
   `roboclaws/maps/` package. Keep cleanup task logic in `molmo_cleanup`; put
   loading, validation, projection, rasterization, and route validation in the
   map package.

   Suggested shape:

   ```text
   roboclaws/maps/
     bundle.py      # load/save/validate Nav2 Map Artifact
     project.py     # bundle -> metric_map()/fixture projection
     rasterize.py   # public scene geometry -> occupancy image
     route.py       # static costmap route validation
   scripts/maps/
     export_bundle.py
     check_bundle.py
   ```

2. **Molmo Map Bundle Exporter**
   Generate deterministic `map.yaml`, occupancy image, `semantics.json`,
   robot profiles, and costmap params for selected MolmoSpaces scenes. Use
   existing subprocess worker/backend scene metadata first: room outlines,
   fixed receptacles/furniture, approximate public footprints, robot poses, and
   current map-rendering helpers. Support authored overrides for fixed demo
   scenes. Keep movable object instances and private scoring truth out.

   Rasterization rule: room polygons become free space; outside-room cells and
   static fixture footprints become occupied; door/driveable links remain free
   corridor regions; inspection/manipulation waypoints must validate as nearby
   free poses after footprint/inflation checks.

3. **Map Contract Harness**
   Add a deterministic checker CLI for prebuilt map bundles. It should run in
   seconds without a live model and should fail a bundle before any live cleanup
   agent starts.

   The checker verifies:

   - required files: `map.yaml`, occupancy image, `semantics.json`, robot
     profile, and costmap params;
   - `map.yaml` resolves to the occupancy image and has sane resolution, origin,
     and thresholds;
   - occupancy image has non-trivial free and occupied cells;
   - `semantics.json` contains rooms, fixtures, affordances, waypoints,
     driveable links, frame ids, and provenance;
   - fixture footprints rasterize to occupied cells;
   - waypoints are in bounds, free, and outside inflated fixture cells;
   - each fixture has a reachable preferred inspection or manipulation waypoint;
   - declared driveable waypoint pairs pass static route validation;
   - no runtime observed objects, movable-object manifest, or private target
     truth is encoded.

4. **Map Projection, Snapshot, Report, And Run Gate**
   Generate `metric_map()` and `fixture_hints` from the selected map bundle
   rather than generating the bundle from contract internals. Copy the selected
   prebuilt bundle into each run directory, render it in the Cleanup Artifact
   Report, and preserve hashes/provenance.

   Live agent runs fail fast when the selected bundle is missing or when the map
   contract harness fails. Unit tests and small synthetic tests may use explicit
   lightweight fixtures, but they should not silently bypass the live-run map
   gate.

5. **Sim Costmap Route Validation**
   Add a pure-Python static costmap route checker behind Molmo
   `navigate_to_waypoint` and fixture navigation. It consumes the occupancy map,
   robot profile, and costmap params; validates reachability; and reports
   `navigation_backend=sim_costmap_planner` with route metadata. Do not launch a
   ROS 2/Nav2 stack for normal Molmo cleanup.

6. **Real Robot Cleanup Profile**
   Add `real_robot_cleanup_v1` to semantic profile metadata with the same
   cleanup-shaped public tool list and explicit blocked manipulation
   capabilities for the first pilot.

7. **Nav2 Backend Adapter With Mock Tests**
   Add a backend interface that resolves waypoint goals to Nav2-style action
   requests, supports timeout/cancel/failure evidence, and can run fully mocked
   in CI without a live ROS graph.

8. **Physical Pilot Runbook**
   Document local prerequisites, map bundle preparation, robot profile selection,
   safety stop expectations, command recipe, acceptance criteria, and artifact
   review steps for a real robot run.

## Non-Goals

- Do not claim physical cleanup.
- Do not implement physical pick/place/open/close.
- Do not expose direct ROS topic/service/action controls to agents.
- Do not run a full ROS 2/Nav2 stack inside the normal Molmo cleanup demo.
- Do not simulate full Nav2 runtime obstacle, voxel, TF timing, or rolling local
  costmap behavior in Molmo; report those gaps explicitly.
- Do not make raw `map.pgm` the agent's planning surface.
- Do not generate map bundles implicitly during cleanup run startup.
- Do not add a generic `robot_task_v1` profile yet.
- Do not make ROSClaw a first-pilot dependency.

## Acceptance Criteria

- A fixed MolmoSpaces scene has a stable prebuilt Nav2 map bundle before a run.
- The map bundle is produced by an explicit exporter and stored under
  `assets/maps/<environment_id>/` for supported simulator demos.
- The map bundle contains non-trivial occupancy, cleanup semantics, robot
  profile, and costmap params.
- A deterministic map contract harness passes before live cleanup starts.
- A live Molmo cleanup run fails fast when its required prebuilt map bundle is
  missing or invalid.
- `metric_map()` and `fixture_hints` are generated from the selected bundle
  snapshot rather than from an independent semantic map source.
- Molmo `navigate_to_waypoint` performs static route validation against the
  selected bundle and records route metadata/provenance.
- A Molmo cleanup run snapshots the selected map bundle and reports its
  artifact paths, provenance, robot profile id, and parameter hash.
- `metric_map()` returns the same normalized map contract shape for Molmo and
  real robot profiles.
- `real_robot_cleanup_v1` exists and validates public/private metadata
  boundaries.
- Mock Nav2 tests prove success, timeout, cancel, unreachable goal, and explicit
  blocked failure responses.
- First hardware pilot can load a prebuilt map bundle and robot profile, attempt
  every inspection waypoint and fixture preferred waypoint, observe from reached
  waypoints, keep physical manipulation blocked, and render
  `physical_navigation_pilot=true` with `physical_cleanup_ready=false`.

## Open Implementation Choices

None at the contract level. Remaining choices should be implementation details
inside the GSD phase unless they change the public contract, artifact layout,
map authority model, harness gate, or hardware safety claim.
