# Roboclaws

[![CI (main)](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml)
[![Live Smoke Reports](https://img.shields.io/badge/live%20smoke-GitHub%20Pages-0A66C2)](https://miaodx.com/roboclaws/)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![Install](https://img.shields.io/badge/install-uv%20recommended-5E5CE6)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

**AI coding agents, VLM agents, and OpenClaw-style robot assistants driving simulated worlds: AI2-THOR today, MolmoSpaces next.**

![Roboclaws robot navigation banner](docs/assets/readme-hero.png)

Roboclaws is a small robotics-agent lab with one practical goal: make embodied
agent behavior visible. The core loop stays deliberately simple: an agent sees,
moves, calls tools, and leaves replayable evidence. Today that loop runs on
AI2-THOR; the next substrate target is MolmoSpaces for object-rich navigation
and manipulation.

> Operational hint: if the live smoke reports look stale, check the
> `CI (main)` badge first. GitHub Pages republishes only after CI succeeds on
> `main`.

## Choose a Path

| Path | Use it for | Entry point |
|------|------------|-------------|
| Direct VLM games | Fast AI2-THOR territory / coverage experiments | `examples/territory_game.py`, `examples/coverage_game.py` |
| OpenClaw / RobotClaws | Assistant-style robot skills, SOULs, browser Control UI | `just openclaw::run nav`, `just chat::run` |
| Coding-agent MCP | Let Codex or Claude Code drive the robot with `observe`, `move`, `done` | `examples/coding_agent_nav_server.py` |
| Reports + appliance | Replayable demos, hosted UI, CI-safe artifacts | `python scripts/generate_demo_report.py --output-dir output/demo`, `DEMO_PASSWORD=demo just appliance::run local` |
| Next substrate | MolmoSpaces spike for richer scenes and manipulation | see [`docs/research-checkpoints/2026-04.md`](docs/research-checkpoints/2026-04.md) |

![Roboclaws control paths](docs/assets/readme-control-paths.png)

## Architecture

![Roboclaws architecture](docs/architecture.svg)

One simulation core, several drivers: direct VLM policies, OpenClaw Gateway,
coding agents over MCP, and a hosted appliance. See [`ARCHITECTURE.md`](ARCHITECTURE.md)
for the code map and [`docs/research-checkpoints/2026-04.md`](docs/research-checkpoints/2026-04.md)
for the OpenClaw / harness / MolmoSpaces direction.

## Quick Start

```bash
uv pip install -e ".[dev,openclaw]" || python -m pip install -e ".[dev,openclaw]"
```

For real VLM/OpenClaw runs, load one provider key:

```bash
export KIMI_API_KEY=...       # Kimi / Moonshot
export MIMO_TP_KEY=...        # MiMo, used by the interactive chat defaults
export NV_API_KEY=...         # NVIDIA NIM
export ANTHROPIC_API_KEY=...  # Claude direct VLM path
export OPENAI_API_KEY=...     # OpenAI direct VLM path
```

### Run a Game

```bash
python examples/territory_game.py --agents 3 --scene FloorPlan201
python examples/coverage_game.py --agents 3 --scene FloorPlan201
```

### Run OpenClaw

```bash
just openclaw::run nav
just chat::run
```
`just openclaw::run nav` is the canonical entrypoint.
`just chat::run` opens the local browser-control workflow. Useful companion
terminals:

```bash
just chat::tail
just chat::view
```

> Recipes are run via [`just`](https://just.systems/) — see
> [`docs/contributing.md`](docs/contributing.md) for the one-line install +
> tab-completion setup. `just --list` shows everything grouped by module.

### Let Codex or Claude Drive the Robot

Terminal 1:

```bash
python examples/coding_agent_nav_server.py --scene FloorPlan201
```

Terminal 2:

```bash
codex mcp add roboclaws --url http://127.0.0.1:18788/mcp
# or
claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp
```

Then start Codex or Claude Code in this repo and ask it to read
`skills/ai2thor-navigator/SKILL.md`, call `roboclaws__observe` first, and
use labeled observes as photos.

Full guide: [docs/coding-agent-nav-server.md](docs/coding-agent-nav-server.md).

## Live Reports

Every successful push to `main` publishes interactive artifacts to GitHub
Pages. Reports include first-person frames, map/chase views, replay GIFs,
tool traces, and run metrics.

| Territory Control | Cooperative Coverage |
|-------------------|----------------------|
| ![territory demo](docs/preview/territory.gif) | ![coverage demo](docs/preview/coverage.gif) |
| [Mock report](https://miaodx.github.io/roboclaws/territory/report.html) | [Mock report](https://miaodx.github.io/roboclaws/coverage/report.html) |

| Stack | Territory | Coverage |
|-------|-----------|----------|
| Mock CI | [report](https://miaodx.github.io/roboclaws/territory/report.html) | [report](https://miaodx.github.io/roboclaws/coverage/report.html) |
| Kimi + real AI2-THOR | [report](https://miaodx.github.io/roboclaws/smoke/territory/report.html) | [report](https://miaodx.github.io/roboclaws/smoke/coverage/report.html) |
| OpenClaw + Kimi | [territory](https://miaodx.github.io/roboclaws/openclaw/territory/report.html) | [coverage](https://miaodx.github.io/roboclaws/openclaw/coverage/report.html) |

OpenClaw navigation report:
[openclaw/demo/report.html](https://miaodx.github.io/roboclaws/openclaw/demo/report.html)

A side-by-side report comparison view is also available:
[report_compare.html](https://miaodx.github.io/roboclaws/report_compare.html).

## Core Demos

### Territory Control

Two or three robots compete over a discrete grid in an iTHOR living room.
Each cell belongs to the first robot that reaches it. The interesting behavior
is strategic: rapid expansion, blocking, and route recovery when an agent gets
stuck.

### Cooperative Coverage

Robots work together to see as much of the room as possible. The report shows
coverage progress, work balance, and whether agents divide the room in useful
ways.

### Observation and Photo Tasks

The single-agent navigation loop is the smallest surface for debugging model
behavior. The photo-task smoke builds on it: the agent moves around
FloorPlan201, calls `observe(label="...")` for chairs/sofas, then finishes with
`done`. The same observation contract is the bridge toward richer MolmoSpaces
tasks.

![Roboclaws photo task](docs/assets/readme-photo-task.png)

```bash
just openclaw::run photo
python scripts/check_photo_task.py --run-dir output/openclaw-photo-task/<timestamp>
```

## Documentation Map

- [Architecture](ARCHITECTURE.md) — code map, four operating modes, MCP contract
- [Architecture Decision Records](docs/adr/) — atomic decisions (platform choice, deferred integrations)
- [Direct Codex/Claude robot driver](docs/coding-agent-nav-server.md)
- [OpenClaw demo guide](docs/openclw/openclaw-demo.md)
- [OpenClaw local guide](docs/openclw/openclaw-local.md)
- [OpenClaw Gateway internals](docs/openclw/openclaw-gateway-internals.md)
- [Model matrix](docs/model-matrix.md)
- [Railway deploy runbook](docs/railway-deploy.md)
- [Railway appliance plan](docs/railway-openclaw-appliance-plan.md)
- [Technical design](docs/technical-design.md)
- [Contributing](docs/contributing.md)

## Related Projects

- [Roboharness](https://github.com/MiaoDX/roboharness) — visual testing harness for AI coding agents in robot simulation
- [Robowbc](https://github.com/MiaoDX/robowbc) — whole-body-control experiments
- [OpenClaw](https://github.com/openclaw/openclaw) — open-source personal AI assistant
- [ROSClaw](https://github.com/PlaiPin/rosclaw) — OpenClaw to ROS 2 bridge
- [AI2-THOR](https://github.com/allenai/ai2thor) — interactive 3D indoor simulation

## License

MIT
