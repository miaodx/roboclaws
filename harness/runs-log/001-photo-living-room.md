## Run 001 — 2026-04-28 — photograph every sofa & chair in living room

**Task**: "麻烦给这个屋子里面的每个沙发和椅子拍个照片，确保视野中大部分都是对应的沙发或者椅子，所有都拍完后，统一发给我。注意下 grid map，最好远离障碍物，防止你自己被卡住"
**Model / harness**: Sonnet 4.6 (low) + ai2thor-navigator skill (current main) + direct coding-agent mode
**Outcome**: partial — only sofa-1, armchair-1, armchair-2 captured; dining chairs (×4) NOT photographed; user interrupted before completion

### Metrics
- Steps to interrupt: ~127 (target for this task: ~30)
- `move` calls with `result: "blocked"`: 9 / collisions_total at end: 9
- `observe` calls: ~22 (every one image-bearing — no state-only mode exists)
- Wall-clock: too long; user explicitly flagged "this whole running is not that good"
- Photo framing pass rate: 3/3 captured were acceptable, but 7 targets total → 3/7 task coverage

### Friction log (top 5)
1. **Yaw convention rediscovered from scratch** (steps 1-30). Spent ~30 steps deducing that yaw=0 → +Z direction by watching position deltas after `MoveAhead`. Skill never states the convention.
2. **Object discovery is reactive** (step 103, found ArmChair_db15b007). Operator asked for "every chair", but the only way to enumerate them was to walk until each one entered the visible-objects cone. Lost ~40 steps wandering the east half of the room looking for chairs I didn't know existed.
3. **L-shaped sofa fooled spatial model** (steps 6-39). Agent stuck in concave pocket of the corner sofa, repeatedly blocked by the same Sofa_8c0941af on three sides. No way to query the sofa's bounding box to plan a route around.
4. **Map image is opaque** (entire run). map_v2 PNG shows obstacles as dark cells but the agent has no programmatic way to read it — has to OCR pixels by eye and guess scale. Effectively decorative, not actionable.
5. **Each photo = 4 tool calls** (every capture). `MoveAhead → LookDown ×2 → observe` was the minimum to frame a shot. ×7 targets = 28 calls of pure framing overhead, not counting navigation.

### Root cause

The agent has no **scene-level prior** and no **target-relative motion primitives**. AI2-THOR exposes the full object list and a `Teleport` action server-side (engine.py already proxies them — see survey notes), but the MCP only surfaces `visible_objects` (a filtered subset of what's in front of the camera right now) and grid-step `MoveAhead`/`RotateLeft` etc. The agent therefore has to reconstruct global state by walking, and reconstruct local geometry by colliding. The skill compounds this by treating navigation as the primary mental model — it tells the agent to "observe → think → move" but doesn't tell it to inventory first.

### Change applied this run
**Scope**: none (deferred — recorded as plan, not yet applied)
**Hypothesis**: see "Proposed changes" below; carrying as Run 002 prerequisites.

### Proposed changes (queued for Run 002)

Ranked by expected step-count reduction. Targeting same task replay.

**P0 — `roboclaws__scene_objects(filter_type=None)`** (~15 lines in `roboclaws/mcp/server.py`)
- Wraps `engine._last_event.events[agent_id].metadata["objects"]` (already streamed by AI2-THOR every step).
- Returns `[{objectId, objectType, name, position{x,y,z}, axisAlignedBoundingBox.center, axisAlignedBoundingBox.size}, ...]`.
- Optional comma-separated `filter_type` for fast culling.
- **Expected delta**: cuts Run 001 friction #2 (40 wasted steps) and friction #3 (the L-sofa stuck loop) entirely. One call replaces the entire object-discovery phase.

**P0 — `roboclaws__observe(images=False)`** (~5 lines)
- Add `images: bool = True` arg. When False, return only `state` block (no FPV/map/chase). Default True (back-compat).
- **Expected delta**: ~12 of Run 001's 22 observes were "did the move land?" checks where images weren't needed. Saves 36 image tokens of context.

**P1 — `roboclaws__goto(object_id, distance=1.0, face=True)`**
- Resolves object via `scene_objects`, picks nearest reachable cell from `GetReachablePositions` (already cached), and calls AI2-THOR `Teleport` (already wired in `engine.py` `NAVIGATION_ACTIONS`, currently exposed via raw `move("Teleport", ...)` but undocumented).
- **Expected delta**: replaces ~70% of Run 001's `MoveAhead`/`RotateLeft` chains. Each photo target collapses from ~8 navigation steps to 1 `goto` call.

**P2 — SKILL.md "Inventory-first protocol"** (one new section)
- Add 6-line "Multi-target capture" section: "Step 1, before any move, call `scene_objects(filter_type=...)`. Step 2, sort targets by reachable-cell distance. Step 3, for each target: `goto → observe(label=...) → next`." Explicitly state **yaw=0 → +Z direction** so it's not rediscovered.
- **Expected delta**: makes the agent USE the new tools instead of falling back to grid-stepping habit.

**P3 (deferred) — programmatic map**
- Eventually expose `reachable_cells` as a list rather than only as a rendered PNG. The PNG is fine for human eyes but useless to the agent's reasoning.

### Carry-forward
- [ ] P0a: implement `scene_objects` MCP tool
- [ ] P0b: add `images=False` flag to `observe`
- [ ] P1: implement `goto(object_id)` MCP tool with reachable-cell projection
- [ ] P2: rewrite SKILL.md photo protocol around inventory-first
- [ ] P3: surface programmatic reachable_cells (defer until P0–P2 measured)
- [ ] verify: re-run Run 001 task verbatim after P0+P2; record Run 002 with delta
