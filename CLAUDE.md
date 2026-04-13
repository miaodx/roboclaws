# Roboclaws

Multiple VLM/OpenClaw agents controlling simulated robots in competition and cooperation. Python 3.10+, AI2-THOR simulation.

## Required reading

Before writing any code, read in order:
1. `CLAUDE.md` (this file)
2. `docs/technical-design.md` (full technical spec: API details, game rules, architecture)

## Build & test

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

Run demos (requires AI2-THOR, auto-downloads Unity build ~1GB):
```bash
# Requires a VLM API key
export ANTHROPIC_API_KEY=sk-...

python examples/single_agent_explore.py
python examples/territory_game.py --agents 3
python examples/coverage_game.py --agents 3
```

## Code style

- Ruff enforces style — do not duplicate linter rules here
- Line length: 100
- Target: Python 3.10
- Type annotations on public APIs; `from __future__ import annotations` in all modules

## Architecture

- `roboclaws/core/engine.py` — AI2-THOR controller wrapper, multi-agent management
- `roboclaws/core/vlm.py` — Unified VLM API interface (Claude Sonnet, GPT-4o, GPT-4o-mini)
- `roboclaws/core/visualizer.py` — Overhead map generation, frame compositing, GIF output
- `roboclaws/core/replay.py` — Game replay recording (frames + state JSON)
- `roboclaws/games/territory.py` — Territory control game logic
- `roboclaws/games/coverage.py` — Cooperative coverage game logic
- `roboclaws/openclaw/` — OpenClaw Skill + Gateway bridge (Phase 2)
- `examples/` — Directly runnable demo scripts

### AI2-THOR key APIs

```python
# Multi-agent initialization
controller = Controller(scene="FloorPlan201", agentCount=3, gridSize=0.25)

# Control a single agent (one agent per step() call)
event = controller.step(action="MoveAhead", agentId=1)

# Get each agent's independent frame and state
frame = event.events[agent_id].frame  # numpy (H, W, 3)
pos = event.events[agent_id].metadata['agent']['position']

# Overhead view
event = controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)
```

**Important notes:**
- iTHOR scenes support multi-agent; ProcTHOR does NOT (known bugs)
- Agents physically collide — they cannot pass through each other
- Agents are visible in each other's camera views
- Scene ranges: FloorPlan1-30 (kitchens), 201-230 (living rooms), 301-330 (bedrooms), 401-430 (bathrooms)

### VLM call pattern

```python
# Each agent's per-step prompt includes:
# 1. First-person camera frame (base64 JPEG)
# 2. Overhead grid map (marking all agent positions + game state)
# 3. Structured JSON (position, score, remaining steps, etc.)
#
# VLM returns JSON: {"reasoning": "...", "action": "MoveAhead"}
```

## Git workflow

- Branch from `main`
- Commit messages: `type: description` (feat, fix, ci, docs, refactor)
- PR strategy: push fixes to the PR's source branch, don't open a new PR

## Design principles

| Principle | Practice |
|-----------|----------|
| **Thin & focused** | Not a heavy framework; give a good model enough context and it runs |
| **Make it work first** | Day 1-2: simplest pipeline to validate core hypothesis. Day 3+: add OpenClaw |
| **Visualization first** | Every feature must produce visible output (screenshots/GIFs/video) |
| **Cost-aware** | Default to GPT-4o-mini for dev; switch to Claude/GPT-4o for final demos |

## Gotchas

- AI2-THOR downloads a Unity build (~1GB) on first run
- AI2-THOR on Linux requires X server or headless rendering (`ai2thor[headless]`)
- macOS may need additional AI2-THOR rendering configuration
- VLM API cost: 3 agents × 200 steps ≈ $0.02 (GPT-4o-mini) to $0.36 (Claude Sonnet)
- `controller.step()` is synchronous, one agent per call — game engine uses turn-based stepping
