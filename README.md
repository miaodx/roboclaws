# Roboclaws 🦞🤖

[![CI (main)](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml)
[![Live Smoke Reports](https://img.shields.io/badge/live%20smoke-GitHub%20Pages-0A66C2)](https://miaodx.com/roboclaws/)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![Install](https://img.shields.io/badge/install-uv%20recommended-5E5CE6)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

**Multiple OpenClaw Agents Controlling Multiple Simulated Robots: Competition & Cooperation**

> The first OpenClaw multi-agent simulated robotics demo
>
> Operational hint: if the live smoke reports look stale, check the `CI (main)` badge first. GitHub Pages republishes only after both `Lint & mock tests` and `Real-model smoke test (Kimi)` succeed on `main`.

## What is this

Roboclaws lets multiple VLM/OpenClaw agent instances simultaneously control robots in a simulated environment, competing (territory control) or cooperating (area coverage). Each robot is driven by an independent AI agent that makes navigation decisions from first-person camera views.

## Two Game Scenarios

**🗺️ Territory Control (Adversarial)** — 2-3 robots compete in an indoor scene. Cells you walk over become yours; others can't claim them. Choose between rapid expansion or blocking your opponents' paths.

**📸 Cooperative Coverage** — 2-3 robots collaboratively explore an entire room. Goal: reach 95% area coverage as fast as possible. Robots must autonomously decide who goes where.

## Live Visualization

Every CI run produces a self-contained, interactive `report.html` per game — step slider, overhead map, per-agent first-person frames, SVG metrics chart, and the full VLM reasoning log. Three stacks run in parallel, from cheapest to most realistic:

### 1. Mock engine — every push, every branch

Synthetic frames, no Unity, no API keys. Validates the visualization + reporting pipeline on every PR.

| 🗺️ Territory Control | 📸 Cooperative Coverage |
|---|---|
| ![territory demo](docs/preview/territory.gif) | ![coverage demo](docs/preview/coverage.gif) |
| [▶ Interactive report](https://miaodx.github.io/roboclaws/territory/report.html) | [▶ Interactive report](https://miaodx.github.io/roboclaws/coverage/report.html) |

### 2. Kimi on real AI2-THOR — push to `main`

Real `FloorPlan201` rendered by Unity, first-person frames fed to the Kimi VLM. Produced by the `real-model-smoke` job. Runs up to 100 steps per game so the ground-truth termination logic (all reachable cells claimed, or 95% area covered) actually fires.

| 🗺️ Territory Control | 📸 Cooperative Coverage |
|---|---|
| ![kimi territory](https://miaodx.github.io/roboclaws/smoke/territory/replay.gif) | ![kimi coverage](https://miaodx.github.io/roboclaws/smoke/coverage/replay.gif) |
| [▶ Interactive report](https://miaodx.github.io/roboclaws/smoke/territory/report.html) | [▶ Interactive report](https://miaodx.github.io/roboclaws/smoke/coverage/report.html) |

### 3. OpenClaw + Kimi — push to `main`

Routes the same three demos through a long-running local Gateway with per-agent personalities
(aggressive / defensive / cooperative SOULs from `skills/ai2thor-navigator/souls/`).
Layer 3 GIFs include SOUL badges + colored trails — aggressive=red, defensive=blue, cooperative=green.

**First local run takes ~15 min** (Docker pull + Unity download).

Quickest local path:
- [OpenClaw demo guide](docs/openclaw-demo.md) — shortest route to `examples/openclaw_demo.py`
- [OpenClaw local guide](docs/openclaw-local.md) — full local matrix (games, interactive chat, autonomous MCP, provider/model notes)

| Demo | GIF | Report |
|------|-----|--------|
| Navigation | ![nav](https://miaodx.github.io/roboclaws/openclaw/demo/replay.gif) | [▶ report](https://miaodx.github.io/roboclaws/openclaw/demo/report.html) |
| Territory  | ![ter](https://miaodx.github.io/roboclaws/openclaw/territory/replay.gif) | [▶ report](https://miaodx.github.io/roboclaws/openclaw/territory/report.html) |
| Coverage   | ![cov](https://miaodx.github.io/roboclaws/openclaw/coverage/replay.gif) | [▶ report](https://miaodx.github.io/roboclaws/openclaw/coverage/report.html) |

Also available: [A/B comparison view](https://miaodx.github.io/roboclaws/report_compare.html) (two mock runs side-by-side).

> All reports are regenerated on every push to `main` and published to GitHub Pages by the CI workflow. To regenerate the mock demos locally: `python scripts/generate_demo_report.py --output-dir output/demo`.

## Quick Start

```bash
uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"

# Single agent exploration
python examples/single_agent_explore.py

# Territory control (3 agents)
python examples/territory_game.py --agents 3 --scene FloorPlan201

# Cooperative coverage (3 agents)
python examples/coverage_game.py --agents 3 --scene FloorPlan201
```

Set a VLM API key:
```bash
export KIMI_API_KEY=...            # Kimi / Moonshot
# or
export ANTHROPIC_API_KEY=sk-...    # Claude
# or
export OPENAI_API_KEY=sk-...       # GPT-4o / GPT-4o-mini
```

## Architecture

```
VLM Agent 0 ──┐
VLM Agent 1 ──┤── Game Controller ── AI2-THOR (multi-agent sim)
VLM Agent 2 ──┘

Per-step loop:
screenshot → generate overhead map → build prompt → VLM decision → execute action → log replay
```

Phase 1 calls VLM APIs directly (Claude/GPT-4o). Phase 2 integrates OpenClaw Gateway for persistent agent memory and multi-channel communication.

## Roadmap

- [x] **Phase 0**: Technical research & design
- [ ] **Phase 1**: AI2-THOR + VLM API multi-agent competition/cooperation demo
- [x] **Phase 2**: OpenClaw integration (Skill + Gateway + memory)
- [x] **Phase 2.2**: long-running OpenClaw games (territory + coverage) with per-agent SOULs
- [ ] **Phase 3**: Isaac Lab migration (G1 humanoid + RL locomotion policy)

## Related Projects

- [Roboharness](https://github.com/MiaoDX/roboharness) — Visual testing harness for AI coding agents in robot simulation
- [Robowbc](https://github.com/MiaoDX/robowbc) — Whole Body Control experiments
- [OpenClaw](https://github.com/openclaw/openclaw) — Open-source personal AI assistant
- [ROSClaw](https://github.com/PlaiPin/rosclaw) — OpenClaw ↔ ROS 2 bridge
- [AI2-THOR](https://github.com/allenai/ai2thor) — Interactive 3D indoor simulation

## License

MIT
