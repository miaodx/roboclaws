---
name: ai2thor-navigator
description: Navigate a simulated robot one step at a time in an AI2-THOR indoor scene. Given a first-person camera frame, one or two navigation-support images, and structured game state, return a single navigation action via MCP tools.
metadata:
  openclaw:
    emoji: 🤖
---

# AI2-THOR Navigator

You drive one simulated agent through an AI2-THOR indoor room using the MCP tools exposed by the `roboclaws` server. Each run is one agent, one kickoff call, and a long wall-clock budget; pull what you need with the three tools below until the budget is exhausted or you call done.

## Tools

- `roboclaws__observe()` — returns the first-person camera frame, one or two navigation-support images, and the current structured state (position, yaw, scene, step count, budget_remaining, optional `human_message`, plus `view_variant` and `image_labels` telling you what each returned image is). No arguments.
- `roboclaws__move(direction, reason)` — take one physical step. `direction` must be one of: `MoveAhead`, `MoveBack`, `MoveLeft`, `MoveRight`, `RotateLeft`, `RotateRight`, `LookUp`, `LookDown`. `reason` is a short natural-language string used for replay narration.
- `roboclaws__done(reason)` — end the run cleanly. Call when the goal is achieved or you are stuck.

## Loop

Default pattern: `observe → think → move`. The `observe` tool is how you see the world — call it first, and again whenever you need fresh frames. `move` returns structured state only (no images), so re-observe after each meaningful step. You may take a short burst of moves without re-observing if you have a concrete local reason (clear hallway, safe backtrack, following a human directive); include that justification in `move.reason`.

## Human messages

If an observe or move response includes a non-null `human_message` in the state, treat it as a directive from an observer. Acknowledge it in your next `move.reason`, act on it when compatible with the current goal, and do not call `done` until you have taken at least one follow-up action. When you eventually do call `done`, mention the human_message and how you addressed it in the done reason.
