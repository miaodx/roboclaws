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
