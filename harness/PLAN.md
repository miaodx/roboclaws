# Roboclaws Navigator Self-Improvement Harness

A logbook for the AI2-THOR navigator agent loop. Each run is recorded as its
own file under `runs-log/` with metrics, root cause, change applied, and
carry-forward. This file is the **stable shell**: a how-to header, a template,
the active carry-forward queue, and an index of every run.

## How to use this file

1. **Before a run**: read the latest entry in `runs-log/` (the highest-
   numbered file). Read the **Active carry-forward** section below — those are
   the unfinished items the next run is responsible for. Read the prior run's
   **Hypothesis for next run** so you know what's being graded.
2. **During a run**: take the task as given. Don't read prior solutions —
   the point is to surface fresh friction.
3. **After a run**: create `runs-log/<NNN>-<task-slug>.md` using the template
   below. Cite step counts, blocked-move counts, and the specific tool
   sequences that were wasteful. Propose ONE bounded change (skill edit OR
   MCP tool addition, not both) and either apply it or queue it as
   carry-forward.
4. **Update this file**: append a row to the **Run index** below in the
   *hypothesis-and-result* format. Then update **Active carry-forward** —
   tick boxes for items the run resolved, add new items the run uncovered.
5. **Commit**: each run is one atomic commit. New `runs-log/<NNN>-...md` +
   PLAN.md index update + (optionally) the change you applied. Keep them
   separable so a botched analysis can be reverted with one `git revert`.

## Run entry template

Copy this into `runs-log/<NNN>-<task-slug>.md`. Hypothesis goes IN
the file (not just the index) because it's where future readers go to
understand what was being graded.

```markdown
## Run NNN — YYYY-MM-DD — <task one-liner>

**Task**: <what the operator asked>
**Model / harness**: <e.g. Sonnet 4.6 + ai2thor-navigator skill v1.2 + harness/run.sh>
**Hypothesis going in**: <H: predicted metrics, e.g. "30 calls / 9-of-9 / done in <5 min">
**Outcome**: <success / partial / failed / aborted>

### Metrics
- Tool calls: NN  (per-tool: scene_objects=N, observe=N, observe_archived=N, move=N, goto=N, done=N)
- Blocked moves: NN
- Targets: NN/NN
- Wall-clock: NN min

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

### Hypothesis for next run
<Concrete predicted metrics for the NEXT iteration. Stating it here
prevents post-hoc rationalization in the next entry.>

### Carry-forward
- [ ] <unaddressed item 1>
- [ ] <unaddressed item 2>
```

## Active carry-forward

(What the next run owns. Drained from the most recent run's Carry-forward
section, edited as items land or get re-prioritised.)

- [ ] **`goto` runtime-collision fallback**: Run 004 surfaced cells that AI2-THOR
  reported as reachable but rejected at Teleport time on FloorPlan201. `goto`
  could retry at distance+0.25m on the first such error before returning. Not
  hit in Run 005 but plausible on other floor plans.
- [ ] **observability — `harness/scripts/summarize.py`**: aggregate `trace.jsonl`
  across runs into a metrics CSV. Closes the "cross-run comparison is
  bash-glue" gap that `harness::history` papers over today.
- [ ] **observability — token / cost telemetry**: each `claude
  --dangerously-skip-permissions` iteration costs real $$; harness has no
  budget tracking. Wrap the invocation to log token counts.
- [ ] **observability — agent reasoning capture**: drop `claude` interactive-TUI
  for `claude -p ... --output-format=stream-json` so we can correlate the
  agent's chain-of-thought with the trace.jsonl tool calls. Bigger swing;
  defer until a class of bug demands it.
- [ ] **Pick the next task class**. The photo task is solved (Run 005 = 9/9 in
  37 calls, clean done). Plausible next: room-by-room object inventory, or
  grasp+place manipulation. New task = new friction = new P-changes.

## Run index

`H: hypothesis | A: actual` — see Format 3 in commit `0b845e2`'s PR
discussion. Hypothesis is what the *previous* run's "Hypothesis for next
run" predicted; actual is what this run measured.

| Run | Date | Task | H: predicted | A: actual | Headline |
|---|---|---|---|---|---|
| [001](runs-log/001-photo-living-room.md) | 2026-04-28 | photo-living-room | (baseline, no prior run) | 127+ calls / 3-of-9 / user-interrupt | manual baseline; geometry rediscovered by collision |
| [002](runs-log/002-photo-living-room.md) | 2026-04-28 | photo-living-room | same as 001 (no code changes) | 55 calls / 3-of-9 / done | autonomous baseline; spontaneous 4-direction survey |
| [003](runs-log/003-photo-living-room.md) | 2026-04-28 | photo-living-room | 30–40 calls / 5+/7 / done | 65 calls / 9-of-9 / timeout @ 600s | scene_objects + skill rewrite; coverage exceeded prediction |
| [004](runs-log/004-photo-living-room.md) | 2026-04-28 | photo-living-room | ~30 calls / 9-of-9 / done | aborted at t=272s — 10/10 gotos errored | goto y-coordinate bug, FakeEngine couldn't catch it |
| [005](runs-log/005-photo-living-room.md) | 2026-04-28 | photo-living-room | ~30 calls / 9-of-9 / done | **37 calls / 9-of-9 / done in 3.8 min** | corrected goto; clean closure of the photo task |
