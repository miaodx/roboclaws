# Agibot G2 Cleanup Support Pilot

**Status:** First SDK-runner backend slice implemented 2026-05-21; real hardware
execution still unrun
**Created:** 2026-05-19
**Source:** grill-with-docs session on Agibot G2 GDK docs, local
`vendors/agibot/app` examples, and `docs/plans/real-robot-nav2-cleanup-pilot.md`
**Workflow:** Pre-GSD plan. Ingest into `.planning/` before implementation.

## Problem

The current real robot cleanup design was shaped around ROS 2/Nav2 map bundles
and direct Nav2 actions. That is a good path for Nav2-backed robots, but Agibot
G2 exposes a higher-level GDK surface: map selection, SLAM/localization state,
camera access, and PNC navigation primitives such as `normal_navi` and
`relative_move`.

Treating Agibot G2 as if it were a Nav2 backend would leak the wrong abstraction
into agent-facing contracts. The Cleanup Agent should not learn Agibot-specific
tools, GDK map ids, relocalization commands, or raw PNC primitives. It should
continue to use the shared cleanup navigation and perception tools while reports
show the Agibot backend evidence clearly.

The first useful Agibot milestone is still a Navigation + Perception Pilot:
prove public navigation goals and robot-local observations on a real G2, while
physical manipulation remains blocked.

## Goal

Extend `real_robot_cleanup_v1` so Agibot G2 can be a backend variant beside
Nav2-backed robots:

- Keep the agent-facing public tool shape stable: `metric_map`,
  `fixture_hints`, `observe`, `navigate_to_waypoint`, `navigate_to_room`,
  `navigate_to_receptacle`, `navigate_to_object`,
  `navigate_to_visual_candidate`, and blocked manipulation tools.
- Generate Agibot agent map context from an operator-authored Agibot GDK Map
  Context, not from a required Nav2 map bundle.
- Let operators capture robot views and fill public map semantics, including
  multiple rooms, fixtures, and inspection waypoints.
- Verify public waypoints through GDK PNC before treating them as hardware-ready.
- Execute existing navigation tools through Agibot GDK PNC without adding
  Agibot-specific agent-facing API names.
- Preserve honest evidence in reports: map/localization gates, waypoint
  verification, backend/provenance labels, local nudge substeps, and failure
  handoff.

## Decisions Locked

- Agibot G2 remains a Backend Variant under `real_robot_cleanup_v1`; do not add
  `agibot_g2_cleanup_v1` unless the public tool shape or safety policy diverges.
- `real_robot_cleanup_v1` should describe a shared physical robot cleanup pilot
  boundary, with metadata equivalent to `backend=physical_robot` and a backend
  variant set such as `nav2_ros2` and `agibot_gdk`.
- `metric_map()` is backend-agnostic agent input. It may contain public rooms,
  fixtures, waypoints, driveable links, reachability status, and preview
  artifacts, but not backend variant metadata, Agibot map ids/names, current-map
  evidence, raw GDK map data, or PNC internals.
- Agibot G2 uses an Agibot GDK Map Context plus Cleanup Map Semantics as its
  Navigation Map Artifact. A Nav2 Map Artifact is not required unless a real
  Agibot-to-Nav2 bridge is later proven.
- Operator-Recorded Waypoints are the first-pilot source of Agibot public
  navigation points. One map context may contain multiple waypoints for
  different rooms, fixtures, and observation poses.
- A waypoint is hardware-ready only after PNC verification. Verification is an
  operator preparation action, not an agent-facing cleanup tool.
- Agibot PNC waypoint verification evidence should use
  `navigation_backend=agibot_gdk`,
  `primitive_provenance=agibot_gdk_normal_navi`, and normalized
  `reachability_status` values: `verified`, `blocked`, or `timeout`.
- Agibot runtime `observe()` defaults to `head_color` as the Policy Observation
  Camera. Other cameras may be captured for report/debug artifacts.
- `adjust_camera` may appear in the first map-build tool boundary, but real G2
  camera motion remains `blocked_capability` or a no-op with explicit evidence
  until bounded camera control is proven.
- Before an agent run starts, an Operator Localization Gate must confirm the
  selected map, G02 Pad relocalization, and localization readiness.
- Before autonomous motion starts, an Operator Run Enablement Gate must confirm
  that the robot may run within the allowed tool boundary. This is a run-level
  gate, not per-action human approval.
- Manipulation remains blocked: `pick`, `place`, `place_inside`,
  `open_receptacle`, and `close_receptacle` return structured
  `blocked_capability`.
- Navigation failure, local-motion failure, map mismatch, or missing
  localization enters Human Takeover Stop. The first pilot should not try hidden
  fallback waypoints, unverified goals, map switching, relocalization, or extra
  local nudges.
- Bounded Local Nudge is backend-internal only. It is not a new agent-facing
  tool and should not replace waypoint navigation as the primary route
  mechanism.
- Toward-Object Nudge may replace the simulator-style near-object approach after
  a waypoint-resolved object navigation call, but it remains small, bounded, and
  backed only by Agibot `relative_move` simple-stop behavior.

## GDK Findings

- `Pnc.normal_navi(NaviReq)` accepts a map-frame target and requires G02 Pad
  relocalization before execution. Use this for verified waypoint navigation.
- `Pnc.relative_move(NaviReq)` accepts a `base_link` relative move and is
  documented as simple obstacle stop without obstacle avoidance. Use only for
  bounded internal nudge substeps near verified waypoints.
- `Pnc.move_chassis(Twist)` is a low-level velocity-control primitive. Keep it
  operator/debug-only for the first pilot.
- PNC task state exposes terminal states including canceled, failed, and
  success. Runtime adapters should poll task state, timeout, cancel where
  possible, and record final state evidence.
- `Map.get_curr_map()` and `Map.get_all_map()` can support operator/report map
  evidence. `switch_map()` and `remove_map()` are not agent capabilities.
- SLAM pose/localization APIs can provide operator/report evidence. The agent
  should not own relocalization.
- Camera APIs expose multiple robot cameras. Runtime policy observation should
  use `head_color`; all-camera capture is an authoring/report helper.

## Contract Shape

Agent-facing `metric_map()` output:

- `schema="real_robot_map_bundle_v1"` for shared real-robot map projection
  compatibility.
- Public rooms, fixture ids/labels/categories, public inspection waypoints, and
  optional driveable links.
- Waypoint fields: id, frame id, x/y/yaw, room id, fixture id, label, purpose,
  source, visited flag, optional capture artifact, and public reachability
  status.
- No Agibot backend labels, GDK map id/name, PNC verification payload, or raw
  current-map evidence.

Operator/report evidence:

- Completed Agibot map context JSON, including GDK map source and captured robot
  pose.
- Captured camera images for map-context authoring and report review.
- Waypoint verification payloads with map check, task states, timeout, final
  state, `navigation_backend=agibot_gdk`, and
  `primitive_provenance=agibot_gdk_normal_navi`.
- Runtime localization gate and run enablement gate evidence.
- Any Bounded Local Nudge substeps with
  `primitive_provenance=agibot_gdk_relative_move` and explicit simple-stop,
  no-avoidance safety model.

Tool behavior:

- `navigate_to_waypoint` resolves the public waypoint id to a PNC-Verified
  Waypoint and executes `Pnc.normal_navi`.
- `navigate_to_room` resolves a room-level goal to a verified public waypoint.
- `navigate_to_receptacle` resolves a fixture to its preferred verified public
  waypoint. It may be used for inspection even when no object is held and must
  report `manipulation_ready=false`.
- `navigate_to_object` and `navigate_to_visual_candidate` may execute only when
  the object/candidate resolves to a verified public waypoint. They may include
  a bounded Toward-Object Nudge substep after successful waypoint navigation.
- Unverified, blocked, unresolved, or missing waypoints return
  `blocked_capability`.
- Map mismatch, missing localization gate, or missing run enablement gate return
  `blocked_capability`.
- `observe` returns `head_color` policy camera evidence by default.

## Implementation Phases

1. **Agibot Docs And Example Mirror**
   Keep the Agibot GDK 2.6.3 docs and relevant example code under
   `vendors/agibot/` so implementation decisions can cite local source
   material. Keep these files vendored evidence, not runtime package code.

2. **Map Context Capture Script**
   Add or harden a script that runs on the Agibot GDK machine, records current
   map evidence, SLAM pose, and camera images, and creates or updates an
   `agibot_gdk_map_context_authoring_v1` JSON file. The script should support
   repeated captures so an operator can mark multiple waypoints.

3. **Human Semantic Authoring Path**
   Define the operator-filled fields for rooms, fixtures, fixture categories,
   fixture footprints or poses, waypoint labels, waypoint purposes, and optional
   capture links. Treat incomplete TODO fields as invalid for generation.

4. **Metric Map Projection Generator**
   Convert completed Agibot context JSON into `metric_map.json`,
   `fixture_hints.json`, `agent_view.json`, and a semantic preview image.
   The generated agent view must remain backend-agnostic and must not include
   Agibot map source or PNC verification internals.

5. **Waypoint PNC Verification Script**
   Add a real-hardware script that requires an explicit `--yes`, checks the
   current GDK map against the selected context, sends `Pnc.normal_navi` goals,
   polls task state, cancels on timeout where possible, and writes normalized
   verification evidence into the authoring context.

6. **Agibot Backend Adapter**
   Add a mockable Agibot backend adapter that implements the existing
   `navigate_to_*` semantics through verified public waypoints and GDK PNC.
   The adapter should expose no raw GDK primitive tools to the agent.

7. **Runtime Gates And Failure Handling**
   Implement the Operator Localization Gate, Operator Run Enablement Gate, map
   mismatch checks, timeout/cancel evidence, and Human Takeover Stop outcomes.
   Failure should stop at the failed state and wait for human takeover.

8. **Observation And Report Integration**
   Wire Agibot `observe()` to the `head_color` policy camera and include
   captured authoring images, runtime observations, waypoint verification, and
   backend provenance in the cleanup report. Debug cameras should stay report
   artifacts, not policy inputs.

9. **Profile And Checker Alignment**
   Update `real_robot_cleanup_v1` metadata and contract tests so physical robot
   profile metadata no longer hard-codes `backend=ros2_nav2` or
   `nav2_action`-only provenance. The profile should allow both `nav2_ros2` and
   `agibot_gdk` backend variants while preserving the same public tool list.

10. **Physical Pilot Runbook**
    Document the Agibot operator workflow: relocalize on G02 Pad, capture
    context views, fill missing semantics, verify waypoints with PNC, generate
    agent map projection, run the navigation + perception pilot, and review the
    report. Include real-hardware warnings and note that scripts are unvalidated
    until exercised on a G2.

## Implementation Evidence

2026-05-21 ADR-0131 / SDK ADR-0002 first slice:

- Added `vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py`, a standalone
  SDK runner for three semantic stages: `agent-view`, `observe`, and
  `navigate-waypoint`.
- Added `roboclaws/molmo_cleanup/agibot_sdk_runner.py`, a subprocess adapter and
  physical Agibot pilot runner that keeps Roboclaws on `real_robot_cleanup_v1`
  while the SDK runner owns Agibot-specific evidence.
- Added `scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py` for a
  deterministic dry-run review artifact.
- Updated `real_robot_cleanup_v1` profile metadata from a Nav2-only backend to
  `physical_robot` with backend variants `nav2_ros2` and `agibot_gdk`.
- Generated the current human-review artifact at
  `output/agibot/adr0131-sdk-runner-dry-run/report.html`.

Subphase HTML reports:

- `output/agibot/adr0131-sdk-runner-dry-run/subphases/01-agent-view/report.html`
- `output/agibot/adr0131-sdk-runner-dry-run/subphases/02-observe/report.html`
- `output/agibot/adr0131-sdk-runner-dry-run/subphases/03-navigate-waypoint/report.html`

Current proof level: dry-run/rehearsal only. The observation and navigation
subphases intentionally render `blocked_capability` without `--execute`, so
these artifacts prove the CLI boundary, report shape, privacy boundary, and
movement gate, not physical PNC execution.

2026-05-28 Agibot pilot gap closure:

- Extended the `AgibotSDKRunnerAdapter` public-tool family beyond waypoint and
  receptacle navigation: `navigate_to_room`, `navigate_to_object`, and
  `navigate_to_visual_candidate` now resolve through verified public waypoints
  or return structured `blocked_capability` responses without exposing raw GDK
  primitives.
- Added explicit Operator Localization Gate and Operator Run Enablement Gate
  evidence before any real-movement path can pass `--execute` through the SDK
  runner. Missing gates stop at `blocked_capability` / Human Takeover Stop
  evidence before importing or calling `agibot_gdk`.
- Wired the Isaac scene-index cleanup scenario path into public fixture hints
  for map-bundle runs so scene-index receptacles can route cleanup without
  leaking private target truth.

2026-05-28 MolmoSpaces/G2 perception comparison grid:

- Added a first-class apple-to-apple grid surface for the G2-adjacent
  MolmoSpaces cleanup comparison:
  `just molmo::apple2apple-grid dry-run`.
- The grid contains one offline Runtime Metric Map setup row plus 12 cleanup
  rows across two map modes (`online`, `offline`), three live-agent routes
  (`codex-api-router`, `claude-kimi`, `claude-mimo-omni`), and two perception
  lanes (`camera-labels` with `visual_grounding=grounding-dino`, and
  `camera-raw` / RAW_FPV direct input with the same Grounding DINO grounding
  boundary).
- Dry-run evidence was generated at
  `output/molmo/apple2apple-grid-0528-dry-run/apple2apple_test_grid.html` and
  `output/molmo/apple2apple-grid-0528-just-dry-run/apple2apple_test_grid.html`.
  These artifacts prove command coverage and provider/profile pinning, not live
  provider execution or real G2 hardware behavior.

## Non-Goals

- Do not claim physical cleanup.
- Do not implement physical manipulation.
- Do not expose Agibot-specific navigation tool names to the Cleanup Agent.
- Do not expose `relative_move`, `move_chassis`, map switching, map removal, or
  relocalization as agent-facing cleanup tools.
- Do not require Agibot G2 to export or import Nav2 maps for the first pilot.
- Do not put Agibot map ids, current-map evidence, or raw GDK map data in the
  agent-facing `metric_map()`.
- Do not use unverified waypoints in runtime navigation unless an explicit
  operator development override exists.
- Do not hide navigation failures by retargeting to fallback waypoints.
- Do not use all available cameras as policy observations by default.

## Acceptance Criteria

- Agibot GDK docs/examples are mirrored under `vendors/agibot/` for local
  reference.
- An operator can capture Agibot map context views and append multiple
  waypoints to one context JSON.
- The metric map generator rejects incomplete TODO context and emits
  backend-agnostic `metric_map.json`, `fixture_hints.json`, `agent_view.json`,
  and a semantic preview.
- Agent-facing Agibot metric map output contains no backend labels, no Agibot
  map source, and no PNC verification payload.
- A waypoint verification script records normalized statuses and canonical
  backend/provenance labels after `Pnc.normal_navi` checks.
- Agibot runtime navigation blocks missing, unverified, blocked, unresolved, or
  map-mismatched goals.
- Existing public navigation tools resolve to verified waypoints and execute via
  GDK PNC without exposing new Agibot agent tools.
- `observe()` uses `head_color` as the policy observation camera.
- First G2 map-build runs use robot-local `head_color` / RAW_FPV evidence with
  `camera-labels` plus real External Visual Grounding Service output as the
  primary perception lane; `camera-raw` remains a comparison/fallback lane.
- `world-labels` and `visual_grounding=sim` remain simulator/control evidence,
  not G2 readiness evidence.
- Manipulation tools remain blocked and report that physical cleanup is not
  ready.
- Reports distinguish top-level `agibot_gdk_normal_navi` navigation evidence
  from any internal `agibot_gdk_relative_move` nudge substeps.
- Mock tests cover map projection, waypoint verification evidence, blocked
  unverified waypoints, gate failures, and successful mocked GDK navigation.
- Real Agibot hardware validation remains explicitly marked unrun until tested
  on a G2.

## Open Implementation Choices

- Exact runtime packaging and command recipe for the Agibot pilot.
- Whether the Agibot backend adapter is integrated directly into the existing
  Molmo cleanup MCP server first or introduced as a separate physical pilot
  runner with the same contract.
- The maximum distance, yaw, and timeout limits for Bounded Local Nudge and
  Toward-Object Nudge. Defaults should be conservative and operator-configured.
- The minimum localization confidence/state values accepted by the Operator
  Localization Gate once real G2 runs expose stable field values.
