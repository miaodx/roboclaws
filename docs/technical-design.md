# Roboclaws Technical Design Document

> Multiple OpenClaw agents controlling simulated robots in competition and cooperation

## Project Positioning

Roboclaws is a thin, focused demo repository that validates "multiple OpenClaw/VLM agent instances simultaneously controlling multiple simulated robots for adversarial and cooperative tasks." Not a heavy framework — an experiment platform where giving a good model enough context lets it run autonomously.

**Core hypothesis:** If a VLM (Claude/GPT-4o) can see the simulation camera feed, it can make reasonable navigation and strategic decisions to control a robot.

**Community differentiation:** As of April 2026, no one in the OpenClaw community has publicly demonstrated multiple OpenClaw instances simultaneously controlling multiple simulated robots in competition/cooperation. We are the first.

## Technology Selection

### Why AI2-THOR (Phase 1)

After surveying MolmoSpaces, Isaac Lab, ManiSkill3, Habitat 3.0/PARTNR, and MuJoCo Gymnasium:

| Platform | Multi-agent | Indoor scenes | Setup time | GPU required |
|----------|-------------|---------------|------------|-------------|
| **AI2-THOR (iTHOR)** | **Native** | 120 scenes | **Half day** | No |
| MolmoSpaces | Not supported | 230K scenes | 1-2 days | MuJoCo: No |
| Isaac Lab | DirectMARLEnv | Must build | 1-2 weeks | Yes |
| ManiSkill3 | Supported | Manipulation focus | 3-5 days | Yes |
| Habitat 3.0/PARTNR | Supported | 60 houses | 1 week+ | Yes |

Key exclusion reasons:
- **MolmoSpaces**: Latest and most comprehensive (230K scenes), but no multi-agent support — excluded immediately
- **Isaac Lab**: No ready-made indoor scenes; building custom USD scenes is unrealistic for a 2-3 day PoC
- **Habitat 3.0/PARTNR**: Most mature multi-agent solution (100K tasks), but setup complexity far exceeds PoC requirements

### Why not Isaac Lab yet (Phase 3)

Isaac Lab's value is in the long-term pipeline: AGILE framework for G1 locomotion, COMPASS cross-embodiment navigation, GR00T N1.6 VLA pipeline. Introduced in Phase 3.

## AI2-THOR Multi-Agent Technical Specs

### Initialization

```python
from ai2thor.controller import Controller

controller = Controller(
    scene="FloorPlan201",   # Living room (FloorPlan201-230)
    agentCount=3,           # 3 agents
    gridSize=0.25,          # Discrete step size 0.25m
    snapToGrid=True,        # Grid-based movement
    rotateStepDegrees=90,   # 90° rotation steps
    fieldOfView=90,
    width=640,
    height=480,
)
```

### Control Model

- **Each `controller.step()` moves only one agent** (via `agentId` parameter)
- Returned event contains all agents' independent state: `event.events[i]`
- Agents **physically collide** — cannot pass through each other
- Agents **are visible in each other's camera views**
- No built-in inter-agent communication — we implement this ourselves

### Per-Agent Data

```python
agent_event = event.events[agent_id]

# Camera frame
rgb_frame = agent_event.frame                    # numpy (H, W, 3)
depth_frame = agent_event.depth_frame            # float32 depth in meters

# Agent state
position = agent_event.metadata['agent']['position']       # {x, y, z}
rotation = agent_event.metadata['agent']['rotation']       # {x, y, z} Euler angles
camera_horizon = agent_event.metadata['agent']['cameraHorizon']

# Visible objects
visible_objects = [o for o in agent_event.metadata['objects'] if o['visible']]

# Action feedback
success = agent_event.metadata['lastActionSuccess']
error = agent_event.metadata['errorMessage']
```

### Overhead View

```python
import copy

event = controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)
pose = copy.deepcopy(event.metadata["actionReturn"])
pose["orthographic"] = True

controller.step(action="AddThirdPartyCamera", **pose, skyboxColor="white")
top_down_frame = controller.last_event.events[0].third_party_camera_frames[-1]
```

### Available Actions

Navigation: `MoveAhead`, `MoveBack`, `MoveLeft`, `MoveRight`, `RotateLeft`, `RotateRight`, `LookUp`, `LookDown`, `Teleport`, `Done`

Object interaction (Phase 3): `PickupObject`, `PutObject`, `OpenObject`, `CloseObject`, `ToggleObjectOn/Off`

### Scene Selection

Use **iTHOR** scenes (not ProcTHOR — multi-agent is buggy):
- Kitchens: FloorPlan1-30
- Living rooms: FloorPlan201-230
- Bedrooms: FloorPlan301-330
- Bathrooms: FloorPlan401-430

Recommended for Phase 1: living rooms (201-230) — larger spaces for multi-agent movement.

## Game Scenario Design

### Scenario A: Territory Control (Adversarial)

**Rules:**
- 2-3 agents in the same room
- Maintain a grid map tracking which cells each agent has claimed
- Each step, agent claims its current cell; already-claimed cells cannot be taken
- Goal: claim more cells (more territory)
- Strategy space: rapid expansion vs. blocking opponents' paths

**VLM receives per step:**
1. Agent's first-person camera frame (base64 JPEG)
2. Overhead grid map (marking self ★, opponents ●, claimed/unclaimed areas)
3. Structured JSON metadata (position, rotation, score, remaining steps)

**VLM outputs:**
```json
{"reasoning": "Opponent is north, I should claim southeast corner first...", "action": "MoveAhead"}
```

**Termination:** All reachable cells claimed OR max steps reached (e.g., 200)

**Metrics:**
- Cells claimed per agent
- Territory connectivity (contiguous vs. fragmented)
- Whether emergent strategies appear (blocking, cutting off)

### Scenario B: Cooperative Coverage

**Rules:**
- 2-3 agents in the same room/apartment
- Maintain a coverage map tracking which areas any agent has "seen"
- Cells within an agent's field of view are marked as "covered"
- Goal: reach 95% coverage as fast as possible

**VLM receives per step:**
1. Agent's first-person camera frame
2. Overhead coverage map (marking self, teammates, covered/uncovered areas)
3. Teammates' last known positions and headings

**Metrics:**
- Total steps to reach 95% coverage
- Work balance (each agent's coverage contribution ratio)
- Whether emergent division of labor appears

## System Architecture

### Phase 1: Pure Python + VLM API (Day 1-2)

```
┌─────────────────────────────────────┐
│           Game Controller           │
│  (Python script, game logic+state)  │
│                                     │
│  ┌───────────┐  ┌───────────┐      │
│  │ Agent 0   │  │ Agent 1   │ ...  │
│  │ VLM call  │  │ VLM call  │      │
│  └─────┬─────┘  └─────┬─────┘      │
│        │              │             │
│        ▼              ▼             │
│  ┌──────────────────────────┐      │
│  │      AI2-THOR Engine     │      │
│  │  (agentCount=N, iTHOR)   │      │
│  └──────────────────────────┘      │
└─────────────────────────────────────┘

Per-step loop:
1. Get each agent's camera frame + metadata from AI2-THOR
2. Update game state (grid map / coverage map)
3. Generate overhead visualization
4. Build prompt per agent (frame + map + state JSON)
5. Call VLM API (Claude/GPT-4o) for action decision
6. Parse VLM output, execute controller.step(action=..., agentId=i)
7. Record replay data
```

### Phase 2: OpenClaw Integration (Day 3-5)

Wrap Phase 1's direct VLM calls as OpenClaw skills:
- Each agent maps to an OpenClaw instance (via Gateway multi-agent routing bindings)
- Each instance has independent SOUL.md (strategy personality) and MEMORY.md (map memory)
- Connect to Telegram/Discord for real-time human observation and intervention

### Phase 3: Isaac Lab Migration (Week 2+)

- Use existing G1 velocity control pipeline
- Two-level architecture: OpenClaw VLM planner (1-5 Hz) + RL locomotion policy (200 Hz)
- Bridge via ROSClaw or direct Python integration
- Scenes from Omniverse USD assets or MolmoSpaces conversion

## VLM Strategy

### Model Selection

| Use case | Recommended model | Reason |
|----------|------------------|--------|
| Development | GPT-4o-mini | $0.002/100 steps, fast iteration |
| Final demo | Claude Sonnet 4.6 / GPT-4o | Better spatial reasoning |
| Multi-agent at scale | Local Qwen-VL / VILA | Zero marginal cost |

### Prompt Structure

```
[System] You are a robot agent navigating an indoor environment. You are competing/cooperating
with other agents. Based on what you see and the map information, choose your next action.

[User]
<image: first-person camera frame>
<image: overhead map marking you (★) and opponents (●)>

Current state:
- Position: (1.25, 0, -2.5), facing: East
- Your territory: 23 cells, opponent territory: 18 cells
- Remaining steps: 157
- Last action: MoveAhead (success)

Available actions: MoveAhead, MoveBack, RotateLeft, RotateRight, Done

Reply in JSON: {"reasoning": "...", "action": "..."}
```

### Cost Estimates

320×240 image + overhead map, 2 images per step:
- GPT-4o-mini: ~$0.00003/step → 3 agents × 200 steps = **$0.018/game**
- GPT-4o: ~$0.0004/step → 3 agents × 200 steps = **$0.24/game**
- Claude Sonnet: ~$0.0006/step → 3 agents × 200 steps = **$0.36/game**

## Implementation Plan

### Day 1: Single-Agent VLM Navigation Loop

**Goal:** One agent in an AI2-THOR living room, VLM sees camera frame and makes reasonable navigation decisions.

**Deliverables:**
- `roboclaws/core/engine.py` — AI2-THOR controller wrapper
- `roboclaws/core/vlm.py` — VLM API wrapper (supports Claude/GPT-4o/GPT-4o-mini)
- `roboclaws/core/visualizer.py` — Overhead map + first-person frame compositing
- `examples/single_agent_explore.py` — Single-agent free exploration demo

### Day 2: Multi-Agent Game Logic

**Goal:** 2-3 agents in the same scene, running territory control and cooperative coverage.

**Deliverables:**
- `roboclaws/games/territory.py` — Territory control game logic
- `roboclaws/games/coverage.py` — Cooperative coverage game logic
- `roboclaws/core/replay.py` — Game replay recording (frame sequences + state logs)
- `examples/territory_game.py` — 2v1 or 3-player territory control
- `examples/coverage_game.py` — 3-agent cooperative coverage
- Screen recordings / GIFs showing emergent behaviors

### Day 3-5: OpenClaw Integration

**Goal:** Each agent controlled by an OpenClaw instance, interactive via Telegram.

**Deliverables:**
- `roboclaws/openclaw/skill.py` — OpenClaw skill wrapper
- `roboclaws/openclaw/bridge.py` — AI2-THOR ↔ OpenClaw Gateway bridge
- `skills/ai2thor-navigator/SKILL.md` — OpenClaw skill definition
- Per-agent SOUL.md templates

### Week 2+: Isaac Lab Version

**Deliverables:**
- `roboclaws/isaac/` — Isaac Lab integration module
- Two-level architecture (VLM planning + RL locomotion)
- G1 velocity control integration
- ROSClaw bridge

## File Structure

```
roboclaws/
├── README.md
├── CLAUDE.md
├── AGENTS.md
├── LICENSE
├── pyproject.toml
├── docs/
│   ├── technical-design.md          # This document
│   └── research/                    # Research reports for periodic review
├── roboclaws/
│   ├── __init__.py
│   ├── core/
│   │   ├── engine.py               # AI2-THOR controller wrapper
│   │   ├── vlm.py                  # VLM API calls (Claude/GPT)
│   │   ├── visualizer.py           # Overhead map, frame compositing
│   │   └── replay.py               # Game replay
│   ├── games/
│   │   ├── territory.py            # Territory control
│   │   └── coverage.py             # Cooperative coverage
│   └── openclaw/
│       ├── skill.py                # OpenClaw skill wrapper
│       └── bridge.py               # Gateway bridge
├── examples/
│   ├── single_agent_explore.py
│   ├── territory_game.py
│   └── coverage_game.py
├── skills/
│   └── ai2thor-navigator/
│       └── SKILL.md
└── tests/
```

## References

### AI2-THOR
- Official site: https://ai2thor.allenai.org/
- GitHub: https://github.com/allenai/ai2thor
- Multi-agent examples: https://allenai.github.io/ai2thor-v2.1.0-documentation/examples
- iTHOR scenes: FloorPlan1-30 (kitchens), 201-230 (living rooms), 301-330 (bedrooms), 401-430 (bathrooms)
- MAP-THOR benchmark: https://openreview.net/pdf?id=ZygZN5egzy

### OpenClaw
- Official: https://openclaw.ai/ / https://github.com/openclaw/openclaw
- ROSClaw (ROS 2 bridge): https://github.com/PlaiPin/rosclaw / arXiv:2603.26997
- DimensionalOS (G1 integration): https://github.com/dimensionalOS/dimos
- ClawBody (MuJoCo sim): https://github.com/tomrikert/clawbody
- RoClaw (dual-brain): https://github.com/EvolvingAgentsLabs/RoClaw
- OpenGo (Go2 skills): arXiv:2604.01708
- NemoClaw (NVIDIA safety): https://github.com/NVIDIA/NemoClaw
- Multi-agent routing: https://docs.openclaw.ai/concepts/multi-agent
- Skill docs: https://docs.openclaw.ai/tools/skills

### Simulation Platforms
- MolmoSpaces: https://github.com/allenai/molmospaces / arXiv:2602.11337
- Isaac Lab: https://github.com/isaac-sim/IsaacLab / arXiv:2511.04831
- AGILE (G1 locomotion): https://github.com/nvidia-isaac/WBC-AGILE
- COMPASS (cross-embodiment nav): https://github.com/NVlabs/COMPASS
- GR00T N1.6: https://github.com/NVIDIA/Isaac-GR00T
- ManiSkill3: https://github.com/haosulab/ManiSkill
- Habitat 3.0/PARTNR: https://github.com/facebookresearch/partnr-planner

### VLM Navigation
- ImagineNav (ICLR 2025): VLM view-selection navigation
- SayNav: LLM + 3D scene graph / arXiv:2309.04077
- NaVILA: VLM + RL two-level nav / arXiv:2412.04453
- SPF (See-Point-Fly): VLM pixel-coordinate nav, 100% success (Gemini 2.5 Pro)

### Multi-Agent Cooperation
- RoCo: Multi-robot LLM dialogue / arXiv:2307.04738
- CoELA (ICLR 2024): Cognitive modular LLM agents
- FurnMove (ECCV 2020): AI2-THOR two-agent furniture moving
- LLaMAR (NeurIPS 2024): LLM long-horizon multi-agent planning
- Neural MMO: Competition-driven territorial exploration
- Voyager: LLM open-ended lifelong learning agent
- Concordia: Game Master/Player separation architecture
