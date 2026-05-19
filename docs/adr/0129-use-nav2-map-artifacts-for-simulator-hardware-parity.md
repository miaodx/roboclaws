# 0129. Use Nav2 Map Artifacts For Simulator Hardware Parity

Date: 2026-05-18

## Status

Accepted

## Decision

MolmoSpaces cleanup and physical robot cleanup should use the same
real-world-like public cleanup contract shape. The simulator path will generate
a Nav2-shaped map artifact from the MolmoSpaces scene, and the hardware path
will consume a prebuilt Nav2 map plus matching fixture/waypoint semantics.

The two paths may differ by provenance and blocked capabilities, not by the
agent-facing map contract: Molmo navigation can remain `api_semantic` or
`sim_planner`, hardware navigation can report `nav2_action`, Molmo manipulation
can remain `api_semantic`, and first-pilot hardware manipulation should remain
`blocked_capability`.

The canonical artifact shape is a directory bundle:

- `map.yaml` plus an occupancy image for Nav2 compatibility;
- `semantics.json` for rooms, fixtures, affordances, inspection waypoints,
  frame IDs, and provenance;
- robot-specific profile and costmap parameter files for the selected robot;
- a normalized JSON `metric_map()` response that references the artifact paths.

Molmo generates the bundle from simulator public scene state. The first
exporter should use the existing MolmoSpaces subprocess worker/backend metadata
such as room outlines, receptacles, object-free public geometry, robot poses,
and map-rendering helpers instead of starting from a raw XML parser. If that
metadata proves insufficient for stable geometry, a later exporter may add a
small XML reader as a fallback or enrichment step. Hardware uses an
operator-provided Nav2 map plus authored fixture/waypoint semantics in the same
bundle shape.

For a fixed MolmoSpaces scene and fixed map-generation parameters, the generated
Nav2 map artifact should be deterministic and reusable. Run-local map snapshots
exist for auditability and report immutability, not because a fixed simulator
scene is expected to drift. Generated or sampled Molmo scenarios may still
produce different map bundles when the scene id, seed, source XML, asset version,
or generation parameters change.

Roboclaws cleanup runs should not switch scenes mid-run. Any MolmoSpaces scene
selected for the supported cleanup set should have its Nav2 map bundle generated
ahead of the run. During a run, Roboclaws copies the selected bundle into the
run output so the report preserves the exact map contract the agent used.
Reusable generated map bundles should live under
`assets/maps/<environment_id>/`, with run-local immutable snapshots copied to
`output/.../map_bundle/`.

The first exporter target is static global costmap parity, not full Nav2 runtime
simulation. A Molmo map bundle should include `costmap_params.yaml` for static
map and inflation settings so simulator and hardware share the same global-map
contract. Runtime obstacle, voxel, sensor marking/clearing, TF timing, and local
rolling costmap behavior are known differences and should be reported as
`not_simulated` or `blocked_capability` until a later runtime-perception phase.
The first `rby1m` defaults are conservative static-navigation values:
`resolution_m=0.05`, `inflation_radius_m=0.45`, `cost_scaling_factor=3.0`,
`occupied_threshold=0.65`, and `free_threshold=0.25`. Robot footprint or radius
belongs in the selected robot profile, not the environment map.

Map artifacts should stay environment-owned, while robot dimensions and
navigation tolerances live in a separate robot profile. First use
`robot_profile=rby1m`, but the bundle structure must allow later profiles such
as `unitree_g1` or `agibot_g2` without rewriting the environment map. Reports
should record the selected robot profile id and a parameter hash.

Inspection waypoints stay as static environment semantics. Roboclaws should not
precompute per-robot resolved waypoint sets in the first implementation. At run
time, the selected backend judges reachability: real hardware through Nav2
planning/actions, and Molmo through the generated static costmap or a simulator
planner approximation. Reports should record each waypoint's
`reachability_status`, `navigation_backend`, and failure reason when blocked.

Navigation failures should be explicit agent-visible outcomes, not hidden
retargeting. If `navigate_to_waypoint` is blocked, the tool returns
`blocked_capability`, backend error summary, current pose, target pose, and
failure type. The agent may choose another public waypoint or observe from the
current pose. A later public semantic service may suggest nearest reachable
alternatives, but the first implementation should not silently change goals.

For the physical pilot, `navigate_to_receptacle` should be implemented as
fixture waypoint navigation: resolve the fixture id through public static
semantics to its preferred inspection or manipulation waypoint, then send that
pose to Nav2. The response should record `goal_source=fixture_preferred_waypoint`
and `manipulation_ready=false`. This keeps the cleanup-shaped tool list aligned
with Molmo while avoiding any claim that physical pick/place/open/close is
available.

## Consequences

- Sim and hardware runs can share one cleanup skill and one map-oriented Agent
  View shape.
- Molmo reports remain useful cleanup demos because semantic pick/place/open/close
  can still execute in simulation.
- The map artifact must be treated as public static environment context, not a
  hidden movable-object map or private scoring shortcut.
