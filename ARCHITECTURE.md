# Architecture

How the roboclaws codebase is organized. For *why* decisions were made
(scenario design, technology choices, phase rationale), see
[`docs/human/technical-design.md`](docs/human/technical-design.md). For *what you can
run*, see [`README.md`](README.md).

## Bird's-eye view

Roboclaws has two embodied-demo stacks that share one review philosophy:
make agent behavior visible, separate public agent inputs from private
evaluation, and keep proof claims tied to artifacts.

1. **AI2-THOR navigation stack** — multi-agent navigation, territory, coverage,
   OpenClaw Gateway demos, coding-agent MCP control, and the Railway appliance.
   The shared center is `MultiAgentEngine` (one process, one Unity controller,
   N agents). Modes differ in what *drives* that engine: a Python game loop,
   a remote OpenClaw Gateway, a coding agent over MCP, or the hosted appliance.
2. **MolmoSpaces cleanup/proof stack** — household cleanup scenarios,
   public/private Agent View contracts, shared cleanup reports, RBY1M robot-view
   timelines, and local RBY1M/CuRobo proof-bundle generation. The shared center
   is `RealWorldCleanupContract`: it defines what the Cleanup Agent may see,
   what stays private for scoring, and which cleanup substeps can later be
   bound to planner-backed manipulation proof.

The navigation stack has three core abstractions:

1. **`MultiAgentEngine`** — wraps `ai2thor.controller.Controller`, owns
   the scene + cameras + per-agent state (`roboclaws/core/engine.py`).
2. **`VLMProvider`** — pluggable inference protocol. Each provider
   (Anthropic, OpenAI, Kimi, MiMo, NVIDIA, Mock) implements `get_action`.
   The protocol and factory live in `roboclaws/core/vlm.py`; provider
   implementations live in `roboclaws/core/providers/`.
3. **`RoboclawsMCPServer`** — the MCP tool surface
   that any external agent (OpenClaw skill, Codex, Claude Code) consumes
   to drive a robot (`roboclaws/mcp/server.py`).

The cleanup/proof stack has four core abstractions:

1. **`RealWorldCleanupContract`** — public cleanup-agent surface: metric map,
   fixture hints, waypoint observations, observed object handles, object/receptacle
   actions, and private scoring separation (`roboclaws/molmo_cleanup/realworld_contract.py`).
2. **Semantic cleanup loop + report underlay** — deterministic cleanup policy,
   semantic substep timeline, Agent View, Private Evaluation, advisory scoring,
   selected Nav2-shaped map bundle snapshots, static costmap route checks, and visual
   report rendering
   (`roboclaws/molmo_cleanup/semantic_cleanup_loop.py`,
   `roboclaws/maps/`,
   `roboclaws/molmo_cleanup/nav2_map_bundle.py`,
   `roboclaws/molmo_cleanup/report.py`).
3. **Planner-proof request and bundle flow** — turns completed cleanup substeps
   into private bound proof requests, dry-run manifests, local execution reports,
   and optional cleanup reruns (`roboclaws/molmo_cleanup/planner_proof_requests.py`,
   `scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py`).
4. **Planner-backed primitive gate** — adapters and checkers that decide whether
   a cleanup subphase is still `api_semantic` or has exact-scene RBY1M/CuRobo
   proof for the requested object/target binding.

Across both stacks, `roboclaws/mcp/profiles.py` now defines semantic MCP
contract profiles. Profiles describe the canonical public capability tools,
capability families, provenance expectations, privileged-tool metadata, and
private-data exclusions for a selected backend/domain. The current built-ins are
`ai2thor_navigation_v1`, `molmospaces_cleanup_v1`, and
`real_robot_cleanup_v1`. For the human design
principles behind profiles, MCP tools, and agent skills, start with
[`README.md`](README.md). For the detailed profile reference, see
[`docs/human/mcp-skills-and-semantic-profiles.md`](docs/human/mcp-skills-and-semantic-profiles.md).

![Architecture diagram](docs/architecture.svg)

## Navigation MCP contract

`roboclaws/mcp/server.py` defines the concrete AI2-THOR navigation tool
surface that external agents use over structured-HTTP transport:

- **`observe(label="")`** — returns a structured agent state plus images
  (FPV, `map-v2` overhead, chase cam) or a text-bridge description for
  vision-light models. Labeled observes archive snapshots to disk and emit
  `MEDIA:` hints the OpenClaw Control UI inlines.
- **`observe_archived(label)`** — captures the same snapshot bundle to
  disk without returning inline images. This keeps long multi-target runs
  out of image-token debt when the agent only needs artifact paths.
- **`move(direction, reason="", steps=1)`** — one navigation step (or up
  to 5). Returns `pose_delta`, `visited_count_here`, `collisions`, and a
  synthetic `human_message` if the agent has moved blind too many times.
- **`done(reason)`** — terminates the run cleanly. Idempotent.

By default, the server registers only that canonical `ai2thor_navigation_v1`
surface. Demo launchers can explicitly opt into privileged simulator helpers:

- **`scene_objects(filter_types="")`** — returns the full AI2-THOR object
  inventory, optionally filtered by object type, so agents can plan
  target-relative routes before moving.
- **`goto(object_id, distance=1.0, face=True)`** — teleports to a reachable
  cell near an object and optionally faces it. This is a high-leverage
  adapter for object-photo tasks where grid-step navigation is incidental.

The semantic profile `ai2thor_navigation_v1` treats `observe`,
`observe_archived`, `move`, and `done` as canonical navigation capability
tools. `scene_objects` and `goto` are privileged opt-in helpers for photo/demo
runs, not default real-robot capability claims.

Every tool call writes a line to `<run_dir>/trace.jsonl`. The schema is a
**frozen superset** of `tests/fixtures/trace_schema_reference.json` —
adding keys is fine; removing or renaming is a breaking change because
`scripts/reports/render_autonomous_replay.py` consumes it.

The server binds to `127.0.0.1:18788` by default. Loopback-only is part
of the threat model (see `.planning/milestones/v1.98-phases/02.6-openclaw-mcp-tools-integration/`
threat T-02.6-01); changing the bind address requires a deliberate
decision, not a one-liner.

## AI2-THOR Operating Modes

All four reuse the same `MultiAgentEngine` core. They differ in what
boots first and what mediates between the engine and the model.

### 1. Direct VLM games

`examples/games/territory_game.py`, `examples/games/coverage_game.py`. Boots
`MultiAgentEngine` + a `VLMProvider` directly. No MCP, no Gateway. Game
logic lives in `roboclaws/games/territory.py` (`TerritoryGame`) and
`roboclaws/games/coverage.py` (`CoverageGame`). Each `step()` passes
prompt images to the provider, parses the action, and applies it. Replay
to `output/<game>/<timestamp>/` via `ReplayRecorder`.

### 2. OpenClaw Gateway

`just chat::run`, `just openclaw::run nav`. Routes through a Gateway docker
container (default `:18789`) that handles auth, sessions, and model
routing. The roboclaws side:

- `roboclaws/openclaw/transport.py` — `OpenClawBridge`: HTTP client to
  the Gateway, retry on read timeout, fail-fast on connect / 4xx / 5xx.
- `roboclaws/openclaw/bridge.py` — `OpenClawProvider`: a
  `VLMProvider`-compatible wrapper that uses `OpenClawBridge`. Tracked
  via `ProviderStatus`.
- `roboclaws/openclaw/skill.py` — `AI2THORNavigatorSkill`: wraps a
  provider with a SOUL preset for use as an OpenClaw skill.
- `roboclaws/mcp/text_bridge.py` — `VisionBridge`: image-to-text
  bridge for vision-light models (e.g., MiMo text variants).

### 3. Direct coding-agent driver

`examples/mcp/coding_agent_nav_server.py`. Boots `MultiAgentEngine` +
`RoboclawsMCPServer` over HTTP. No Gateway, no VLM key needed
server-side — the coding agent (Codex / Claude Code) is the model. Public
launchers run that agent in the pinned `Dockerfile.coding-agents` runtime while
the MCP server and AI2-THOR stay host-side. Output:
`output/runs/<timestamp>/` unless `--output-dir` is passed. Operating instructions
for the agent itself live in
[`skills/ai2thor-navigator/SKILL.md`](skills/ai2thor-navigator/SKILL.md).

### 4. Railway appliance

`Dockerfile.railway` + `deploy/railway/`. Single container bundling
AI2-THOR + xvfb + nginx + supervisord + the OpenClaw Gateway + the MCP
server + `reset_server.py` (HTTP `/reset`). Public surface is nginx on
`:8080` with auth via `OPENCLAW_TOKEN` / `DEMO_PASSWORD`. Env-driven
config seeded by `scripts/appliance/appliance_seed_openclaw.py`. Full deploy
runbook: [`docs/human/railway/deploy.md`](docs/human/railway/deploy.md).

## MolmoSpaces Cleanup Flow

The MolmoSpaces side is a separate embodied-cleanup flow rather than a fifth
AI2-THOR mode. It exists to answer a different question: when a household
cleanup artifact says "the robot cleaned this up," which parts were semantic
simulator state edits, and which parts have planner-backed RBY1M/CuRobo proof?

The normal path is:

1. A generated mess scenario creates a hidden set of moved objects.
2. The Cleanup Agent receives the public contract: metric map, room-level
   fixture hints, waypoint observations, and observed object handles.
3. The semantic cleanup loop records `nav -> pick -> nav -> open? -> place`
   substeps and writes one shared Cleanup Artifact Report.
4. Private scoring evaluates the final scene with hidden acceptable-destination
   truth that the agent never saw.
5. Planner-proof request generation turns completed semantic substeps into
   bound local proof commands. Proof-bundle runner reports then show whether
   RBY1M/CuRobo execution actually produced planner-backed cleanup binding.

Operator-facing settings and recommended recipes live in
[`docs/human/molmospaces-settings.md`](docs/human/molmospaces-settings.md).

## Code map

| Path | Role |
|------|------|
| `roboclaws/core/engine.py` | `MultiAgentEngine`: AI2-THOR controller wrapper, owns scene + cameras (overhead orthographic + per-agent chase), reachable-positions cache. Public API: `step`, `reset`, `get_agent_state`, `get_overhead_frame`, `add_chase_cam`. |
| `roboclaws/core/views.py` | View composition: `NavigationViewContext` (per-scene stable state) + `NavigationPromptBundle` (per-turn render). Outputs the `map-v2+chase` view variant — FPV + structured overhead + chase cam. |
| `roboclaws/core/visualizer.py` | `GameVisualizer`: lower-level overhead/structured map rendering. Called by `views.py`. |
| `roboclaws/core/vlm.py`, `roboclaws/core/providers/` | `VLMProvider` protocol + `create_provider()` factory, with concrete provider implementations split by backend. Tracks per-provider health via `ProviderStatus`. Owns SOUL loading (`load_agent_souls`). |
| `roboclaws/core/replay.py` | `ReplayRecorder`: per-step capture (frames, overhead, prompt state, response). Persists to `replay.json` + per-step PNG dirs (`frames/`, `agent_frames/`, `overhead/`, `scene_views/`). Optional GIF. |
| `roboclaws/games/territory.py` | `TerritoryGame`: adversarial cell-claiming. Tracks `cells_claimed`, `connectivity_ratio`, `blocking_events`. |
| `roboclaws/games/coverage.py` | `CoverageGame`: cooperative coverage. Tracks `coverage_pct`, per-agent `contribution`, `work_balance`. |
| `roboclaws/games/common.py` | Shared action set + `SAFE_FALLBACK_ACTION = "RotateRight"`. |
| `roboclaws/mcp/server.py` | `RoboclawsMCPServer`: FastMCP server exposing canonical `observe`, `observe_archived`, `move`, and `done` tools by default, with privileged `scene_objects` and `goto` helpers only when a launcher opts in. Owns trace.jsonl, snapshot archiving, human-message queue, blind-move warnings, and reset coordination. |
| `roboclaws/mcp/profiles.py`, `roboclaws/mcp/entrypoint.py` | Semantic MCP contract profile declarations and a small router helper for registering one selected profile's public tools. Current profiles represent AI2-THOR navigation, MolmoSpaces cleanup, and the first real-robot Nav2 cleanup pilot while excluding privileged simulator tools/private evaluator truth from canonical public metadata. |
| `roboclaws/mcp/text_bridge.py` | `VisionBridge`: image-to-text bridge for vision-light models. |
| `roboclaws/molmo_cleanup/realworld_contract.py` | `RealWorldCleanupContract`: ADR-0003 public/private cleanup surface, perception modes, observed handles, and cleanup tools. |
| `roboclaws/maps/` | Reusable Nav2-shaped map artifact package: bundle writing/validation, metric-map projection, occupancy rasterization, and pure-Python static costmap route validation. |
| `roboclaws/molmo_cleanup/nav2_map_bundle.py` | Molmo cleanup compatibility wrapper that resolves/validates selected prebuilt bundles and attaches run-local map bundle snapshots to cleanup artifacts. |
| `roboclaws/molmo_cleanup/nav2_adapter.py`, `physical_nav2_pilot.py` | Mockable direct Nav2 backend adapter plus the first physical navigation/perception pilot runner: load a prebuilt map bundle, attempt inspection and fixture preferred waypoints, observe reached waypoints, and keep manipulation blocked. |
| `roboclaws/molmo_cleanup/semantic_cleanup_loop.py` | Shared semantic cleanup driver used by direct demos and MCP smoke paths. |
| `roboclaws/molmo_cleanup/report.py`, `report_visual_core.py` | Shared Cleanup Artifact Report renderer: Agent View, Private Evaluation, semantic substeps, robot timeline, planner proof, and bridge readiness sections. |
| `roboclaws/molmo_cleanup/planner_proof_requests.py` | Converts cleanup substeps into private bound planner-proof requests, proof-bundle manifests, selection memory, fallback filtering, and cleanup rerun commands. |
| `roboclaws/molmo_cleanup/planner_probe_primitive_executor.py`, `planner_primitive_executor.py` | Executor adapters for promoting exact matching planner probe evidence into planner-backed cleanup primitive provenance. |
| `roboclaws/molmo_cleanup/grasp_*`, `rby1m_curobo_gate.py` | Local proof diagnostics for RBY1M/CuRobo runtime readiness, grasp-cache validity/generation, and task feasibility blockers. |
| `roboclaws/openclaw/bridge.py` | `OpenClawProvider`: VLMProvider that talks to a Gateway. |
| `roboclaws/openclaw/transport.py` | `OpenClawBridge`: HTTP transport for the Gateway, retry policy. |
| `roboclaws/openclaw/skill.py` | `AI2THORNavigatorSkill`: wraps a provider as an OpenClaw skill with SOUL injection. |
| `roboclaws/openclaw/reset_server.py` | HTTP `/reset` for appliance scene resets (loopback-only). |
| `roboclaws/openclaw/diagnostics.py` | Replay-loading utilities (`load_replay_turn`). |
| `examples/games/territory_game.py`, `coverage_game.py` | Mode 1 entry points. |
| `examples/mcp/coding_agent_nav_server.py` | Mode 3 entry point (no Gateway). |
| `examples/openclaw/openclaw_demo.py`, `openclaw_nav_autonomous.py`, `openclaw_photo_task.py`, `openclaw_interactive.py` | Mode 2 entry points (Gateway). |
| `examples/molmo_cleanup/molmospaces_realworld_cleanup.py` | MolmoSpaces cleanup entry point for ADR-0003 public/private real-world cleanup. |
| `examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py`, `roboclaws/molmo_cleanup/realworld_mcp_server.py` | Direct Codex/Claude/OpenClaw-style cleanup-agent MCP surface for the ADR-0003 contract. |
| `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py` | Deterministic smoke wrapper for the cleanup MCP contract and report/checker path. |
| `scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py` | Proof-bundle dry-run/execution/rerun harness for local RBY1M/CuRobo proof attempts. |
| `Dockerfile.railway`, `deploy/railway/` | Mode 4 entry point + supervisord/nginx config. |
| `skills/ai2thor-navigator/SKILL.md` | Base operating instructions for any agent driving the AI2-THOR robot via MCP — shared by OpenClaw skills, Codex, and Claude Code. |
| `skills/capture-object-photo/SKILL.md` | Skill-level photo behavior (`locate -> navigate -> observe`) plus route-planning helper. Keeps object-photo strategy out of the MCP capability surface. |
| `scripts/` | Supporting tooling: bootstrap, scoring (`check_photo_task.py`), replay rendering (`render_autonomous_replay.py`), appliance config (`appliance_seed_openclaw.py`), regression harnesses. |
| `tests/` | Mock-heavy unit tests + integration guards (refactor regression, photo-task smoke, MCP server contracts). |

## View system

The view system exists because VLMs reason about navigation better when
given multiple complementary views. `roboclaws/core/views.py` composes
three:

- **FPV** — the agent's first-person camera (`engine.frame`).
- **map-v2** — a structured overhead map that overlays reachable cells,
  visited cells, agent positions, and game state on the orthographic
  top-down projection. Rendered by
  `GameVisualizer.render_projected_structured_map()`.
- **chase** — third-person behind-agent camera (`engine.add_chase_cam()`
  once per agent, `engine.update_chase_cam()` per step).

Only one variant is in use today —
`ViewVariant = Literal["map-v2+chase"]` (`views.py:18`). The variant
string + `image_labels` pair is part of the trace schema, so adding a
new variant is an additive change.

## Replay & artifacts

Two artifact pipelines coexist, one per drive style:

- **Game runs** (`ReplayRecorder` in `core/replay.py`) — used by Mode 1.
  Produces `replay.json` + per-step PNG directories + optional GIF.
  Default output: `output/<game>/<timestamp>/`.
- **MCP runs** (`roboclaws/mcp/server.py`) — used by Modes 2 / 3 / 4. Produces
  `trace.jsonl` (one line per tool call), `run_result.json` on done, and
  labeled snapshots in `<run_dir>/snapshots/agent-<id>/`. Default output:
  `output/runs/<timestamp>/` (Mode 3) or
  `output/openclaw-*/<timestamp>/` (Mode 2).

The `latest.fpv.png` / `latest.map.png` / `latest.chase.png` symlinks
under `snapshots/agent-<id>/` are written on every observe (labeled or
not) and power the `just chat::view` live viewer.

## Pointers

| What you want | Where it lives |
|---------------|----------------|
| Scenario design rationale, VLM strategy, references | [`docs/human/technical-design.md`](docs/human/technical-design.md) |
| Big-picture MCP and skill principles | [`README.md`](README.md) |
| Semantic profiles and privileged-tool boundaries | [`docs/human/mcp-skills-and-semantic-profiles.md`](docs/human/mcp-skills-and-semantic-profiles.md) |
| MolmoSpaces cleanup settings and proof boundaries | [`docs/human/molmospaces-settings.md`](docs/human/molmospaces-settings.md) |
| Domain vocabulary for cleanup/proof language | [`docs/human/domain.md`](docs/human/domain.md) |
| Atomic architectural decisions (platform choice, deferred integrations) | [`docs/adr/`](docs/adr/) |
| Direct coding-agent driver setup (Mode 3) | [`docs/human/coding-agent-nav-server.md`](docs/human/coding-agent-nav-server.md) |
| OpenClaw local setup (Mode 2) | [`docs/human/openclaw/local.md`](docs/human/openclaw/local.md) |
| OpenClaw Gateway internals | [`docs/human/openclaw/gateway-internals.md`](docs/human/openclaw/gateway-internals.md) |
| Railway appliance deploy (Mode 4) | [`docs/human/railway/deploy.md`](docs/human/railway/deploy.md) |
| Verified models per provider | [`docs/human/model-matrix.md`](docs/human/model-matrix.md) |
| Operating rules for any agent driving the robot | [`skills/ai2thor-navigator/SKILL.md`](skills/ai2thor-navigator/SKILL.md) |
| Current status and active source links | [`STATUS.md`](STATUS.md) |
| Active GSD execution state | [`.planning/STATE.md`](.planning/STATE.md) |
| Pre-GSD plans | [`docs/plans/`](docs/plans/) |
| Shipped-phase history | `docs/retrospectives/` |
