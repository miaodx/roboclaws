# Roboclaws 🦞🤖

**Multiple OpenClaw Agents Controlling Multiple Simulated Robots: Competition & Cooperation**

> The first OpenClaw multi-agent simulated robotics demo

## What is this

Roboclaws lets multiple VLM/OpenClaw agent instances simultaneously control robots in a simulated environment, competing (territory control) or cooperating (area coverage). Each robot is driven by an independent AI agent that makes navigation decisions from first-person camera views.

## Two Game Scenarios

**🗺️ Territory Control (Adversarial)** — 2-3 robots compete in an indoor scene. Cells you walk over become yours; others can't claim them. Choose between rapid expansion or blocking your opponents' paths.

**📸 Cooperative Coverage** — 2-3 robots collaboratively explore an entire room. Goal: reach 95% area coverage as fast as possible. Robots must autonomously decide who goes where.

## Live Visualization

Every CI run produces a self-contained, interactive `report.html` per game — step slider, overhead map, per-agent first-person frames, SVG metrics chart, and the full VLM reasoning log. Preview frames below; click the links for the full browsable reports.

| Territory Control | Cooperative Coverage |
|---|---|
| ![territory demo](docs/preview/territory.gif) | ![coverage demo](docs/preview/coverage.gif) |
| [▶ Interactive report](https://miaodx.github.io/roboclaws/territory/report.html) | [▶ Interactive report](https://miaodx.github.io/roboclaws/coverage/report.html) |

Also available:

- 🎮 [**Real AI2-THOR + Kimi run**](https://miaodx.github.io/roboclaws/smoke/territory/report.html) — actual FloorPlan201 indoor scene rendered by Unity, driven by the Kimi VLM. Produced by the `real-model-smoke` CI job on every push to `main`.
- [A/B comparison view](https://miaodx.github.io/roboclaws/report_compare.html) — two mock runs side-by-side.

The above two games use a mock engine so every branch push produces visualizations quickly without the ~1 GB AI2-THOR Unity build; the linked real-model report is the genuine simulated view.

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
