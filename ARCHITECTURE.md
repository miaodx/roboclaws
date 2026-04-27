# Architecture

How the roboclaws codebase is organized. For *why* decisions were made
(scenario design, technology choices, phase rationale), see
[`docs/technical-design.md`](docs/technical-design.md). For *what you can
run*, see [`README.md`](README.md).

## Bird's-eye view

Roboclaws wraps AI2-THOR's multi-agent simulator behind a small set of
abstractions and exposes them through four operating modes. The shared
center is `MultiAgentEngine` (one process, one Unity controller, N
agents). Modes differ only in what *drives* the engine: a Python game
loop, a remote OpenClaw Gateway, a coding agent over MCP, or a Railway
appliance bundling all of the above.

Three abstractions matter:

1. **`MultiAgentEngine`** — wraps `ai2thor.controller.Controller`, owns
   the scene + cameras + per-agent state (`roboclaws/core/engine.py`).
2. **`VLMProvider`** — pluggable inference protocol. Each provider
   (Anthropic, OpenAI, Kimi, MiMo, NVIDIA, Mock) implements `get_action`
   (`roboclaws/core/vlm.py`).
3. **`RoboclawsMCPServer`** — the `observe` / `move` / `done` tool surface
   that any external agent (OpenClaw skill, Codex, Claude Code) consumes
   to drive a robot (`roboclaws/openclaw/mcp_server.py`).

![Architecture diagram](docs/architecture.svg)

## The MCP contract

`roboclaws/openclaw/mcp_server.py` defines the canonical surface that
external agents use. Three tools, structured-HTTP transport:

- **`observe(label="")`** — returns a structured agent state plus images
  (FPV, `map-v2` overhead, chase cam) or a text-bridge description for
  vision-light models. Labeled observes archive snapshots to disk and emit
  `MEDIA:` hints the OpenClaw Control UI inlines. Implementation:
  `mcp_server.py:382–477`.
- **`move(direction, reason="", steps=1)`** — one navigation step (or up
  to 5). Returns `pose_delta`, `visited_count_here`, `collisions`, and a
  synthetic `human_message` if the agent has moved blind too many times.
  Implementation: `mcp_server.py:479–590`.
- **`done(reason)`** — terminates the run cleanly. Idempotent.
  Implementation: `mcp_server.py:592–604`.

Every tool call writes a line to `<run_dir>/trace.jsonl`. The schema is a
**frozen superset** of `tests/fixtures/trace_schema_reference.json` —
adding keys is fine; removing or renaming is a breaking change because
`scripts/render_autonomous_replay.py` consumes it.

The server binds to `127.0.0.1:18788` by default. Loopback-only is part
of the threat model (see `.planning/phases/02.6-openclaw-mcp-tools-integration/`
threat T-02.6-01); changing the bind address requires a deliberate
decision, not a one-liner.

## Four operating modes

All four reuse the same `MultiAgentEngine` core. They differ in what
boots first and what mediates between the engine and the model.

### 1. Direct VLM games

`examples/territory_game.py`, `examples/coverage_game.py`. Boots
`MultiAgentEngine` + a `VLMProvider` directly. No MCP, no Gateway. Game
logic lives in `roboclaws/games/territory.py` (`TerritoryGame`) and
`roboclaws/games/coverage.py` (`CoverageGame`). Each `step()` passes
prompt images to the provider, parses the action, and applies it. Replay
to `output/<game>/<timestamp>/` via `ReplayRecorder`.

### 2. OpenClaw Gateway

`make chat`, `make openclaw-nav`. Routes through a Gateway docker
container (default `:18789`) that handles auth, sessions, and model
routing. The roboclaws side:

- `roboclaws/openclaw/transport.py` — `OpenClawBridge`: HTTP client to
  the Gateway, retry on read timeout, fail-fast on connect / 4xx / 5xx.
- `roboclaws/openclaw/bridge.py` — `OpenClawProvider`: a
  `VLMProvider`-compatible wrapper that uses `OpenClawBridge`. Tracked
  via `ProviderStatus`.
- `roboclaws/openclaw/skill.py` — `AI2THORNavigatorSkill`: wraps a
  provider with a SOUL preset for use as an OpenClaw skill.
- `roboclaws/openclaw/vision_bridge.py` — `VisionBridge`: image-to-text
  bridge for vision-light models (e.g., MiMo text variants).

### 3. Direct coding-agent driver

`examples/coding_agent_nav_server.py`. Boots `MultiAgentEngine` +
`RoboclawsMCPServer` over HTTP. No Gateway, no VLM key needed
server-side — the coding agent (Codex / Claude Code) is the model.
Output: `output/coding-agent-nav/<timestamp>/`. Operating instructions
for the agent itself live in
[`skills/ai2thor-navigator/SKILL.md`](skills/ai2thor-navigator/SKILL.md).

### 4. Railway appliance

`Dockerfile.railway` + `deploy/railway/`. Single container bundling
AI2-THOR + xvfb + nginx + supervisord + the OpenClaw Gateway + the MCP
server + `reset_server.py` (HTTP `/reset`). Public surface is nginx on
`:8080` with auth via `OPENCLAW_TOKEN` / `DEMO_PASSWORD`. Env-driven
config seeded by `scripts/appliance_seed_openclaw.py`. Full deploy
runbook: [`docs/railway-deploy.md`](docs/railway-deploy.md).

## Code map

| Path | Role |
|------|------|
| `roboclaws/core/engine.py` | `MultiAgentEngine`: AI2-THOR controller wrapper, owns scene + cameras (overhead orthographic + per-agent chase), reachable-positions cache. Public API: `step`, `reset`, `get_agent_state`, `get_overhead_frame`, `add_chase_cam`. |
| `roboclaws/core/views.py` | View composition: `NavigationViewContext` (per-scene stable state) + `NavigationPromptBundle` (per-turn render). Outputs the `map-v2+chase` view variant — FPV + structured overhead + chase cam. |
| `roboclaws/core/visualizer.py` | `GameVisualizer`: lower-level overhead/structured map rendering. Called by `views.py`. |
| `roboclaws/core/vlm.py` | `VLMProvider` protocol + `create_provider()` factory. Concrete providers: `MockProvider`, `OpenAIProvider`, `KimiProvider`, `KimiCodingProvider`, `AnthropicProvider`, `NvidiaProvider`, `MimoProvider`. Tracks per-provider health via `ProviderStatus`. Owns SOUL loading (`load_agent_souls`). |
| `roboclaws/core/replay.py` | `ReplayRecorder`: per-step capture (frames, overhead, prompt state, response). Persists to `replay.json` + per-step PNG dirs (`frames/`, `agent_frames/`, `overhead/`, `scene_views/`). Optional GIF. |
| `roboclaws/games/territory.py` | `TerritoryGame`: adversarial cell-claiming. Tracks `cells_claimed`, `connectivity_ratio`, `blocking_events`. |
| `roboclaws/games/coverage.py` | `CoverageGame`: cooperative coverage. Tracks `coverage_pct`, per-agent `contribution`, `work_balance`. |
| `roboclaws/games/common.py` | Shared action set + `SAFE_FALLBACK_ACTION = "RotateRight"`. |
| `roboclaws/openclaw/mcp_server.py` | `RoboclawsMCPServer`: FastMCP server exposing `observe` / `move` / `done`. Owns trace.jsonl, snapshot archiving, human-message queue, blind-move warnings. |
| `roboclaws/openclaw/bridge.py` | `OpenClawProvider`: VLMProvider that talks to a Gateway. |
| `roboclaws/openclaw/transport.py` | `OpenClawBridge`: HTTP transport for the Gateway, retry policy. |
| `roboclaws/openclaw/skill.py` | `AI2THORNavigatorSkill`: wraps a provider as an OpenClaw skill with SOUL injection. |
| `roboclaws/openclaw/vision_bridge.py` | `VisionBridge`: image-to-text for vision-light models. |
| `roboclaws/openclaw/reset_server.py` | HTTP `/reset` for appliance scene resets (loopback-only). |
| `roboclaws/openclaw/diagnostics.py` | Replay-loading utilities (`load_replay_turn`). |
| `examples/territory_game.py`, `coverage_game.py` | Mode 1 entry points. |
| `examples/coding_agent_nav_server.py` | Mode 3 entry point (no Gateway). |
| `examples/openclaw_demo.py`, `openclaw_nav_autonomous.py`, `openclaw_photo_task.py`, `openclaw_interactive.py` | Mode 2 entry points (Gateway). |
| `Dockerfile.railway`, `deploy/railway/` | Mode 4 entry point + supervisord/nginx config. |
| `skills/ai2thor-navigator/SKILL.md` | Operating instructions for any agent driving the robot via MCP — shared by OpenClaw skills, Codex, and Claude Code. |
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
- **MCP runs** (`mcp_server.py`) — used by Modes 2 / 3 / 4. Produces
  `trace.jsonl` (one line per tool call), `run_result.json` on done, and
  labeled snapshots in `<run_dir>/snapshots/agent-<id>/`. Default output:
  `output/coding-agent-nav/<timestamp>/` (Mode 3) or
  `output/openclaw-*/<timestamp>/` (Mode 2).

The `latest.fpv.png` / `latest.map.png` / `latest.chase.png` symlinks
under `snapshots/agent-<id>/` are written on every observe (labeled or
not) and power the `make chat-view` live viewer.

## Pointers

| What you want | Where it lives |
|---------------|----------------|
| Scenario design rationale, VLM strategy, references | [`docs/technical-design.md`](docs/technical-design.md) |
| Atomic architectural decisions (platform choice, deferred integrations) | [`docs/adr/`](docs/adr/) |
| Direct coding-agent driver setup (Mode 3) | [`docs/coding-agent-nav-server.md`](docs/coding-agent-nav-server.md) |
| OpenClaw local setup (Mode 2) | [`docs/openclaw-local.md`](docs/openclaw-local.md) |
| OpenClaw Gateway internals | [`docs/openclaw-gateway-internals.md`](docs/openclaw-gateway-internals.md) |
| Railway appliance deploy (Mode 4) | [`docs/railway-deploy.md`](docs/railway-deploy.md) |
| Verified models per provider | [`docs/model-matrix.md`](docs/model-matrix.md) |
| Operating rules for any agent driving the robot | [`skills/ai2thor-navigator/SKILL.md`](skills/ai2thor-navigator/SKILL.md) |
| Active phase plan | `PLAN.md` (current) + `.planning/STATE.md` (GSD-managed) |
| Shipped-phase history | `docs/retrospectives/` |
