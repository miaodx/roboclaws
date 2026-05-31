# Agibot G2 Codex A Acceptance

This runbook is the narrow acceptance path for **A: navigation + perception on
Agibot G2 through Codex**.

It proves that Docker-backed Codex can call the Agibot-backed MCP surface,
observe through the G2 `head_color` camera, and command one operator-approved
navigation waypoint through Agibot GDK PNC. It is not a physical cleanup proof.
Manipulation remains blocked.

For the broader Agibot pilot context, see
[Agibot G2 Cleanup Pilot](agibot-g2-cleanup-pilot.md).

## Acceptance Target

The accepted target is:

- public task: `semantic-map-build`
- driver: `codex`
- evidence lane: `camera-labels`
- backend: `agibot_gdk`
- MCP server: `agibot_semantic_map_build`
- policy: `codex_agibot_semantic_map_build_pilot`
- physical scope: one or more verified navigation waypoints plus live
  `head_color` observations

The run is accepted only when the hardware checker passes with
`--require-agibot-g2-hardware`.

## Preconditions

Run this on a trusted local workstation connected to the Agibot GDK machine, or
directly on the GDK machine. Do not run this in hosted CI.

A human operator must own:

- robot-side E-stop or manual stop
- workspace safety boundary
- G02 Pad map selection and relocalization
- operator localization and run-enablement gates

Prepare the repo environment:

```bash
uv sync --extra dev
set -a && source .env && set +a
just dev::network-status
```

On the work network, Codex must use repo-local `.env` routes such as
`XM_LLM_API_KEY`, or explicit `CODEX_BASE_URL` plus `CODEX_API_KEY`. Do not
paste keys into logs, reports, or docs.

## Prepare Map Context

Capture the live Agibot map, pose, and policy-camera evidence:

```bash
.venv/bin/python scripts/agibot/capture_map_context_views.py \
  --output-dir output/agibot/map-context/<stamp> \
  --cameras head_color
```

Before movement, complete
`output/agibot/map-context/<stamp>/agibot_map_context.completed.json` with the
operator gates:

```json
{
  "operator_localization_gate": {
    "selected_map_confirmed": true,
    "g02_pad_relocalized": true,
    "localization_ready": true,
    "operator": "<operator>",
    "confirmed_at": "<iso8601>"
  },
  "operator_run_enablement_gate": {
    "enabled": true,
    "scope": "session",
    "operator": "<operator>",
    "confirmed_at": "<iso8601>"
  }
}
```

Generate the agent-facing map artifacts:

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

At least one candidate must become `verified` with:

- `navigation_backend=agibot_gdk`
- `primitive_provenance=agibot_gdk_normal_navi`

Use that verified waypoint for the first Codex hardware run.

## Codex Dry Run

Run the Codex route without movement first:

```bash
just task::run semantic-map-build codex camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  output_dir=output/agibot/semantic-map-build-codex-dry-run \
  policy=codex_agibot_semantic_map_build_pilot \
  visual_grounding=grounding-dino \
  visual_grounding_timeout_s=20
```

The dry run should produce `run_result.json`, `trace.jsonl`,
`runtime_metric_map.json`, and `report.html`. It may show explicit
no-live-camera or no-movement evidence, but it must still prove the Codex MCP
route is launching against `agibot_semantic_map_build`.

Do not call a dry-run artifact hardware evidence.

## Codex Hardware Run

Enable real movement only after the operator confirms the run-level gate:

```bash
just task::run semantic-map-build codex camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  output_dir=output/agibot/semantic-map-build-hardware \
  policy=codex_agibot_semantic_map_build_pilot \
  visual_grounding=grounding-dino \
  visual_grounding_timeout_s=20 \
  real_movement_enabled=true
```

The run must leave artifacts under:

```text
output/agibot/semantic-map-build-hardware/<stamp>/seed-7/
```

The expected hardware evidence is:

- `agent_driven=true`
- `mcp_server=agibot_semantic_map_build`
- `cleanup_profile=real_robot_cleanup_v1`
- `backend_variant=agibot_gdk`
- `physical_navigation_pilot=true`
- `physical_cleanup_ready=false`
- `real_movement_enabled=true`
- successful `agibot_gdk_normal_navi` navigation evidence
- live `agibot_gdk_head_color_camera` observation evidence with image artifacts
- successful external visual-grounding evidence for `grounding-dino`
- no Human Takeover Stop
- manipulation tools remain blocked

## Hardware Checker

After the Codex hardware run, verify the artifact:

```bash
.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  output/agibot/semantic-map-build-hardware/<stamp>/seed-7/run_result.json \
  --expect-backend agibot_gdk \
  --expect-mcp-server agibot_semantic_map_build \
  --require-agent-driven \
  --require-camera-model-policy \
  --expect-visual-grounding-pipeline grounding-dino \
  --require-runtime-metric-map \
  --require-semantic-sweep \
  --require-agibot-g2-hardware \
  --min-generated-mess-count 0 \
  --min-sweep-coverage 1.0 \
  --allow-partial-cleanup
```

If this checker fails, A is not accepted yet. Fix the reported evidence gap and
rerun from the smallest necessary step.

## Failure Handling

Stop the run and hand control back to the operator when any of these happen:

- current GDK map does not match the completed context
- localization or run-enablement gate is missing
- waypoint is unverified, blocked, timed out, or unresolved
- `Pnc.normal_navi` fails or times out
- live `head_color` observation is missing
- visual grounding fails during a hardware-acceptance run
- robot-side obstacle stop or human E-stop is triggered

Do not add hidden fallback waypoints, map switches, relocalization attempts, or
arbitrary coordinate navigation during A acceptance.

## Out Of Scope

These are not required for A:

- OpenClaw Gateway
- household object cleanup success
- physical manipulation: `pick`, `place`, `place_inside`, `open_receptacle`,
  or `close_receptacle`
- MolmoSpaces simulation evidence
- dry-run Codex artifacts as hardware proof

The acceptance claim is intentionally small: Codex can call the Agibot-backed
public MCP surface, move to verified G2 waypoints, observe through `head_color`,
and produce a checker-passing hardware artifact.
