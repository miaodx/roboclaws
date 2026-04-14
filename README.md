# Roboclaws 🦞🤖

**Multiple OpenClaw Agents Controlling Multiple Simulated Robots: Competition & Cooperation**

> The first OpenClaw multi-agent simulated robotics demo

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

Same VLM, but routed through the OpenClaw Gateway so each agent has a persistent `MEMORY.md`, a `SOUL.md` persona, and shows up as a first-class entity in the Gateway. Proves Phase 2 end-to-end. **Coming online with [#39](https://github.com/MiaoDX/roboclaws/issues/39)**; GIFs below auto-populate once the job turns green.

| 🗺️ Territory Control | 📸 Cooperative Coverage |
|---|---|
| ![openclaw territory](https://miaodx.github.io/roboclaws/openclaw/territory/replay.gif) | ![openclaw coverage](https://miaodx.github.io/roboclaws/openclaw/coverage/replay.gif) |
| [▶ Interactive report](https://miaodx.github.io/roboclaws/openclaw/territory/report.html) | [▶ Interactive report](https://miaodx.github.io/roboclaws/openclaw/coverage/report.html) |

Also available: [A/B comparison view](https://miaodx.github.io/roboclaws/report_compare.html) (two mock runs side-by-side).

> All reports are regenerated on every push to `main` and published to GitHub Pages by the CI workflow. To regenerate the mock demos locally: `python scripts/generate_demo_report.py --output-dir output/demo`.

## Quick Start

```bash
pip install -e ".[dev]"

# Single agent exploration
python examples/single_agent_explore.py

# Territory control (3 agents)
python examples/territory_game.py --agents 3 --scene FloorPlan201

# Cooperative coverage (3 agents)
python examples/coverage_game.py --agents 3 --scene FloorPlan201
```

Set a VLM API key:
```bash
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
- [ ] **Phase 2**: OpenClaw integration (Skill + Gateway + memory)
- [ ] **Phase 3**: Isaac Lab migration (G1 humanoid + RL locomotion policy)

## Related Projects

- [Roboharness](https://github.com/MiaoDX/roboharness) — Visual testing harness for AI coding agents in robot simulation
- [Robowbc](https://github.com/MiaoDX/robowbc) — Whole Body Control experiments
- [OpenClaw](https://github.com/openclaw/openclaw) — Open-source personal AI assistant
- [ROSClaw](https://github.com/PlaiPin/rosclaw) — OpenClaw ↔ ROS 2 bridge
- [AI2-THOR](https://github.com/allenai/ai2thor) — Interactive 3D indoor simulation

## License

MIT
