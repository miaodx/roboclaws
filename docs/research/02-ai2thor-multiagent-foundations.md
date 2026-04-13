# AI2-THOR Multi-Agent API & OpenClaw Integration Technical Details

> Research date: 2026-04-13
> Status: Complete. Key specs incorporated into technical design.

## AI2-THOR Multi-Agent API

### Initialization & Control

`agentCount` parameter at init, `agentId` per step. Each `controller.step()` moves one agent only (synchronous turn-based). Returns multi-agent event with independent Event objects per agent.

### Per-Agent Independent Data

- `event.events[i].frame`: Independent first-person RGB numpy array
- `event.events[i].depth_frame`: Depth map (float32, meters)
- `event.events[i].metadata['agent']`: Position, rotation, cameraHorizon
- `event.events[i].metadata['objects']`: Object list with per-agent `visible` flags
- `event.events[i].metadata['lastActionSuccess']`: Action result

### Collision & Visibility

Agents are Unity physics entities — **cannot pass through each other**. Collisions cause action failure (`lastActionSuccess=False`). Agents **are visible in each other's camera views** as capsule/character models.

### Movement Modes

- **Grid-based** (default, `snapToGrid=True`): Discrete `gridSize` steps, `rotateStepDegrees` rotation
- **Continuous** (`snapToGrid=False`): Arbitrary distance/angle, noise simulation supported

### Overhead View

`GetMapViewCameraProperties` + `AddThirdPartyCamera` for orthographic top-down. Supports semantic segmentation overlay. Third-party cameras dynamically updatable.

### ProcTHOR Multi-Agent Bug

GitHub Issues #1169 and #1265: ProcTHOR `agentCount=2` returns only one event; controlling `agentId=1` throws TimeoutError. Both unresolved. **Must use iTHOR scenes.**

### Known Limitations

- No native simultaneous actions (turn-based only)
- No built-in inter-agent communication
- No documented agentCount upper limit; rendering overhead scales linearly
- Sparse multi-agent documentation
- No deformable objects

## OpenClaw Architecture

### SKILL.md Format

YAML frontmatter (name, description, version, requirements) + Markdown body (When to Use, How to Use, Rules, Examples). Located at `~/.openclaw/workspace/skills/<skill-name>/`. Auto-reloaded on changes. Published to ClawHub (5,400+ community skills).

### Gateway API

WebSocket server (default `ws://127.0.0.1:18789`), JSON-RPC 2.0 style. Two roles: operator (control plane) and node (capability host). Supports Tailscale/SSH/VPN remote access.

### Multi-Agent Routing

Multiple fully isolated agents within one Gateway process. Deterministic routing via bindings matching channel, accountId, peer, guild/team ID. Most-specific binding wins. Each agent has independent workspace, SOUL.md, MEMORY.md, skills.

### SOUL.md and MEMORY.md

- **SOUL.md**: Agent personality ("character sheet"), injected at session context start
- **MEMORY.md**: Agent-written long-term memory. Three tiers: Tier 1 (always loaded, ~100 lines) → Tier 2 (date-based, auto-load today+yesterday) → Tier 3 (deep knowledge, semantic search retrieval)
- Per-file truncation: 20,000 chars; aggregate cap: 150,000 chars

### Image Processing

Separate `imageModel` config. Native multimodal models (Claude Sonnet, GPT-4o) receive original images directly. Auto-resize to JPEG 2048px max.

## VLM Navigation Prompt Strategies

### Five Validated Approaches (by effectiveness)

1. **Spatial grounding (SPF/See-Point-Fly)**: VLM outputs pixel coordinates on image. 100% success (Gemini 2.5 Pro, GPT-4.1).
2. **View selection (ImagineNav, ICLR 2025)**: VLM selects best direction from candidates. GPT-4o-mini, 62% on HM3D.
3. **Programmatic state (ProgPrompt)**: Environment as Python code.
4. **3D scene graph (SayNav)**: Subgraph to text prompt.
5. **Topological map (Guide-LLM)**: Text nodes for locations.

### Token Costs (320×240 images)

| Model | Tokens/image | Cost per 100 steps |
|-------|-------------|-------------------|
| GPT-4o-mini (low detail) | 85 | $0.002 |
| GPT-4o (low detail) | 85 | $0.03 |
| Claude Haiku 4.5 | ~102 | $0.012 |
| Claude Sonnet 4.6 | ~102 | $0.037 |

3 agents × 1000 steps total cost: $0.04 (GPT-4o-mini) to $0.74 (Claude Sonnet).

## MAP-THOR & Multi-Agent AI2-THOR Ecosystem

- **MAP-THOR** (NeurIPS 2024): 45 tasks × 5 floor plans, 1-5 agents. LLaMAR cognitive architecture (Plan-Act-Correct-Verify), 30% higher success than prior methods.
- **FurnMove** (ECCV 2020): 2 agents moving furniture. SYNC-policies + CORDIAL, 58% completion.
- **CoELA** (ICLR 2024): 5-module cognitive architecture, GPT-4 agents 40%+ efficiency improvement.
- **PARTNR** (ICLR 2025, Habitat 3.0): 100K human-robot tasks. LLMs achieve only 30% vs humans 93%.

## Inspiration Projects

- **Neural MMO**: 128+ agents; competition naturally drives territorial niche differentiation
- **OpenAI Hide-and-Seek**: Simple competitive rewards produce 6-phase emergent strategies
- **Voyager**: LLM lifelong learning with automatic curriculum + skill library + self-verification
- **Concordia**: Game Master / Player separation architecture
- **Stanford Generative Agents**: Observation → reflection → planning memory architecture

## References

- AI2-THOR: https://ai2thor.allenai.org/ / https://github.com/allenai/ai2thor
- MAP-THOR: https://openreview.net/pdf?id=ZygZN5egzy
- LLaMAR: https://github.com/nsidn98/LLaMAR
- ImagineNav: arXiv:2410.09874
- SayNav: arXiv:2309.04077
- SPF: https://spf-web.pages.dev/
- Voyager: https://voyager.minedojo.org/
- OpenClaw multi-agent routing: https://docs.openclaw.ai/concepts/multi-agent
