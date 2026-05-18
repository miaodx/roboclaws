# Real Robot Nav2 Cleanup Pilot

This runbook is for the first physical Navigation + Perception Pilot. It is not
a physical cleanup proof: navigation and observation may execute through Nav2,
while physical manipulation stays `blocked_capability`.

## Preconditions

- A ROS 2/Nav2 robot is running with an operator-owned E-stop or teleop stop.
- A Nav2 map bundle exists for the selected environment:
  - `map.yaml`
  - occupancy image such as `map.pgm`
  - `semantics.json`
  - `profiles/<robot>.yaml`
  - `costmaps/<robot>.costmap_params.yaml`
- The selected robot profile matches the real base footprint, map/base frames,
  camera frame, and navigation tolerances.
- The MCP-facing backend exposes only cleanup tools. Agents must not receive
  direct ROS topic, service, or action access.

## Pilot Contract

Use semantic profile `real_robot_cleanup_v1`.

Navigation and perception pilot tools:

- `metric_map`
- `fixture_hints`
- `navigate_to_room`
- `navigate_to_waypoint`
- `observe`
- `adjust_camera`
- `declare_visual_candidates`
- `navigate_to_visual_candidate`
- `inspect_visible_object`
- `navigate_to_object`
- `navigate_to_receptacle`
- `done`

Blocked first-pilot manipulation tools:

- `pick`
- `place`
- `place_inside`
- `open_receptacle`
- `close_receptacle`

`navigate_to_receptacle` means fixture preferred-waypoint navigation. It must
return `goal_source=fixture_preferred_waypoint` and
`manipulation_ready=false`.

## Local Acceptance

The pilot is accepted only when the report shows:

- `physical_navigation_pilot=true`
- `physical_cleanup_ready=false`
- every public inspection waypoint was attempted
- every fixture preferred waypoint was attempted
- reached waypoints have an `observe` result
- successful physical navigation is labeled `nav2_action`
- failed navigation is labeled `blocked_capability` with a failure type,
  current pose, target pose, and backend summary
- manipulation tools remain blocked
- `map_bundle/` contains the run-local Nav2 artifact snapshot and appears in
  `report.html`

## Simulator Rehearsal

Use the MolmoSpaces world-label report before hardware:

```bash
just task::run molmo-cleanup direct world-labels seed=7 generated_mess_count=10
```

For a live Codex cleanup rehearsal with the supported Docker runtime:

```bash
ROBOCLAWS_CODE_AGENT_DOCKER_USE_HOST_CODEX_HOME=1 \
ROBOCLAWS_CODEX_PROVIDER=system \
ROBOCLAWS_CODEX_MODEL=gpt-5.5 \
just task::run molmo-cleanup codex world-labels seed=7 generated_mess_count=10
```

If the local network resets Codex Responses websocket connections, keep the
same official Codex provider and switch only the transport:

```bash
ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS=1 \
ROBOCLAWS_CODE_AGENT_DOCKER_USE_HOST_CODEX_HOME=1 \
ROBOCLAWS_CODEX_PROVIDER=system \
ROBOCLAWS_CODEX_MODEL=gpt-5.5 \
just task::run molmo-cleanup codex world-labels seed=7 generated_mess_count=10
```

On networks that still reset the built-in Codex system provider before the
first MCP tool call, use the official OpenAI API provider profile if an
`OPENAI_API_KEY` is available and `api.openai.com` is reachable:

```bash
ROBOCLAWS_CODEX_PROVIDER=openai-responses \
ROBOCLAWS_CODEX_MODEL=gpt-5.5 \
just task::run molmo-cleanup codex world-labels seed=7 generated_mess_count=10
```

For the official GPT-5.5 Nav2 acceptance proof, write to a stable proof root
and use the smaller five-object gate so the no-regression expectation is exact:

```bash
ROBOCLAWS_CODEX_PROVIDER=openai-responses \
ROBOCLAWS_CODEX_MODEL=gpt-5.5 \
just task::run molmo-cleanup codex world-labels \
  output_dir=output/molmo/codex-gpt55-nav2-report \
  seed=7 \
  generated_mess_count=5
```

If local `api.openai.com` access is blocked but GitHub Actions has an official
`OPENAI_API_KEY` repository secret, dispatch the dedicated opt-in CI proof
instead of the normal Molmo live matrix:

```bash
gh workflow run ci.yml \
  -f molmo_live=false \
  -f molmo_official_codex=true
```

Review the detached run with:

```bash
just molmo::status
```

The simulator report must pass the real-robot alignment checker and the cleanup
no-regression gate before a hardware pilot. Point the checker at the timestamped
run directory that contains `seed-7/run_result.json`:

```bash
uv run python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  output/molmo/codex-gpt55-nav2-report/<stamp> \
  --expect-backend molmospaces_subprocess \
  --expect-policy codex_agent \
  --expect-profile world-labels \
  --expect-seeds 7 \
  --min-generated-mess-count 5 \
  --require-agent-driven \
  --require-clean-agent-run \
  --require-advisory-scoring \
  --min-restored-count 5 \
  --min-sweep-coverage 1.0 \
  --require-waypoint-honesty \
  --require-real-robot-alignment
```

Acceptance evidence is incomplete until the official Codex run produces
`run_result.json`, `report.html`, and `map_bundle/map.yaml` under that
timestamped `seed-7/` directory.
