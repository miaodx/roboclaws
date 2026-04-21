---
name: ai2thor-navigator
description: Navigate a simulated robot one step at a time in an AI2-THOR indoor scene. Given a first-person camera frame, an overhead map, and structured game state, return a single navigation action as JSON.
metadata:
  openclaw:
    emoji: 🤖
---

# AI2-THOR Navigator Skill

An OpenClaw skill that drives a single simulation agent through an AI2-THOR indoor
scene.  In Phase 2 each simulation agent runs as a separate OpenClaw instance, each
with its own SOUL preset and independent memory.

## What this skill does

Receives per-step observations from the AI2-THOR simulation engine:

1. **First-person camera frame** — the agent's eye view (base64 JPEG)
2. **Overhead map** — top-down grid annotated with agent positions and game state
3. **Structured game state** — position, score, remaining steps, teammate info

Returns a single navigation action:

| Action | Effect |
|--------|--------|
| `MoveAhead` | Move forward one grid cell |
| `MoveBack` | Move backward one grid cell |
| `MoveLeft` | Strafe left one grid cell |
| `MoveRight` | Strafe right one grid cell |
| `RotateLeft` | Rotate 90° counter-clockwise |
| `RotateRight` | Rotate 90° clockwise |
| `LookUp` | Tilt camera up |
| `LookDown` | Tilt camera down |
| `Teleport` | Teleport to a target position (requires extra args) |
| `Done` | Signal that this agent has finished |

## Python usage

```python
from roboclaws.core.vlm import create_provider
from roboclaws.openclaw.skill import AI2THORNavigatorSkill, SkillInput

# Choose VLM backend: "mock" (CI-safe), "anthropic", "kimi", "gpt-4o", "gpt-4o-mini"
provider = create_provider("anthropic")

# Choose play style: "aggressive", "defensive", or "cooperative"
skill = AI2THORNavigatorSkill(provider, soul="aggressive")

output = skill.run(SkillInput(
    agent_id=0,
    camera_frame=agent_state.frame,        # (H, W, 3) uint8 numpy array
    overhead_frame=engine.get_overhead_frame(),
    game_state=game.get_state(),
))

print(output.action)    # e.g. "MoveAhead"
print(output.reasoning) # VLM chain-of-thought
```

## Play styles (SOUL presets)

Three built-in SOUL presets are provided in `souls/`:

| Soul | File | Strategy |
|------|------|----------|
| `aggressive` | `souls/aggressive.md` | Rush unclaimed areas; cut off opponents |
| `defensive` | `souls/defensive.md` | Build a solid contiguous region; avoid contests |
| `cooperative` | `souls/cooperative.md` | Spread to uncovered areas; coordinate with teammates |

Custom SOUL text may be passed directly as a string:

```python
skill = AI2THORNavigatorSkill(provider, soul="You are a random walker. Move randomly.")
```

## Input schema

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | `int` | Zero-based agent index |
| `camera_frame` | `np.ndarray (H×W×3 uint8)` | Agent's first-person camera feed |
| `overhead_frame` | `np.ndarray (H×W×3 uint8)` | Overhead grid map with annotations |
| `game_state` | `dict` | Structured state from the game engine |

## Output schema

| Field | Type | Description |
|-------|------|-------------|
| `reasoning` | `str` | VLM chain-of-thought justification |
| `action` | `str` | Navigation action to execute (always one of `NAVIGATION_ACTIONS`) |

## Multi-agent setup (Phase 2 Gateway bridge)

For multi-agent OpenClaw integration (issue #13), each simulation agent maps to a
separate skill instance.  The Gateway bridge (`roboclaws/openclaw/bridge.py`) routes
per-agent observations to the correct skill instance and forwards action decisions
back to the AI2-THOR engine.

```
┌─────────────────────────────────────────────┐
│              AI2-THOR Engine                │
│  agent-0 frame ──► Skill (soul=aggressive)  │
│  agent-1 frame ──► Skill (soul=defensive)   │
│  agent-2 frame ──► Skill (soul=cooperative) │
└─────────────────────────────────────────────┘
```

## VLM cost estimates (per-step)

| Model | Cost/step | 3 agents × 200 steps |
|-------|-----------|----------------------|
| GPT-4o-mini | ~$0.00003 | ~$0.018 |
| GPT-4o | ~$0.0004 | ~$0.24 |
| Claude Sonnet | ~$0.0006 | ~$0.36 |
| Mock (CI) | $0.00 | $0.00 |

## Tools

For the Phase 2.5 autonomous loop, the agent can call three HTTP tools served by the
local simulation bridge at `http://host.docker.internal:18788`.

In the current OpenClaw Gateway image, these are not exposed as native structured tool
slots. Read this skill file first, then use the generic `exec` tool with `curl` to call
the endpoints below and parse their JSON responses.

If you choose to use OpenClaw's built-in `image` tool anyway, prefer passing
base64 `data:image/...` payloads directly or files written under the current
workspace/media roots. Avoid `/tmp/...` paths inside the Gateway container — the
local-media policy rejects paths outside the allowed workspace/media/temp roots.

### `observe`

- HTTP: `GET http://host.docker.internal:18788/observe`
- Request body: none
- Response body:

```json
{
  "fpv": "<base64 JPEG 320x240>",
  "overhead": "<base64 JPEG 320x240>",
  "state": {
    "agent_id": 0,
    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
    "camera_horizon": 0.0,
    "last_action_success": true
  },
  "human_message": null
}
```

- Usage: Call `observe` when you need to see the world. It returns the current
  first-person view, an overhead map, and the latest physical state. Start every run
  with one `observe`.

### `move`

- HTTP: `POST http://host.docker.internal:18788/move`
- Request body:

```json
{
  "direction": "MoveAhead | MoveBack | MoveLeft | MoveRight | RotateLeft | RotateRight | LookUp | LookDown",
  "reason": "<optional brief natural-language rationale>"
}
```

- Response body:

```json
{
  "state": {
    "agent_id": 0,
    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
    "camera_horizon": 0.0,
    "last_action_success": true
  },
  "human_message": null,
  "server_warning": "move before first observe"
}
```

- Usage: Call `move` to take one physical step in the world. The response gives you
  updated state but does not include new images, so call `observe` again when you need
  to re-look. Default behavior is `observe -> think -> move`. You may take a short
  burst of repeated `move` calls when you have a concrete local reason such as a clear
  hallway, a safe backtrack, or following a human-directed maneuver. When you do, send
  a short `reason` string so the replay can explain why you continued without a fresh
  observation. The `server_warning` field is optional and appears when the server needs
  to flag a non-fatal issue such as moving before the first observation.

### `done`

- HTTP: `POST http://host.docker.internal:18788/done`
- Request body:

```json
{
  "reason": "<short natural-language reason>"
}
```

- Response body:

```json
{
  "status": "ok",
  "reason": "<same reason>"
}
```

- Usage: Call `done` when the navigation goal is achieved or you are stuck and further
  moves will not help. This ends the run cleanly.

Call `observe` when you need to see the world. Prefer `observe -> think -> move`, but
stay agentic: if the scene clearly supports a short continuation, you may keep moving
and justify it with `move.reason`. Call `done` when the navigation goal is achieved or
you're stuck.

## Human messages

Tool responses from `observe` and `move` may include a `human_message` field. When
present, it is a directive from a human observer watching the run. Treat it as a
high-priority hint: follow it when compatible with your current goal, and acknowledge
it explicitly in your reasoning either way. If you cannot follow it, say why. If you
choose to follow it, say so. If you later call `done`, mention the human message and
what you did about it in the `done.reason`. The human is steering you, not
interrupting you.

Example tool response:

```json
{
  "state": {
    "agent_id": 0
  },
  "human_message": "try rotating left to see the window"
}
```

Your next reasoning step should reference the message before calling the next tool, for
example: "human observer suggests rotating left; compatible with exploring the east
wall, rotating now."
