# Roboclaws Technical Design Document

> Multiple OpenClaw / VLM agents controlling simulated robots in
> competition and cooperation.

This document captures the **design rationale** for roboclaws: what
problem it's solving, why scenarios are shaped the way they are, and
which model strategy fits the constraints. For *how the code is
organized*, see [`ARCHITECTURE.md`](../../ARCHITECTURE.md). For *individual
architectural decisions* (platform choice, deferred integrations), see
[`docs/adr/`](../adr/).

## Project positioning

Roboclaws is a thin, focused demo repository for embodied-agent demos where
the important thing is not just "the agent succeeded," but whether a reviewer
can see what happened and trust the claim being made.

There are now two project threads:

- **AI2-THOR navigation** validates "multiple OpenClaw / VLM agent instances
  simultaneously controlling multiple simulated robots for adversarial and
  cooperative tasks." Not a heavy framework — an experiment platform where
  giving a good model enough context lets it run autonomously.
- **MolmoSpaces cleanup/proof** validates household cleanup artifact honesty:
  the Cleanup Agent gets a public Agent View, the Scorer keeps private truth
  private, semantic simulator mutations stay labeled `api_semantic`, and
  physical manipulation claims require planner-backed RBY1M/CuRobo proof.

**Core navigation hypothesis:** if a VLM can see the simulation camera feed,
it can make reasonable navigation and strategic decisions to control a robot.

**Core cleanup/proof hypothesis:** a cleanup demo is only useful if it separates
what the agent was allowed to know, how the scene was semantically changed, and
which robot manipulation substeps have real planner-backed evidence.

**Community differentiation:** as of April 2026, no one in the OpenClaw
community has publicly demonstrated multiple OpenClaw instances
simultaneously controlling multiple simulated robots in competition /
cooperation. This is the first.

## Technology selection

The navigation platform is **AI2-THOR (iTHOR scenes)**. See
[ADR-0001](../adr/0001-use-ai2thor-for-phase-1.md) for the original
navigation-platform survey and the decision shape. **Isaac Lab is intentionally
deferred** to Phase 3 — see [ADR-0002](../adr/0002-defer-isaac-lab-to-phase-3.md).

The cleanup/proof platform is **MolmoSpaces** with a real upstream MuJoCo scene
when local runtime assets are available. This was not the Phase 1 navigation
choice, but it became the right layer for household cleanup because it exposes
movable objects, receptacles, semantic state, RBY1M robot views, and planner
proof hooks that AI2-THOR does not provide.

For the OpenClaw integration shape, see
[`openclaw/local.md`](openclaw/local.md) and
[`openclaw/gateway-internals.md`](openclaw/gateway-internals.md).
For the direct coding-agent driver, see
[`coding-agent-nav-server.md`](coding-agent-nav-server.md).

For cleanup/proof settings, see
[`molmospaces-settings.md`](molmospaces-settings.md). For the vocabulary that
keeps Agent View, Private Evaluation, Scorer, and planner-backed proof claims
separate, see [`domain.md`](domain.md).

## Game scenario design

Two scenarios drive the multi-agent demo. Both run on the same
`MultiAgentEngine` (see [`ARCHITECTURE.md`](../../ARCHITECTURE.md)) and the
same view system; what differs is rules + metrics + termination.

### Scenario A: Territory Control (adversarial)

**Rules:**

- 2-3 agents in the same room.
- A grid map tracks which cells each agent has claimed.
- Each step, an agent claims its current cell; already-claimed cells
  cannot be taken.
- Goal: claim more cells than opponents.
- Strategy space: rapid expansion vs. blocking opponents' paths.

**VLM input per step:**

1. Agent's first-person camera frame (base64 JPEG).
2. Overhead grid map marking self (★), opponents (●), and
   claimed / unclaimed areas.
3. Structured JSON metadata (position, rotation, score, remaining steps).

**VLM output:**

```json
{"reasoning": "Opponent is north, I should claim southeast corner first...", "action": "MoveAhead"}
```

**Termination:** all reachable cells claimed OR `max_steps` reached
(default 200).

**Metrics:** cells claimed per agent, territory connectivity (largest
connected component / total claimed), blocking-event count.

### Scenario B: Cooperative Coverage

**Rules:**

- 2-3 agents in the same room or apartment.
- A coverage map tracks which areas any agent has "seen."
- Cells within an agent's field of view become "covered."
- Goal: reach 95% coverage as fast as possible.

**VLM input per step:**

1. Agent's first-person camera frame.
2. Overhead coverage map marking self, teammates, covered / uncovered
   areas.
3. Teammates' last known positions and headings.

**Metrics:** total steps to reach 95% coverage, work balance (per-agent
coverage contribution ratio), emergent division-of-labor signals.

## Cleanup scenario design

MolmoSpaces cleanup demos are structured around a different failure mode than
navigation games. In navigation, the main risk is that an agent gets lost,
collides, or fails to coordinate. In cleanup, the main risk is that an artifact
quietly uses private information or semantic state edits while looking like a
real robot manipulation result.

The cleanup stack therefore keeps four surfaces separate:

- **Agent View** — public map, room-level fixture hints, waypoint observations,
  observed object handles, support estimates, and cleanup tools.
- **Private Evaluation** — hidden generated mess set and acceptable-destination
  truth used only after the run ends.
- **Semantic Cleanup Timeline** — the visible `nav -> pick -> nav -> open? -> place`
  rhythm shared by reports and proof requests.
- **Planner Proof Evidence** — optional local RBY1M/CuRobo proof bundles that
  can promote exact matching cleanup substeps from `api_semantic` to
  `planner_backed`.

This is why the current status can say the cleanup bridge is blocked even when
the visual report is clean: clean semantic cleanup and planner-backed
manipulation proof are intentionally separate gates.

## VLM strategy

### Prompt structure

Each per-step prompt has three components:

```text
[System] You are a robot agent navigating an indoor environment.
You are competing / cooperating with other agents. Based on what you
see and the map information, choose your next action.

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

The prompt is constructed once per agent per step in
`roboclaws/games/territory.py` and `roboclaws/games/coverage.py`. The
same shape is consumed by `RoboclawsMCPServer.observe` when an external
coding agent drives the robot — see
[`ARCHITECTURE.md`](../../ARCHITECTURE.md) for the full contract.

### Model selection

Per-provider verified models and their costs evolve fast — see
[`model-matrix.md`](model-matrix.md) for current data. As a stable
heuristic:

- **Development**: a cheap provider (Kimi / MiMo / GPT-4o-mini). Fast
  iteration, low cost-per-game.
- **Final demo**: a stronger spatial-reasoning model (Claude Sonnet,
  GPT-4o). Better navigation quality, higher cost.
- **Multi-agent at scale**: local Qwen-VL / VILA against a local
  OpenClaw deployment. Marginal cost approaches zero.

## References

### AI2-THOR

- Official site: https://ai2thor.allenai.org/
- GitHub: https://github.com/allenai/ai2thor
- Multi-agent examples: https://allenai.github.io/ai2thor-v2.1.0-documentation/examples
- iTHOR scene ranges: FloorPlan1-30 (kitchens), 201-230 (living rooms),
  301-330 (bedrooms), 401-430 (bathrooms)
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

### Simulation platforms

- MolmoSpaces: https://github.com/allenai/molmospaces / arXiv:2602.11337
- Isaac Lab: https://github.com/isaac-sim/IsaacLab / arXiv:2511.04831
- AGILE (G1 locomotion): https://github.com/nvidia-isaac/WBC-AGILE
- COMPASS (cross-embodiment nav): https://github.com/NVlabs/COMPASS
- GR00T N1.6: https://github.com/NVIDIA/Isaac-GR00T
- ManiSkill3: https://github.com/haosulab/ManiSkill
- Habitat 3.0/PARTNR: https://github.com/facebookresearch/partnr-planner

### VLM navigation

- ImagineNav (ICLR 2025): VLM view-selection navigation
- SayNav: LLM + 3D scene graph / arXiv:2309.04077
- NaVILA: VLM + RL two-level nav / arXiv:2412.04453
- SPF (See-Point-Fly): VLM pixel-coordinate nav, 100% success (Gemini 2.5 Pro)

### Multi-agent cooperation

- RoCo: Multi-robot LLM dialogue / arXiv:2307.04738
- CoELA (ICLR 2024): Cognitive modular LLM agents
- FurnMove (ECCV 2020): AI2-THOR two-agent furniture moving
- LLaMAR (NeurIPS 2024): LLM long-horizon multi-agent planning
- Neural MMO: Competition-driven territorial exploration
- Voyager: LLM open-ended lifelong learning agent
- Concordia: Game Master/Player separation architecture
