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

- MolmoSpaces generates or consumes Nav2-shaped map bundles for selected fixed
  scenes.
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
- Supported MolmoSpaces scenes should have map bundles generated before a run.
- Fixed MolmoSpaces scene + fixed source XML/seed/assets/parameters should
  produce deterministic, reusable map bundles.
- The first Molmo exporter should use existing MolmoSpaces worker/backend state
  metadata rather than direct source XML parsing; add XML parsing later only if
  public scene metadata is missing required geometry.
- Each run still snapshots the selected map bundle into `output/.../map_bundle/`
  for report immutability.
- Reusable map bundles live under `assets/maps/<environment_id>/`; run outputs
  contain only the immutable per-run snapshot.
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
- `navigate_to_waypoint` returns `nav2_action` on hardware success, `api_semantic`
  or `sim_planner` in Molmo, and `blocked_capability` with evidence on failure.
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

1. **Molmo Map Bundle Exporter**
   Generate deterministic `map.yaml`, occupancy image, `semantics.json`,
   `robot_profile.yaml`, and `costmap_params.yaml` for selected MolmoSpaces
   scenes. Use existing subprocess worker/backend scene metadata first: room
   outlines, receptacles, object-free public geometry, robot poses, and current
   map-rendering helpers. Keep movable object instances and private scoring
   truth out.

2. **Map Snapshot, Report, And Checker**
   Copy the selected map bundle into each run directory, reference it from
   `metric_map()`, render it in the Cleanup Artifact Report, and add checker
   gates for artifact presence, hash/provenance, policy-view safety, and known
   runtime costmap gaps.

3. **Real Robot Cleanup Profile**
   Add `real_robot_cleanup_v1` to semantic profile metadata with the same
   cleanup-shaped public tool list and explicit blocked manipulation
   capabilities for the first pilot.

4. **Nav2 Backend Adapter With Mock Tests**
   Add a backend interface that resolves waypoint goals to Nav2-style action
   requests, supports timeout/cancel/failure evidence, and can run fully mocked
   in CI without a live ROS graph.

5. **Physical Pilot Runbook**
   Document local prerequisites, map bundle preparation, robot profile selection,
   safety stop expectations, command recipe, acceptance criteria, and artifact
   review steps for a real robot run.

## Non-Goals

- Do not claim physical cleanup.
- Do not implement physical pick/place/open/close.
- Do not expose direct ROS topic/service/action controls to agents.
- Do not simulate full Nav2 runtime obstacle, voxel, TF timing, or rolling local
  costmap behavior in Molmo.
- Do not add a generic `robot_task_v1` profile yet.
- Do not make ROSClaw a first-pilot dependency.

## Acceptance Criteria

- A fixed MolmoSpaces scene can produce a stable Nav2 map bundle before a run.
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

None. Remaining choices should be implementation details inside the GSD phase
unless they change the public contract, artifact layout, or hardware safety
claim.
