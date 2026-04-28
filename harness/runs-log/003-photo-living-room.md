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
