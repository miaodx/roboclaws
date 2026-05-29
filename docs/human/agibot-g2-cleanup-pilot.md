# Agibot G2 Cleanup Pilot

This runbook is for the Agibot G2 Navigation + Perception Pilot. It is not a
physical cleanup proof: the first accepted target is `semantic-map-build`,
navigation and observation may execute through the Agibot SDK runner, and
physical manipulation stays `blocked_capability`.

## Preconditions

- Run on a trusted local workstation or the Agibot GDK machine, not hosted CI.
- A human operator owns the robot-side E-stop, manual stop, and workspace
  safety boundary.
- The robot is on the intended map in G02 Pad and has been relocalized.
- The repo-local `.venv/` is synced with dev dependencies:

```bash
uv sync --extra dev
```

- If a live Codex or Claude comparison run is involved, configure repo-local
  `.env` keys as described in [local-runtime.md](local-runtime.md). Do not paste
  keys into logs or reports.
- Check the current network before any OpenClaw or coding-agent workflow:

```bash
just dev::network-status
```

On the work network, OpenClaw is blocked. Codex is allowed only through
repo-local `.env` routes such as `XM_LLM_API_KEY`, or explicit
`CODEX_BASE_URL` plus `CODEX_API_KEY`.

## Capture Map Context

Capture map, pose, and camera evidence on the Agibot GDK machine:

```bash
.venv/bin/python scripts/agibot/capture_map_context_views.py \
  --output-dir output/agibot/map-context/<stamp> \
  --cameras head_color
```

For the minimal-map path, the completed context must include safety bounds plus
generated or free-space exploration candidates. It must not require
hand-authored rooms, fixtures, or semantic waypoints.

Generate the Roboclaws agent view and preview locally:

```bash
.venv/bin/python scripts/agibot/generate_metric_map_from_context.py \
  output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  --output-dir output/agibot/map-context/<stamp>/generated_metric_map
```

Review `agent_view.json`, `metric_map.json`, `fixture_hints.json`, and
`semantic_preview.png`. The agent-facing map must not expose raw Agibot map
source, GDK internals, or PNC verification payloads.

## Verify Waypoints

Waypoint verification moves the robot. Run it only after the operator confirms
the map, localization, safety bounds, and stop access:

```bash
.venv/bin/python scripts/agibot/verify_waypoints_with_pnc.py \
  output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  --all \
  --yes
```

The verification evidence should normalize candidate status to `verified`,
`blocked`, or `timeout`, with `navigation_backend=agibot_gdk` and
`primitive_provenance=agibot_gdk_normal_navi` for successful PNC evidence.

## Dry-Run Report

Before enabling movement, run the public task route in dry-run mode:

```bash
just task::run semantic-map-build direct camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  waypoint_id=<verified_waypoint_id> \
  output_dir=output/agibot/semantic-map-build-dry-run
```

This should produce `run_result.json`, `trace.jsonl`, subphase reports, and
`report.html`. The report is expected to show dry-run movement-gate blocks,
visible policy decisions, skipped waypoint reasoning, and blocked manipulation.

For the Codex-controlled semantic-map-build lane, use the Agibot-specific MCP
server route:

```bash
just task::run semantic-map-build codex camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  output_dir=output/agibot/semantic-map-build-codex-dry-run \
  visual_grounding=grounding-dino
```

This route launches the Docker-backed Codex runtime against the
`agibot_semantic_map_build` MCP server and writes `run_result.json`,
`trace.jsonl`, `runtime_metric_map.json`, and `report.html`. For
`camera-labels`, the report records `perception_mode=camera_model_policy`, the
requested visual-grounding pipeline, and explicit no-live-camera failure
evidence instead of fabricating labels. The route exists, has mocked contract
coverage, and has passed a live Codex fixture dry-run at
`output/agibot/semantic-map-build-codex-live-validation/0529_1849/seed-7/`.
That artifact records `evidence_lane=camera-labels`,
`perception_mode=camera_model_policy`,
`visual_grounding_pipeline_id=grounding-dino`, and the explicit
`live_camera_capture_not_enabled` failure boundary for dry-run camera evidence.
Real G2 hardware validation is still a separate unrun gate.

For a cleanup-shaped contract rehearsal, use the same backend route while
keeping manipulation blocked:

```bash
just task::run household-cleanup direct camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  waypoint_id=<verified_waypoint_id> \
  output_dir=output/agibot/household-cleanup-dry-run
```

Do not describe this as physical cleanup success.

## Movement Run

Set `real_movement_enabled=true` only after the operator confirms the run-level
gate. The first hardware target is `semantic-map-build`:

```bash
just task::run semantic-map-build direct camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  waypoint_id=<verified_waypoint_id> \
  output_dir=output/agibot/semantic-map-build-hardware \
  real_movement_enabled=true
```

The SDK-backed direct CLI boundary remains the smallest hardware bring-up path.
The Codex MCP route is now available for `semantic-map-build` with
`backend=agibot_gdk`, but do not present mocked contract tests, direct-run
reports, or dry-run Codex reports as real G2 hardware evidence. A hardware
acceptance claim requires the Codex route to run against the actual G2 with the
operator gates enabled and the report label honest.

## Review Checklist

Accept the pilot only when `report.html` and `run_result.json` show:

- `cleanup_profile=real_robot_cleanup_v1`
- `backend_variant=agibot_gdk`
- `physical_navigation_pilot=true`
- `physical_cleanup_ready=false`
- `agent_view.policy_view.policy_observation_camera=head_color`
- navigation evidence is `agibot_gdk_normal_navi` for real movement or
  `blocked_capability` for dry-run/gate failures
- `cleanup_policy_trace.agent_reasoning_visible=true`
- visited and skipped public waypoints include decision, progress, and reason
- manipulation tools remain blocked
- any failure enters Human Takeover Stop evidence instead of hidden fallback

Real Agibot hardware validation remains unrun until this checklist is satisfied
on a G2 with operator-supervised movement.
