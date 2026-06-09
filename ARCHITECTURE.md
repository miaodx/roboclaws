# Architecture

Roboclaws is a thin robotics demo repo. Its architecture goal is not to hide
robot work behind one opaque tool; it is to make every run reviewable through
public surface/intent inputs, MCP tool traces, maps, reports, and
private-evaluation boundaries.

For commands, start with [`README.md`](README.md). For the
surface/intent/skill/profile model, read
[`docs/human/mcp-skills-and-semantic-profiles.md`](docs/human/mcp-skills-and-semantic-profiles.md).

![Architecture diagram](docs/architecture.svg)

## Core Model

The current human-facing layers are:

```text
Open-ended goal
  -> Runnable Surface and Intent
  -> Agent Skill
  -> Capability Profile requirements
  -> MCP Capability Tools
  -> Backend Variant
  -> Artifacts and reports
```

- **Runnable Surfaces And Intents** are public run contracts such as
  `surface=ai2thor-world intent=navigate`,
  `surface=household-world intent=map-build`, and
  `surface=household-world intent=cleanup`. They own command names,
  parameters, report shape, and acceptance gates.
- **Agent Skills** own strategy: prompts, scripts, examples, recovery loops,
  and trace-preserving routines such as `navigate -> pick -> place`.
- **Capability Profiles** define reusable capability environments. Skills
  require profiles; profiles should not be copied into task-specific supersets.
- **MCP Tools** are the stable public robot interface: observe, navigate, map,
  pick, place, done, and related bounded capabilities.
- **Backend Variants** implement the same public shape in mock, simulator, API,
  or physical-robot environments.

The real-robot rule is: physical runs should reuse the same surface, intent,
skill, profile, and MCP tool layers. They differ by backend variant,
provenance, safety gates, operator map context, and blocked-capability status.

## Major Stacks

Roboclaws currently has two embodied-demo stacks.

### AI2-THOR Navigation

This stack proves multi-agent navigation and coding-agent MCP control over
AI2-THOR scenes.

Key pieces:

- `roboclaws/core/engine.py` owns the `MultiAgentEngine` wrapper around
  AI2-THOR.
- `roboclaws/core/vlm.py` and `roboclaws/core/providers/` own provider routing.
- `roboclaws/ai2thor/navigation_mcp.py` exposes the AI2-THOR navigation MCP
  surface.
- `roboclaws/cli/agent_server.py` starts coding-agent MCP servers for
  `ai2thor-nav`, `household-cleanup`, and `semantic-map-build`.
- `roboclaws/agents/live_runtime.py` defines the provider-neutral runtime
  contract for one live coding-agent invocation. Current Codex and Claude Code
  CLI routes remain the product baselines; experimental SDK runtimes live under
  `roboclaws/agents/drivers/` without changing public task strategy.
- `examples/games/` contains runnable game examples.

The canonical navigation tools are `observe`, `observe_archived`, `move`, and
`done`. Simulator helpers such as `scene_objects` and `goto` are privileged
opt-ins for demos; they are not real-robot capability claims.

### Household World And Cleanup

This stack proves household world understanding, semantic cleanup, runtime maps,
and future physical robot parity.

Key pieces:

- `roboclaws/household/realworld_contract.py` owns the public/private
  household contract.
- `roboclaws/household/realworld_cleanup.py` owns the direct deterministic
  cleanup and semantic-map sweep CLI used by `just` and harness recipes.
- `roboclaws/household/semantic_cleanup_loop.py` owns the direct semantic
  cleanup flow.
- `roboclaws/maps/` owns reusable navigation map artifacts, projections, and
  Actionable Semantic Map Snapshot conversion.
- `roboclaws/household/realworld_mcp_server.py` exposes the cleanup MCP
  surface for coding agents and OpenClaw-style clients.
- `roboclaws/cli/household_agent_server.py` and
  `roboclaws/cli/agibot_map_build_agent_server.py` assemble live household MCP
  server processes behind `python -m roboclaws.cli.agent_server ...`.
- `roboclaws/household/report.py` renders the shared report.
- `roboclaws/household/camera_control.py` owns the external render-camera
  request schema used by MuJoCo, Isaac, and opt-in Genesis scene probes.
- `roboclaws/household/agibot_sdk_runner.py` and
  `vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py` keep the Agibot SDK
  boundary behind a subprocess runner.
- `roboclaws/operator_console/` provides the standalone local agent operator
  console. It exposes explicit coding-agent route metadata, per-backend locks,
  route gates, normalized live operator state, redacted raw-log access, and
  links to existing run artifacts.

The clean-slate direction is:

- `surface=household-world intent=map-build` produces Runtime Metric Map
  snapshots, which can be wrapped as an Actionable Semantic Map Snapshot for
  downstream task consumption.
- `surface=household-world intent=cleanup` runs cleanup.
- The canonical map flow is minimal-first: start from occupancy/free-space
  navigation context, run `intent=map-build`, then feed the resulting
  `runtime_metric_map.json` or `actionable_semantic_map_snapshot.json` to
  cleanup with `runtime_map_prior=...` when a prior sweep is useful.
- Offline Agibot `navigation_memory.json` conversion happens at the map-artifact
  boundary and produces the same Actionable Semantic Map Snapshot contract;
  cleanup and open household tasks should not add Agibot-only loading branches.
- `household_world_v1` is the reusable world-understanding capability profile.
- Manipulation capability should be composed as a separate requirement when a
  skill needs `pick`, `place`, `open_receptacle`, or `close_receptacle`.

## Public Command Surface

The public command grammar is intentionally small:

```bash
just run::surface surface=<surface> driver=<driver> [intent=<intent>] [key=value ...]
```

Examples:

```bash
just run::surface surface=ai2thor-world driver=codex intent=navigate report=visual
just run::surface surface=household-world driver=direct intent=map-build evidence_lane=world-oracle-labels seed=7
just run::surface surface=household-world driver=direct intent=cleanup evidence_lane=world-oracle-labels seed=7
just console::run
```

For household runs, callers pass the cleanup input/evidence lane explicitly as
`evidence_lane=...`.
`evidence_lane` decides what the agent sees. Supported current lanes are
`world-oracle-labels`, `world-public-labels`, `camera-grounded-labels`, and
`camera-raw-fpv`. `camera-grounded-labels` additionally requires
`camera_labeler=...`, such as `sim-projected-labels` for the deterministic
camera-projected control producer or `grounding-dino` for the default real
open-vocabulary bbox proposer. `camera_labeler` is invalid for world-label and
raw-FPV lanes. The `smoke` token remains a cheap synthetic preset, not an
evidence lane.

Cleanup lanes do not select online/offline map behavior. The default map
projection is `map_mode=minimal`, which exposes occupancy geometry, generated
exploration candidates, and runtime semantic anchors instead of authored room
or fixture labels. Use `runtime_map_prior=...` to consume a raw runtime map or
canonical Actionable Semantic Map Snapshot prior. `map_mode=rich` remains only
as an explicit legacy/debug shortcut for tests that need pre-authored public
fixture semantics.

The clean-slate household public shape is `surface=household-world` plus
explicit intents. `intent=map-build` produces Runtime Metric Map evidence,
`actionable_semantic_map_snapshot_v1` is the canonical downstream artifact
contract, and `intent=cleanup` consumes household-world evidence for cleanup.
Older task/profile names such as `semantic-map-build`, `household-cleanup`,
and Molmo-specific profile names are legacy compatibility details, not the
canonical task layer.

`just console::run` starts a standalone local operator console for supported
coding-agent household routes. The console does not expose arbitrary shell
commands: route selection comes from explicit console metadata and still
resolves through the public surface/intent catalog constraints.

## Capability Profiles

`roboclaws/mcp/profiles.py` defines current MCP capability metadata. The
household head is `household_world_v1`, composed with
`household_manipulation_v1` and `household_episode_v1` for cleanup skills.
Older backend/domain ids such as `molmospaces_cleanup_v1` and
`real_robot_cleanup_v1` remain legacy compatibility details.

Going forward:

- Add a new runnable surface or intent by adding a domain `tasks.py` spec and
  registering it in `roboclaws/launch/catalog.py`; keep behavior in the domain
  package.
- Add a new backend as a reusable adapter under the owning domain package, then
  expose it through task metadata or launch validation.
- Add a new coding-agent driver under `roboclaws/agents/drivers/` and keep
  task-specific kickoff text in `roboclaws/agents/prompts/`. Shared launcher
  and status semantics should flow through `roboclaws/agents/live_runtime.py`
  when the driver is a live coding-agent runtime.
- Add or revise MCP tools in the domain-local MCP module when the capability
  surface is stable enough to reuse across skills.
- Profiles describe reusable capability environments, not whole tasks.
- Skills compose profiles by requirement; profiles should not copy other
  profiles' tool lists.
- Backend variants belong in metadata/config, not in public task names.
- Private generated mess sets, acceptable destinations, hidden target lists,
  private manifests, and private scorer truth must not appear in public profile
  metadata or agent-facing inputs.

## Runtime Artifacts

Every serious run should produce reviewable evidence:

- `trace.jsonl` for tool calls and state transitions.
- `agent_view.json` / `run_result.json` for public agent-facing state.
- `runtime_metric_map.json` when a run builds or updates household world
  evidence.
- `actionable_semantic_map_snapshot.json` when online runtime-map output or
  offline Agibot navigation memory is packaged for downstream household tasks.
- `report.html` for human review.
- Optional planner-proof bundles when cleanup substeps are checked against
  local RBY1M/CuRobo proof.

The artifact boundary matters: public agent evidence and private scoring truth
must remain separate. Reports may display both, but agent inputs and MCP
profiles must not leak private evaluator data.

## Real-Robot Boundary

Real-robot work is incremental:

1. Prove public map context and observation.
2. Prove bounded navigation to operator-approved waypoints or backend-verified
   goals.
3. Keep manipulation as `blocked_capability` until physical proof exists.
4. Promote physical manipulation only when reports can show provenance, safety
   gates, and failure modes.

Agibot G2 and ROS2/Nav2 should be backend variants under the same public
task/profile shape, not separate robot-only task taxonomies.

## Where To Look

| Need | Start here |
| --- | --- |
| What to run | [`README.md`](README.md), [`just/README.md`](just/README.md) |
| Surface/intent/skill/profile design | [`docs/human/mcp-skills-and-semantic-profiles.md`](docs/human/mcp-skills-and-semantic-profiles.md) |
| MolmoSpaces settings | [`docs/human/molmospaces-settings.md`](docs/human/molmospaces-settings.md) |
| Local runtime and keys | [`docs/human/local-runtime.md`](docs/human/local-runtime.md) |
| Current project focus | [`STATUS.md`](STATUS.md) |
| Detailed plans and evidence | `docs/plans/`, `docs/status/active/`, `docs/retrospectives/` |
