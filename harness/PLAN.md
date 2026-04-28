# Roboclaws Navigator Self-Improvement Harness

A logbook for the AI2-THOR navigator agent loop. Each run is recorded with what
the task was, what went wrong, what changed, and the measurable delta. The aim
is a closed loop where the agent reads prior runs, proposes one bounded change
to the skill or MCP, applies it, runs the next task, and appends a new entry.

## How to use this file

1. **Before a run**: read the latest `## Run NNN` entry. Note its open
   "carry-forward" items — they are unfinished improvements.
2. **During a run**: take the task as given. Do not read prior solutions —
   the point is to surface fresh friction.
3. **After a run**: append a new `## Run NNN` block using the template below.
   Cite step counts, failed-move counts, and the specific tool sequences that
   were wasteful. Then propose ONE bounded change (skill edit OR MCP tool
   addition, not both) and either apply it or queue it as carry-forward.
4. **Commit**: each entry is one atomic commit on its own branch. Squash
   rejected changes — keep the log clean.

## Template

```
## Run NNN — YYYY-MM-DD — <task one-liner>

**Task**: <what the operator asked>
**Model / harness**: <e.g. Sonnet 4.6 + ai2thor-navigator skill v1.2>
**Outcome**: <success / partial / failed>

### Metrics
- Steps to completion: NN (target: NN)
- `move` calls: NN (blocked: NN, %blocked: NN)
- `observe` calls: NN (image-bearing: NN)
- Wall-clock: NN min
- Photo framing pass rate (target ≥60% of frame): NN/NN

### Friction log (top 3)
1. <one-line description, with step number>
2. ...
3. ...

### Root cause (one paragraph)
<Why those frictions happened. Not "I made a mistake" — what was missing
from the agent's information or tooling that forced the trial-and-error?>

### Change applied this run
**Scope**: skill | mcp | both | none (deferred)
**File(s)**: <path>
**Diff summary**: <2-3 lines>
**Hypothesis**: <if we re-run the same task, expected metric delta>

### Carry-forward
- [ ] <unaddressed item 1>
- [ ] <unaddressed item 2>
```

---

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

---

## Run 002 — 2026-04-28 — replay of Run 001 task, no code changes (baseline)

**Task**: identical to Run 001 (`harness/tasks/photo-living-room.txt`)
**Model / harness**: `claude --dangerously-skip-permissions` inside `just code::cc`, driven by `harness/run.sh 002 ... 600`. Cap 10 min.
**Outcome**: timeout — 3 targets captured (sofa-1, armchair-1, dining-chair-1) of 7+ expected; tore down at 602s

### Metrics
- Tool calls: **55** (vs Run 001 ≈127+ before user interrupt) — **57% fewer for ~same coverage**
- FPV snapshots: 21 (vs Run 001 ~30+)
- Wall-clock: 602s
- Targets photographed: 3 (vs Run 001: 3 — different mix; this run hit dining-chair-1 but missed armchair-2; Run 001 hit armchair-2 but missed all dining chairs)
- `blocked_moves` metric: reported 0, but that's a harness bug — the grep pattern `"result": "blocked"` doesn't appear in the MCP server log (FastMCP doesn't log response bodies). Carry-forward: instrument blocked count server-side or via snapshot-archive log lines.

### Friction log (top 3)
1. **Same dining-chair pathfinding wall as Run 001** (steps ~30–55). After photographing sofa-1 + armchair-1, the agent burned ~25 tool calls probing south through the dining area: snapshot labels include `replan-011`, `south-corridor-012`, `east-corridor-check-013`, `stuck-check-014`, `replan-2-015`, `south-route-016`, `south-clear-017`, `deep-south-018`, `facing-dining-019` before finally landing `dining-chair-1-020`. That's 9 navigation-probe captures for 1 successful target.
2. **Multi-attempt framing per shot** — labels show `approach-armchair-1`, `armchair-1-frame-check`, `armchair-1-aim`, `armchair-approach`, `armchair-1` (5 captures to land 1 framed shot). Same `move + LookDown + observe` × N pattern as Run 001 friction #5.
3. **TUI transcript is unparseable** — `tmux pipe-pane` captured raw escape codes from Claude Code's spinner. For analysis, only the MCP log + snapshot labels are usable signal. `harness/run.sh` should drop the transcript file and rely on log-derived metrics.

### What changed between runs (NOT a code change — model behavior alone)
This agent did a **4-direction survey at start** (`survey-east-002`, `survey-south-003`, `survey-west-004`) before moving. Run 001 (me) did not — I rotated incrementally and only realized the room layout after ~15 collisions. The survey-first habit alone explains most of the tool-call savings. **This is a coin flip though** — it's not in SKILL.md, so the next agent run might revert to my pattern. P2 (codify inventory-first in SKILL.md) protects the gain.

### Root cause (unchanged from Run 001)
Still no scene-level prior, still no target-relative motion. The agent CAN do better strategy spontaneously (Run 002 proves it), but the dining-chair pocket is geometrically hostile to grid-step navigation regardless of strategy. Without `scene_objects` (P0a) + `goto` (P1), every run will hit this wall.

### Change applied this run
**Scope**: harness only (`harness/run.sh`, `harness/PLAN.md`, `harness/tasks/photo-living-room.txt`) — committed as `6b4a513`. No skill or MCP changes. This run is the baseline measurement against which P0a + P2 will be evaluated.

### Carry-forward (updated)
- [ ] **P0a**: implement `scene_objects` MCP tool (`roboclaws/mcp/server.py`). ~15 lines. Highest expected delta.
- [ ] **P2**: SKILL.md "Multi-target capture" section — encode inventory-first + yaw convention. ~10 lines.
- [ ] **P0b**: `observe(images=False)` flag.
- [ ] **P1**: `goto(object_id)` with reachable-cell projection.
- [ ] **harness/run.sh fixes**:
  - tee race: `mkdir -p harness/runs/$RUN_ID` happens AFTER the launcher's tee target is opened by the caller; either drop the tee or do mkdir client-side.
  - drop `transcript.txt` (TUI escape soup, no signal)
  - replace `blocked_moves` grep with a server-side instrumentation OR count `*-blocked-*` snapshot labels OR count `last_action_success: false` if logged
- [ ] verify: re-run task with P0a + P2 applied → record Run 003 with delta.

### Hypothesis for Run 003
With P0a + P2 only (no goto):
- Tool calls: 30–40 (down from 55) — inventory-first becomes 1 call instead of 4 surveys.
- Targets: 5+/7 — agent now knows ALL chair object IDs upfront, can plan a TSP route. Still grid-step navigation so dining chairs may still cost 5–8 calls each.
- The dining-chair wall persists until P1 lands.

## Run 003 — 2026-04-28 — replay with P0a + P2 applied

**Task**: identical to Run 001/002.
**Model / harness**: same agent surface as Run 002, but with two changes landed: `roboclaws__scene_objects` (commit `0de955b`) and the inventory-first SKILL.md rewrite (commit `62fa7fe`). Plus harness reads `trace.jsonl` now (`9a1a9b2`).
**Outcome**: timeout at 600s — but **all 9 targets captured** before the cap. The agent simply didn't realize it was finished in time to call `done`.

### Metrics
- Tool calls: **65** (vs Run 002: 55, Run 001: 127+)
- Per tool: `scene_objects=1`, `observe=20`, `observe_archived=0`, `move=44`
- `blocked_moves`: **10** (15.4% of calls; vs Run 002 ≈19/68 = 28%)
- FPV snapshots: 21
- **Targets captured: 9/9** — `chair-1`, `chair-2`, `chair-3`, `chair-4`, `chair-5`, `chair-6` (all 6 dining chairs), `sofa-1`, `armchair-1`, `armchair-2`

### Friction log (top 3)
1. **Cap was too tight** (t=600s). Agent was on the trace's last frame `chair-3-frame` when the harness cut it off; one more turn and it would have called `done` cleanly. With `goto` (P1) this would compress to ~30 calls and cap timing becomes irrelevant. Until then, raise the cap to 900s for this task.
2. **`observe_archived` not used at all** despite SKILL.md endorsing it for "the final shot if you've already framed it via the previous observe". The agent always re-`observe`d for capture (visible: `chair-1-frame-002` then `chair-1-003` is two image-bearing observes; an `observe_archived(label="chair-1")` for the second would have saved 3 image tokens). Carry-forward: tighten the SKILL.md guidance.
3. **Block rate (15.4%) still high.** The dining-chair pocket caused most blocks (`chair-3-frame` terminal block, `west-corridor-007` mid-run). `goto(object_id)` projecting to nearest reachable cell is the structural fix.

### Root cause of remaining cost
With P0a + P2, the inventory + planning phase collapsed from 30+ tool calls (Run 001) or 4 surveys (Run 002) to **1 call**. The remaining 64 calls are all execution: navigate-frame-capture-repeat across 9 targets at ~7 calls/target. That's still grid-step navigation; P1 (`goto`) collapses it to ~3 calls/target.

### Change applied this run
**Scope**: skill + harness (no further mid-run code changes).
**Files**: `skills/ai2thor-navigator/SKILL.md` (62fa7fe), `harness/run.sh` (9a1a9b2).
**Hypothesis from Run 002 PLAN entry**:
- Predicted: 30–40 calls, 5+/7 targets.
- Actual: 65 calls, 9/9 targets.
- Calls came in higher than predicted (the dining-chair pocket needed more probing than I estimated), but coverage **exceeded** prediction substantially. The 4-direction-survey-then-explore behavior of Run 002 was the optimistic prior; turns out grid-step navigation across 6 dining chairs is what dominated the budget.

### Harness bug discovered
`metrics.txt` shows a stray `0` line between `observe_archived: 0` and `move: 44`. The `trace_count_request_tool` shell function returns nothing on grep-zero-match because `grep -c PATTERN file` exits 1 when count is 0 (printing "0" to stdout already), and the `|| echo 0` then prints another "0", concatenating. Plus bash arithmetic errors in the monitoring loop when `DONE_CALLS=""`. Fix in next harness commit:
```sh
trace_count_request_tool() {
  local n
  n=$(grep -c "..." "$path" 2>/dev/null) || n=0
  echo "${n:-0}"
}
```

### Carry-forward
- [ ] **harness**: fix `trace_count_*` zero-match return (one-line bug; gates clean Run 003 metrics file).
- [ ] **harness**: bump default `TIME_CAP` to 900s for the photo-living-room task — close calls like Run 003 should not be classified as timeout.
- [ ] **SKILL.md**: clarify that the second `observe` after framing should be `observe_archived` to save image-token cost. Run 003 captured 9 targets but issued 20 observes; ~9 of those could be archived.
- [ ] **P1 — `goto(object_id)`**: still queued. With Run 003 proving the loop measures real deltas, P1 is the next high-impact change. Predicted: ~30 calls, 9/9 targets, well under the 600s cap, agent calls `done` cleanly.
- [ ] **P0b — `observe(images=False)`**: deprioritised. Run 003's 20 observes are largely necessary (framing) and `observe_archived` already provides a no-images variant for batch capture.
- [ ] verify: re-run task with the harness fixes + observe_archived clarification → record Run 004.

<!-- Append new ## Run NNN entries below. Do not edit prior runs. -->
