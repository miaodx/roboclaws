## Run 006 — 2026-04-30 — Codex comparison on solved photo task

**Task**: same `photo-living-room` task; photograph every sofa/chair/armchair in FloorPlan201.
**Model / harness**: Codex `gpt-5.5` with `medium` reasoning, launched through `just code::codex` by the agent-aware harness.
**Hypothesis going in**: Codex should follow the existing photo protocol without skill changes: `scene_objects` first, `goto` per target, 9/9 target photos, `done` in roughly 40-45 tool calls.
**Outcome**: **done** at t=247s. **9/9 targets** captured. **0 blocked moves**.

This is a Codex comparison run, not a replacement for the Claude history in Runs 001-005.

### Metrics

- Tool calls: **42** (per-tool: `scene_objects=1`, `observe=17`, `observe_archived=0`, `move=11`, `goto=12`, `done=1`)
- Blocked moves: **0**
- Targets: **9/9**
- FPV snapshots: **18**
- Wall-clock: **247s** (4.1 min)
- Trace: `harness/runs/006/trace.jsonl`
- Snapshot dir: `output/runs/202604301518/snapshots/agent-0`
- Final recommended target labels: `sofa-1-close`, `chair-1-detail`, `chair-2-detail`, `chair-3-detail`, `chair-4-detail`, `chair-5-detail`, `chair-6-detail`, `armchair-1-detail`, `armchair-2-detail`

### Friction log (top 3)

1. **Harness wiring smoke before the measured run**: Codex launched and the prompt appeared in the TUI, but the harness's `Enter` submit path left it parked in the input buffer. The trace stayed at `0` tool calls through t=90s. This was fixed before rerunning Run 006 by passing the kickoff as Codex's initial prompt file.
2. **All captures used image-bearing `observe`**: Codex produced `observe=17` and `observe_archived=0`. It still completed in 42 calls, but used more image context than the Claude Run 005 pattern (`observe=5`, `observe_archived=7`).
3. **Framing refinement on the first chair was tool-heavy**: the trace shows three `goto` calls to `Chair|-03.12|+00.02|+01.41` at distances `0.7`, `0.45`, and `0.2`, plus two `LookDown` moves before `chair-1-detail`. No collisions occurred; this was visual framing work, not navigation failure.

### Root cause

The only clear infrastructure root cause was that the harness assumed Claude and Codex accepted pasted multiline prompts the same way. Claude submits with the final `Enter`; Codex's TUI did not, so the prompt was visible but no model turn started. The measured Codex trace after the fix shows the navigator skill itself is self-contained for Codex: it called `observe(label="preflight")`, inventoried `Sofa,Chair,ArmChair`, used `goto` for target-relative motion, produced labeled snapshots, and called `done`.

### Change applied this run

**Scope**: harness only
**File(s)**: `harness/run.sh`, `just/code.just`, `just/harness.just`, `harness/README.md`, `tests/test_harness_runner.py`
**Diff summary**:

- Added `agent={claude,codex}` to `just harness::run`, keeping `claude` as the default.
- Added Codex model/reasoning plumbing (`gpt-5.5` / `medium` for this run), agent-specific tmux session names, and full per-tool metrics including `goto` and `done`.
- Passed Codex kickoff prompts through `CODEX_INITIAL_PROMPT_FILE` so the run starts without TUI keybinding ambiguity.

### Hypothesis for next run

The photo task is now solved by both Claude and Codex. If it is rerun only as a regression check, expect first tool call within 60s, 40-45 total tool calls, 9/9 target photos, 0 blocked moves, and `done` under 5 minutes. The next improvement loop should use a new task class rather than tuning the solved photo task further.

### Carry-forward

- [ ] Pick the next task class. Photo capture is solved under both Claude and Codex; plausible next tasks remain room-by-room object inventory or a first manipulation-oriented grasp/place task.
- [ ] Consider a future skill nudge only if image-token cost becomes a bottleneck: Codex ignored `observe_archived`, but the task still completed cleanly, so no skill edit is justified from this run alone.
