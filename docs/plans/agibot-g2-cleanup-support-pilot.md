# Agibot G2 Cleanup Support Pilot

**Status:** First SDK-runner backend slice implemented 2026-05-21; real hardware
execution still unrun
**Created:** 2026-05-19
**Source:** grill-with-docs session on Agibot G2 GDK docs, local
`vendors/agibot_sdk/` docs/examples, and
`docs/plans/real-robot-nav2-cleanup-pilot.md`
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
- Generate Agibot agent map context from a minimal Agibot GDK map context, not
  from a required Nav2 map bundle or hand-authored semantic map.
- Support a minimal-map path from Agibot occupancy/free-space artifacts where
  semantic-map-build enriches rooms, fixtures, and observation targets through
  public robot-local evidence.
- Let operators choose maps, relocalize, set safety bounds, and approve run
  gates, while `semantic-map-build` creates public map semantics automatically
  from robot-local observations.
- Verify public or generated navigation targets through GDK PNC before treating
  them as hardware-ready.
- Execute existing navigation tools through Agibot GDK PNC without adding
  Agibot-specific agent-facing API names.
- Preserve honest evidence in reports: map/localization gates, waypoint
  verification, backend/provenance labels, local nudge substeps, and failure
  handoff.
- Use the existing public task grammar for hardware runs, e.g.
  `semantic-map-build` with `driver=codex` and `backend=agibot_gdk`; do not add
  an Agibot-only public task taxonomy.

## Decisions Locked

- Agibot G2 remains a Backend Variant under `real_robot_cleanup_v1`; do not add
  `agibot_g2_cleanup_v1` unless the public tool shape or safety policy diverges.
- `real_robot_cleanup_v1` should describe a shared physical robot cleanup pilot
  boundary, with metadata equivalent to `backend=physical_robot` and a backend
  variant set such as `nav2_ros2` and `agibot_gdk`.
- Agibot G2 is selected as a backend variant such as `backend=agibot_gdk` under
  the existing `just task::run <task> <driver> ...` command grammar. It is not
  a separate public task name.
- `metric_map()` is backend-agnostic agent input. In rich-map mode it may
  contain public rooms, fixtures, waypoints, driveable links, reachability
  status, and preview artifacts. In minimal-map mode it may start from
  occupancy/free-space geometry, pose/frame metadata, safety bounds, and
  generated exploration candidates. It must not expose backend variant metadata,
  Agibot map ids/names, current-map evidence, raw GDK map data, or PNC internals.
- Agibot G2 uses an Agibot Minimal Map Context as its Navigation Map Artifact.
  A Nav2 Map Artifact and a hand-authored cleanup semantic map are not required
  unless explicitly selected for a comparison run.
- System-generated exploration candidates derived from public free-space
  geometry are the first-pilot navigation source. The agent may select or order
  those candidates; it may not invent arbitrary physical coordinates.
- A waypoint or generated exploration candidate is hardware-ready only after
  PNC verification or an equivalent backend reachability gate. Verification is
  an operator/backend preparation action, not an agent-facing cleanup tool.
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
  gate, not per-action human approval. After the gate, Codex should control
  task-level tool choice and print or record its reasoning/progress; humans
  remain safety supervisors through robot-side obstacle stop and manual
  emergency stop.
- Manipulation remains blocked: `pick`, `place`, `place_inside`,
  `open_receptacle`, and `close_receptacle` return structured
  `blocked_capability`.
- Navigation failure, local-motion failure, map mismatch, or missing
  localization enters Human Takeover Stop. Robot-side obstacle stops and human
  emergency stops also enter Human Takeover Stop. The first pilot should not try
  hidden fallback waypoints, unverified goals, map switching, relocalization,
  arbitrary coordinates, or extra local nudges.
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
- Rich-map mode: public rooms, fixture ids/labels/categories, public inspection
  waypoints, and optional driveable links, only for explicit comparison/dev
  runs.
- Minimal-map mode: occupancy/free-space metadata, current pose/frame context,
  safety bounds, and generated exploration candidates. Runtime rooms, fixture
  candidates, and observed objects are added only from public observation
  evidence.
- Waypoint fields: id, frame id, x/y/yaw, room id, fixture id, label, purpose,
  source, visited flag, optional capture artifact, and public reachability
  status.
- No Agibot backend labels, GDK map id/name, PNC verification payload, or raw
  current-map evidence.

Operator/report evidence:

- Completed or minimal Agibot map context JSON, including GDK map source,
  captured robot pose, safety bounds, and any generated exploration candidates.
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
- Minimal-map generated exploration candidates should first be represented as
  `generated_*` waypoint entries and use `navigate_to_waypoint`. Add a dedicated
  `navigate_to_exploration_candidate` tool only if simulator evidence shows
  waypoint projection is ambiguous or unsafe. Either way, the target must resolve
  to a backend-verified navigation target before executing `Pnc.normal_navi`.
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
   `vendors/agibot_sdk/` so implementation decisions can cite local source
   material. Keep these files vendored evidence, not runtime package code.

2. **Minimal Map Context Capture Script**
   Replace the old human semantic authoring flow with a script that runs on the
   Agibot GDK machine and records current map evidence, occupancy/free-space
   artifacts, frame/origin/resolution metadata, robot pose/localization
   evidence, camera images for report review, and operator safety bounds. The
   output is an Agibot Minimal Map Context and must not require hand-authored
   rooms, fixtures, fixture labels, or manually tagged semantic waypoints.

2A. **Minimal Map Context Path**
   Generate safe exploration candidates from Agibot occupancy/free-space
   artifacts, current pose, frame metadata, and operator safety bounds. Project
   those candidates as generated waypoint entries for `navigate_to_waypoint`.

3. **Remove Human Semantic Authoring Path**
   Remove the Agibot runtime path that requires operators to fill rooms,
   fixtures, fixture categories, fixture footprints, and manually tagged
   semantic waypoints. Do not preserve the old Agibot rich semantic authoring
   route for backward compatibility.

4. **Metric Map Projection Generator**
   Convert an Agibot Minimal Map Context into `metric_map.json`,
   `fixture_hints.json`, `agent_view.json`, and map preview artifacts.
   `fixture_hints` may be empty before observation-derived anchors exist. The
   generated agent view must remain backend-agnostic and must not include
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
   runtime observations, waypoint verification, visual-grounding evidence or
   visible visual-grounding failure evidence, and backend provenance in the
   report. Debug cameras should stay report artifacts, not policy inputs.

9. **Profile And Checker Alignment**
   Update `real_robot_cleanup_v1` metadata and contract tests so physical robot
   profile metadata no longer hard-codes `backend=ros2_nav2` or
   `nav2_action`-only provenance. The profile should allow both `nav2_ros2` and
   `agibot_gdk` backend variants while preserving the same public tool list.

10. **Codex-Driven Physical Pilot Runbook**
    Document the Agibot operator workflow: relocalize on G02 Pad, capture a
    minimal map context, set safety bounds, generate and approve exploration
    candidates, run the Codex-driven navigation + perception pilot, and review
    the report. Include real-hardware warnings and note that physical
    manipulation remains blocked.

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

2026-05-29 Agibot minimal-map context gap closure:

- Updated `scripts/agibot/generate_metric_map_from_context.py` so an Agibot
  context with safety bounds and generated/free-space exploration samples can
  emit `metric_map.json`, `fixture_hints.json`, `agent_view.json`, and a preview
  without hand-authored rooms, fixtures, or semantic waypoints.
- Mirrored the same minimal projection in the vendored SDK runner
  `agent-view` export. Generated exploration candidates are projected as public
  `inspection_waypoints` with `waypoint_source=generated_exploration_candidate`
  and `purpose=minimal_map_exploration`, preserving the existing
  `navigate_to_waypoint` tool path.
- Minimal Agibot Agent View now marks `mode=minimal`, leaves `rooms` and
  `fixture_hints.rooms` empty before runtime observations, carries public
  safety bounds and candidate provenance, and still excludes Agibot map source,
  raw GDK/PNC evidence, and verification payloads.
- Focused mock verification now covers direct generator output, SDK-runner
  agent-view export, dry-run navigation to a generated candidate, existing rich
  context behavior, unverified-waypoint blocking, and physical pilot adapter
  regressions.

2026-05-29 Agibot public task routing slice:

- Added public `just task::run ... backend=agibot_gdk` routing for the existing
  `semantic-map-build` and `household-cleanup` tasks through
  `scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py`.
- The route requires `context_json=<agibot map context JSON>` and may pass
  `waypoint_id`, `run_dir`, `runner_python`, `runner_script`,
  `agibot_map_artifact_dir`, and `real_movement_enabled`. This keeps Agibot G2
  as a backend variant under the shared task grammar instead of adding an
  Agibot-only public task name.
- The routed `household-cleanup` shape still uses the Agibot Navigation +
  Perception Pilot artifact and keeps manipulation blocked; it is not a
  physical cleanup success claim.
- Focused route tests cover `semantic-map-build direct camera-labels
  backend=agibot_gdk`, cleanup-shaped direct routing, and the required
  `context_json` guard. At that direct-routing slice, Codex-driven task control
  remained a later acceptance layer; the later Codex Agibot semantic-map-build
  route slice adds the live MCP route without claiming hardware validation.

2026-05-29 Agibot pilot report trace slice:

- Extended the physical Agibot pilot `cleanup_policy_trace` with
  `agent_review_kind=agibot_navigation_perception_pilot_review`,
  `agent_reasoning_visible=true`, selected/skipped waypoint counts, and
  operator-review notes.
- Each pilot trace event now records the visible tool choice plus
  `decision`, `progress`, and `reason` fields for `observe_head_color`,
  `visit_public_waypoint`, `skip_public_waypoint`, and
  `block_manipulation` decisions. This makes dry-run movement-gate blocks and
  intentionally blocked physical manipulation reviewable in the shared cleanup
  report.
- Shared report rendering now shows the richer decision/progress/reason columns
  only when those fields are present, preserving the existing generic cleanup
  policy trace shape for non-Agibot reports.
- Focused verification:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_physical_agibot_pilot.py -q`,
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`,
  `./.venv/bin/ruff check roboclaws/molmo_cleanup/agibot_sdk_runner.py roboclaws/molmo_cleanup/report.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`,
  and `./.venv/bin/ruff format --check roboclaws/molmo_cleanup/agibot_sdk_runner.py roboclaws/molmo_cleanup/report.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`.
  This remains dry-run/report evidence, not real G2 hardware validation.

2026-05-29 Agibot G2 pilot runbook slice:

- Added `docs/human/agibot-g2-cleanup-pilot.md` and linked it from
  `docs/human/README.md`.
- The runbook covers operator map capture, minimal context projection,
  PNC waypoint verification, dry-run report review, movement enablement, and
  the acceptance checklist for `real_robot_cleanup_v1` on Agibot G2.
- It explicitly documented the then-current limitation that Agibot hardware
  routing was the SDK-backed direct CLI boundary behind `just task::run`, before
  the later Codex Agibot semantic-map-build route slice added the live MCP
  route. Real Codex provider and G2 hardware validation still must not be
  claimed from direct-run artifacts.

2026-05-29 mocked Agibot GDK navigation gate:

- Aligned this plan's vendored-doc path references with the actual SDK mirror at
  `vendors/agibot_sdk/`.
- Added a focused contract test that injects a fake `agibot_gdk` module into
  the SDK runner execute path and verifies successful `Pnc.normal_navi`
  evidence: `navigation_status=succeeded`,
  `navigation_backend=agibot_gdk`,
  `primitive_provenance=agibot_gdk_normal_navi`, and
  `pose_source=agibot_gdk_pnc_arrival`.
- Corrected SDK-runner navigation request evidence so dry-run requests render
  `sent=false` / `not_sent=true`, while mocked successful execution renders
  `sent=true` / `not_sent=false`.
- Added mocked timeout coverage for both the standalone waypoint verifier and
  the SDK runner execute path. Timeout artifacts now record positive
  cancellation evidence (`cancel_attempted`, `cancel_task_id`,
  `cancel_requested`, `cancel_error`) and final task state after cancel; the SDK
  runner calls `Pnc.cancel_task()` on timeout instead of only reporting the
  timed-out `Pnc.normal_navi` state.
- Tightened Human Takeover Stop readiness classification so runtime navigation
  failures such as timeout, PNC failure, `normal_navi` exception, map mismatch,
  and bounded local nudge failure require takeover evidence, while dry-run
  movement-gate blocks and unverified-waypoint refusals remain ordinary blocked
  capability outcomes.
- Added an execute-only current-map check to the SDK runner navigation path:
  when real movement is enabled, Roboclaws passes the Agibot context JSON to
  `navigate-waypoint`, the runner compares `Map.get_curr_map()` with
  `map_source`, and a mismatch returns `failure_type=map_mismatch` before
  `Pnc.normal_navi` is called.
- Focused verification:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/agibot/test_agibot_map_context_scripts.py -q`,
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_physical_agibot_pilot.py -q`,
  `./scripts/dev/run_pytest_standalone.sh tests/contract/agibot/test_agibot_map_context_scripts.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py -q`,
  `./.venv/bin/ruff check scripts/agibot/verify_waypoints_with_pnc.py vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py tests/contract/agibot/test_agibot_map_context_scripts.py`,
  `./.venv/bin/ruff check roboclaws/molmo_cleanup/agibot_sdk_runner.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`,
  `./.venv/bin/ruff check vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py roboclaws/molmo_cleanup/agibot_sdk_runner.py tests/contract/agibot/test_agibot_map_context_scripts.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`,
  `./.venv/bin/ruff format --check scripts/agibot/verify_waypoints_with_pnc.py vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py tests/contract/agibot/test_agibot_map_context_scripts.py`,
  `./.venv/bin/ruff format --check roboclaws/molmo_cleanup/agibot_sdk_runner.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`,
  and `./.venv/bin/ruff format --check vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py roboclaws/molmo_cleanup/agibot_sdk_runner.py tests/contract/agibot/test_agibot_map_context_scripts.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`.
  This is mocked SDK evidence, not real G2 hardware validation.

2026-05-29 Codex Agibot semantic-map-build route slice:

- Added an Agibot-specific `agibot_semantic_map_build` MCP server for
  `semantic-map-build` with `backend=agibot_gdk`. It exposes public map,
  fixture, navigation, observation, blocked camera/manipulation, and `done`
  tools backed by the Agibot SDK runner boundary.
- Added the live Codex runner wrapper
  `scripts/molmo_cleanup/run_live_codex_agibot_map_build.py` plus the public
  route `just task::run semantic-map-build codex <lane> backend=agibot_gdk
  context_json=...`. Non-Agibot `semantic-map-build codex` remains rejected
  until intentionally supported.
- The MCP `done` artifact now writes `run_result.json`, `trace.jsonl`,
  `runtime_metric_map.json`, and `report.html` with
  `agent_driven=true`, `mcp_server=agibot_semantic_map_build`, and
  `backend_variant=agibot_gdk`.
- The Agibot MCP artifact now carries the public evidence lane through the
  server. `camera-labels` records `perception_mode=camera_model_policy`, the
  requested visual-grounding pipeline, robot-local `head_color` RAW_FPV intent,
  and explicit no-live-camera/no-external-label failure evidence instead of
  implying camera labels existed in dry-run.
- Focused verification:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_physical_agibot_pilot.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`,
  `./.venv/bin/ruff check roboclaws/devtools/commands.py roboclaws/molmo_cleanup/agibot_map_build_mcp_server.py examples/molmo_cleanup/agibot_semantic_map_build_agent_server.py scripts/molmo_cleanup/run_live_codex_agibot_map_build.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py tests/contract/dev_tools/test_task_agent_just_recipes.py`,
  and `./.venv/bin/ruff format --check` over the same touched files.
- Live Codex fixture dry-run verification:
  `just task::run semantic-map-build codex camera-labels backend=agibot_gdk context_json=tests/fixtures/agibot_map_context.completed.json output_dir=output/agibot/semantic-map-build-codex-live-validation policy=codex_agibot_semantic_map_build_pilot visual_grounding=grounding-dino`
  produced `output/agibot/semantic-map-build-codex-live-validation/0529_1849/seed-7/`
  with `agent_driven=true`, `mcp_server=agibot_semantic_map_build`,
  `backend_variant=agibot_gdk`, `cleanup_status=physical_agibot_semantic_map_build_rehearsal`,
  `sweep_coverage_rate=1.0`, `evidence_lane=camera-labels`,
  `perception_mode=camera_model_policy`,
  `visual_grounding_pipeline_id=grounding-dino`,
  `camera_model_policy_evidence.private_truth_included=false`, and explicit
  `live_camera_capture_not_enabled` / `external_visual_grounding_not_invoked`
  failure evidence for the dry-run camera lane. `trace.jsonl` records Codex MCP
  calls to `metric_map`, `fixture_hints`, `navigate_to_waypoint`, `observe`, and
  `done`. Movement and live camera capture were disabled, so this is
  live-provider/fixture dry-run evidence; real G2 hardware validation remains
  unrun.
- The artifact checker now accepts this no-cleanup map-build shape only through
  an explicit semantic-sweep gate. Verification command:
  `./.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py output/agibot/semantic-map-build-codex-live-validation/0529_1849/seed-7/run_result.json --expect-backend agibot_gdk --expect-mcp-server agibot_semantic_map_build --require-agent-driven --require-camera-model-policy --expect-visual-grounding-pipeline grounding-dino --require-visual-grounding-failure --require-runtime-metric-map --require-semantic-sweep --min-generated-mess-count 0 --min-sweep-coverage 1.0 --allow-partial-cleanup`.

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
- Live local provider evidence was generated at
  `output/molmo/apple2apple-grid-0528-live-full-rows/apple2apple_test_grid.html`,
  with the machine-readable manifest at
  `output/molmo/apple2apple-grid-0528-live-full-rows/apple2apple_test_grid.json`.
  The offline rows used the Runtime Metric Map prior from
  `output/molmo/apple2apple-grid-0528-live-full/_offline-semantic-map-prior/0528_1457/seed-7/runtime_metric_map.json`.
  This is still MolmoSpaces/RBY1M simulation evidence, not real G2 hardware
  execution.
- Live row results for seed 7, 10 generated mess objects:

  | Map | Agent route | Perception lane | Row status | Private scorer result |
  | --- | --- | --- | --- | --- |
  | online | Codex API router | Grounding DINO labels | success | partial_success; 3/10 exact, 7/10 semantic, sweep 1.0 |
  | online | Codex API router | RAW_FPV direct | success | success; 7/10 exact, 8/10 semantic, sweep 1.0 |
  | online | Claude Code Kimi | Grounding DINO labels | success | partial_success; 3/10 exact, 7/10 semantic, sweep 1.0 |
  | online | Claude Code Kimi | RAW_FPV direct | success | success; 7/10 exact, 8/10 semantic, sweep 1.0 |
  | online | Claude Code MiMo v2 Omni | Grounding DINO labels | success | partial_success; 2/10 exact, 7/10 semantic, sweep 1.0 |
  | online | Claude Code MiMo v2 Omni | RAW_FPV direct | success | partial_success; 5/10 exact, 8/10 semantic, sweep 1.0 |
  | offline | Codex API router | Grounding DINO labels | success | partial_success; 3/10 exact, 7/10 semantic, sweep 1.0 |
  | offline | Codex API router | RAW_FPV direct | failed | no final report; 9 cleanup chains completed, then MCP transport failed before final `observe`/`done` |
  | offline | Claude Code Kimi | Grounding DINO labels | success | partial_success; 2/10 exact, 7/10 semantic, sweep 1.0 |
  | offline | Claude Code Kimi | RAW_FPV direct | success | success; 8/10 exact, 9/10 semantic, sweep 1.0 |
  | offline | Claude Code MiMo v2 Omni | Grounding DINO labels | success | partial_success; 2/10 exact, 7/10 semantic, sweep 1.0 |
  | offline | Claude Code MiMo v2 Omni | RAW_FPV direct | success | partial_success; 6/10 exact, 8/10 semantic, sweep 1.0 |

  The failed offline Codex RAW_FPV row is retained as a grid outcome, not
  omitted: `live_status.json` records `phase=failed`, `exit_status=1`, and
  `reason="cleanup MCP server exited with status -15"`; the agent's final
  message records 13/14 observed waypoints, 9 successful cleanup chains, and
  repeated HTTP transport failures to `127.0.0.1:18788/mcp`.

## Non-Goals

- Do not claim physical cleanup.
- Do not implement physical manipulation.
- Do not expose Agibot-specific navigation tool names to the Cleanup Agent.
- Do not expose `relative_move`, `move_chassis`, map switching, map removal, or
  relocalization as agent-facing cleanup tools.
- Do not require Agibot G2 to export or import Nav2 maps for the first pilot.
- Do not require human-authored Agibot room, fixture, fixture-label, or semantic
  waypoint tagging for the mainline hardware path.
- Do not keep the previous Agibot human semantic-map tagging implementation for
  backward compatibility.
- Do not put Agibot map ids, current-map evidence, or raw GDK map data in the
  agent-facing `metric_map()`.
- Do not use unverified waypoints in runtime navigation unless an explicit
  operator development override exists.
- Do not hide navigation failures by retargeting to fallback waypoints.
- Do not use all available cameras as policy observations by default.

## Acceptance Criteria

- Agibot GDK docs/examples are mirrored under `vendors/agibot_sdk/` for local
  reference.
- An operator can capture an Agibot Minimal Map Context without hand-tagging
  rooms, fixtures, or semantic waypoints.
- The metric map generator emits backend-agnostic `metric_map.json`,
  `fixture_hints.json`, `agent_view.json`, and preview artifacts from the
  minimal context; pre-observation `fixture_hints` may be empty.
- Agent-facing Agibot metric map output contains no backend labels, no Agibot
  map source, and no PNC verification payload.
- Generated exploration candidates are accepted, blocked, or timed out through
  normalized GDK PNC reachability evidence with canonical backend/provenance
  labels.
- Agibot runtime navigation blocks missing, unverified, blocked, unresolved, or
  map-mismatched goals.
- Existing public navigation tools resolve to verified generated waypoints and
  execute via GDK PNC without exposing new Agibot agent tools.
- `observe()` uses `head_color` as the policy observation camera.
- First G2 map-build runs use robot-local `head_color` / RAW_FPV evidence with
  `camera-labels` plus real External Visual Grounding Service output as the
  primary perception lane; `camera-raw` remains a comparison/fallback lane.
- The first Codex-driven hardware target is `semantic-map-build`. The code
  should support both `semantic-map-build` and a cleanup-shaped
  `household-cleanup` path for Agibot, but the cleanup-shaped path keeps
  manipulation blocked and does not claim physical cleanup success. Full
  `household-cleanup` is not the first hardware acceptance gate.
- The pilot report captures Codex-driven tool choices and progress/reasoning so
  the operator can review why each generated waypoint was visited or skipped.
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

## Implementation Defaults

- Runtime packaging and command recipe should reuse the existing public
  `just task::run <task> <driver> [lane] key=value...` facade with
  `backend=agibot_gdk`.
- The Agibot backend adapter should integrate into the existing cleanup MCP
  server while keeping the same public tool contract.
- The maximum distance, yaw, and timeout limits for Bounded Local Nudge and
  Toward-Object Nudge. Defaults should be conservative and operator-configured.
- The minimum localization confidence/state values accepted by the Operator
  Localization Gate once real G2 runs expose stable field values.
