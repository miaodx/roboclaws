# MolmoSpaces Real-Robot Contract Alignment

**Status:** Proposed source plan
**Created:** 2026-05-11
**Source:** repo status review, real-world cleanup contract review, Nav2/EasyNav
alignment discussion
**Workflow:** Pre-GSD plan. Ingest into `.planning/` before implementation.

## Problem

Roboclaws has moved from VLM/AI2-THOR demos toward MCP-driven coding agents
running cleanup and manipulation tasks. The strongest real-robot-facing surface
today is `realworld_cleanup_v1` through `molmo_cleanup_realworld`, not the older
AI2-THOR navigator contract.

The current repo still has simulation-only capabilities in nearby surfaces:

- `scene_objects` and `goto` are useful AI2-THOR debug/oracle tools but are not
  real robot capabilities.
- `map-v2` and chase camera views are valuable report/debug artifacts, but a
  physical robot policy should not depend on a third-person chase camera.
- `navigate_to_object` and `navigate_to_receptacle` currently can still be
  backed by semantic simulator state, so their provenance must remain explicit.
- The cleanup contract exposes metric map and fixture hints, but those payloads
  are not yet shaped like Nav2-compatible map/pose data.

The next step should align the contract and reports with realistic wheeled or
humanoid robot deployment without adding a live ROS/Nav2 dependency yet.

## Goal

Make `realworld_cleanup_v1` look like a real-robot contract at the data boundary:

- public metric maps are Nav2-compatible in shape;
- fixed environment semantics are represented as rooms, fixtures, affordances,
  and inspection waypoints;
- small movable objects are still discovered from robot-local FPV/perception;
- navigation and manipulation responses carry honest provenance;
- chase camera is marked report-only and excluded from policy inputs;
- reports and checkers expose whether an artifact is real-robot-ready or still
  simulation/semantic.

Do not create a new generic `robot_task_v1` contract in this phase. Extend the
existing cleanup contract first; extract a generic robot-task contract only
after another non-cleanup task needs the same interface.

## Decisions Locked

- Use `realworld_cleanup_v1` / `molmo_cleanup_realworld` as the phase baseline.
- Nav2 is the first alignment target because its map/action concepts are the
  most common ROS 2 deployment path.
- EasyNav/NavMap remains a later adapter option, not a first-phase acceptance
  criterion.
- The prebuilt semantic map may include only static environment knowledge:
  rooms, fixed fixtures, affordances, waypoints, footprints, and optional
  object-category priors.
- The prebuilt semantic map must not include movable object instances, hidden
  target lists, acceptable destination sets, or `is_misplaced` labels.
- Runtime movable objects remain `observed_*` handles created by `observe` or a
  camera-model policy from local FPV evidence.
- Grasp maps, grasp pose caches, IK, collision checking, and execution are owned
  by the external manipulation backend. Roboclaws records their provenance but
  does not standardize them in this phase.

## Public Contract Changes

### `metric_map`

Return a `real_robot_map_bundle_v1` style payload while preserving existing
public/private boundaries:

- `frame_id`, default `map`;
- `map_id` and `map_version`;
- `resolution_m`;
- `origin` as `{x, y, yaw}`;
- `width`, `height`, and occupancy semantics for unknown/free/occupied values;
- optional `occupancy_grid_artifact` path for YAML/image or JSON debug output;
- `robot_pose` as a pose in `frame_id`;
- `inspection_waypoints` as PoseStamped-like rows:
  `waypoint_id`, `frame_id`, `x`, `y`, `yaw`, `room_id`, `label`,
  `visited`, and `purpose`.

The simulator may derive this from MolmoSpaces geometry or current waypoint
fixtures, but the response must not expose movable object locations.

### `fixture_hints`

Treat this as the static fixture semantic map:

- rooms with labels and optional polygons;
- fixed fixtures/receptacles with `fixture_id`, category/name, room, affordances,
  optional footprint, optional pose, and optional manipulation frame;
- waypoint links such as `preferred_inspection_waypoint_id` or
  `preferred_manipulation_waypoint_id`;
- `fixture_hint_mode=room_only` remains the default;
- `exact_fixtures` remains an explicit easier mode and must be recorded.

Do not include runtime `observations` inside the prebuilt static map. Runtime
observations belong in `agent_view.raw_fpv_observations`,
`visible_object_detections`, camera-model policy evidence, or a future explicit
observed-object store.

### Navigation Responses

For `navigate_to_waypoint`, `navigate_to_object`, and
`navigate_to_receptacle`, return navigation evidence fields:

- `navigation_backend`: `api_semantic`, `sim_planner`,
  `agibot_gdk_normal_navi`, or `blocked_capability`;
- `primitive_provenance`, using existing provenance vocabulary;
- `goal_pose` when a map pose is known;
- `pose_source`: `inspection_waypoint`, `fixture_semantic_map`,
  `latest_observation`, `operator_annotation`, or `unavailable`;
- `staleness_s` and confidence/covariance when the goal comes from perception;
- `requires_reobserve` when a dynamic object pose is too stale or unavailable;
- failure fields for stale references, missing pose, or blocked capability.

In this phase, semantic simulator navigation must continue to report
`api_semantic`; it must not pretend to be Nav2 execution.

### Policy Views And Report Views

Separate policy input from report/debug artifacts:

- policy view may include FPV, map metadata, navigation status, fixture hints,
  and robot-local detections;
- policy view must not include chase camera images;
- report view may include chase/sim third-person images, but must label them as
  `report_only_simulation_view`;
- checkers should reject artifacts that claim real-robot readiness while
  exposing chase imagery as policy input.

## Implementation Sketch

- Add map bundle helpers in the Molmo cleanup contract layer rather than a new
  top-level maps package unless duplication appears.
- Extend `RealWorldCleanupContract.metric_map()` and `fixture_hints()` to emit
  the new fields while keeping backward-compatible keys where practical.
- Extend navigation response construction in `RealWorldCleanupContract` to add
  backend/provenance/pose-source fields.
- Add a `Real-Robot Readiness` section to cleanup reports summarizing map shape,
  fixture semantic map scope, policy-view safety, navigation provenance,
  manipulation provenance, and blocked capabilities.
- Extend `scripts/check_molmo_realworld_cleanup_result.py` with opt-in checks
  for real-robot contract alignment.
- Update `skills/molmo-realworld-cleanup/SKILL.md` to say the agent should use
  static fixture semantics plus runtime observations, and that chase views are
  report-only.

## Non-Goals

- Do not connect to a live ROS graph.
- Do not implement `Nav2Backend` or send `NavigateToPose` actions.
- Do not implement EasyNav support.
- Do not add a generic `robot_task_v1` contract.
- Do not standardize the external grasp map/grasp cache format.
- Do not make raw FPV object inference successful; preserve existing perception
  modes and provenance.
- Do not remove AI2-THOR debug/oracle tools from their existing simulation-only
  surfaces; only keep them out of the real-world cleanup contract.

## Acceptance Criteria

- `metric_map` includes Nav2-compatible map metadata and PoseStamped-like
  inspection waypoints.
- `fixture_hints` represents a static fixture semantic map without small movable
  object instances or private scoring truth.
- `observe` remains robot-local and does not expose target receptacles,
  acceptable destination sets, generated mess truth, or `is_misplaced`.
- Navigation responses expose backend/provenance/pose-source fields and keep
  semantic simulator navigation labeled `api_semantic`.
- `run_result.json` and `report.html` render a Real-Robot Readiness section.
- Checker tests can require the real-robot alignment fields and can reject chase
  imagery in policy input.
- Existing ADR-0003 cleanup tests and report/checker regressions continue to
  pass.

## Verification Plan

- Focused unit tests for `RealWorldCleanupContract.metric_map()`,
  `fixture_hints()`, and navigation response metadata.
- Report tests for the Real-Robot Readiness section and chase report-only label.
- Checker tests for required map metadata, static fixture semantic map scope,
  no oracle leakage, and provenance honesty.
- Synthetic cleanup harness run with the checker alignment flag enabled.
- Optional MolmoSpaces subprocess run with robot views enabled to prove the
  report labels chase/map/FPV correctly without claiming real Nav2 execution.

## Follow-Up Phases

1. **Nav2 adapter phase:** implement a `Nav2Backend` or adapter that resolves
   waypoints to poses and calls Nav2 `NavigateToPose` or `NavigateThroughPoses`,
   with mock action tests before real ROS graph tests.
2. **Real-robot navigation dry run:** load a prebuilt map and fixture semantic
   map, sweep waypoints, record FPV observations, and validate observed-handle
   lifecycle without pick/place.
3. **Manipulation integration phase:** accept external grasp/manipulation
   backend results and bind them to observed handles, fixture targets, and
   cleanup primitive provenance.

## Risks

- Nav2 has mature occupancy-grid, costmap, and action interfaces, but no single
  household semantic-map standard. Roboclaws should define a small fixture
  semantic layer and project only navigation-relevant semantics into future Nav2
  costmap/route plugins.
- Humanoid navigation may need footstep, posture, whole-body reachability, and
  manipulation-frame constraints that a 2D occupancy grid cannot express.
- Object-handle association from FPV will be noisy on real robots; every dynamic
  object pose must carry source, confidence, and staleness instead of being
  treated as ground truth.
- Prebuilt static maps can go stale. Runtime local costmaps and observations
  must remain separate dynamic layers.
- Simulation success may still overstate real capability unless every artifact
  records whether navigation and manipulation were semantic, simulated, or real
  planner-backed.
