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
- The map bundle passes the deterministic contract gate before an agent starts:

```bash
uv run python scripts/maps/check_bundle.py assets/maps/<environment_id>
```

For Molmo rehearsal lanes other than `smoke`, the public
`just run::surface surface=household-world preset=cleanup ...` facade selects the checked-in
`assets/maps/molmo-cleanup-default-7` bundle by default and fails before
cleanup startup if it is missing or invalid. Override the selection with
`map_bundle=<path-or-assets-id>` when testing another prepared environment.

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
- simulator rehearsal navigation is labelled `sim_costmap_planner` with static
  route metadata; hardware success is the first place `nav2_action` may appear

For a deterministic local contract/artifact rehearsal with a mock Nav2 client:

```bash
uv run python scripts/molmo_cleanup/run_physical_nav2_cleanup_pilot.py \
  --map-bundle-dir assets/maps/molmo-cleanup-default-7 \
  --run-dir output/molmo/physical-nav2-pilot-local-check

uv run python scripts/maps/check_bundle.py \
  output/molmo/physical-nav2-pilot-local-check/map_bundle
```

That command exercises the physical-pilot report path without a live ROS graph.
For a real robot run, keep the same `DirectNav2Adapter` contract and replace the
deterministic client with an operator-approved ROS/Nav2 action client.

## Simulator Rehearsal

Use the MolmoSpaces world-label report before hardware:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=10
```

For a live Codex cleanup rehearsal with the supported local runtime, set
`CODEX_BASE_URL` and `CODEX_API_KEY` in the repo-local `.env` for the default
`codex-env` route, then run:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=10
```

For a local Codex Nav2 acceptance rehearsal, write to a stable proof root and use
the smaller five-object gate so the no-regression expectation is exact:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels \
  output_dir=output/molmo/codex-gpt55-nav2-report \
  seed=7 \
  scenario_setup=relocate-cleanup-related-objects \
  relocation_count=5 \
  map_bundle=molmo-cleanup-default-7
```

Hosted CI does not support Codex runs. Do not add a CI Codex provider smoke,
repository-secret OpenAI route, or Codex acceptance artifact. CI may exercise
supported Claude Code and OpenClaw routes; Codex proof stays local and uses the
repo-local `.env`.

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
  --expect-profile world-oracle-labels \
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

Validate the immutable map snapshot directly when debugging map issues:

```bash
uv run python scripts/maps/check_bundle.py \
  output/molmo/codex-gpt55-nav2-report/<stamp>/seed-7/map_bundle
```

Local Codex acceptance evidence is incomplete until the run produces
`run_result.json`, `report.html`, and `map_bundle/map.yaml` under that
timestamped `seed-7/` directory.
