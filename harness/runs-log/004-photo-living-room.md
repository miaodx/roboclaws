## Run 004 — 2026-04-28 — P1 (`goto`) landed, ABORTED on physics bug

**Task**: same.
**Model / harness**: `goto` shipped (commit `75ce415`). Cap raised to 900s and grep zero-match fixed (`e85b8e5`).
**Outcome**: aborted by harness operator at t≈272s after the trace.jsonl revealed all 10 `goto` calls were failing with AI2-THOR's `InvalidOperationException: Collided with: Floor` / `Patio`.

### Metrics (partial)
- `goto: 10`, all returning `result=error`
- After every failed goto, the agent fell back to `move`: `move: 9` mid-run, accumulating
- Targets captured: 4 (chair-1, sofa-1, sofa-1b, chairs-row) — all via grid-step nav, not goto
- Run aborted before metrics.txt was written

### Friction log (top 1)
1. **`goto` teleported the agent INTO the floor.** I was passing `y = target.bbox.center.y` (~0.5m for a chair seat) to AI2-THOR's `Teleport`. The agent's standing collision capsule clipped through the floor and Unity rejected every call. Fixed in commit `d9f1d4d` by reading `y` from `get_agent_state()` instead.

### Why FakeEngine didn't catch this
`tests/test_mcp_server.py::FakeEngine.step("Teleport", ...)` snaps `_position` to whatever was passed without running any physics. The 5 `goto` tests passed because they only assert on the **arguments** the server sent to Teleport, not on whether Teleport would have succeeded against a real Unity scene. Lesson: **for any tool that crosses the AI2-THOR boundary, the FakeEngine fake is necessary but not sufficient — a single live-probe run is mandatory** before declaring done.

The harness loop caught this in <5 min of agent runtime. No code review would have.

### Carry-forward (closed in Run 005)
- [x] fix goto y-coordinate bug (`d9f1d4d`)
- [x] re-run task to validate fix → Run 005 below
