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
