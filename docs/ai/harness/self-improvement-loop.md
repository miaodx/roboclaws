# Navigator Harness — Self-Improvement Loop

Date: 2026-04-28

A scripted loop that exercises the AI2-THOR navigator skill end-to-end on
a curated task, captures structured metrics, and feeds the result back
into a curated logbook so the **next** iteration starts with concrete
ground to stand on. Operational quick-start lives in
[`harness/README.md`](../../../harness/README.md); this document is the design
rationale.

## What problem this solves

Before the harness, "is the navigator skill working well?" was answered by
running it interactively, watching tool calls scroll by, and forming an
impression. Two of those impressions in this repo's history (Run 001 — manual,
127+ tool calls, partial coverage; observed by the human) directly motivated
the harness. Impressionistic evaluation has three failure modes the loop
fixes:

1. **No baseline.** Without metrics, "this run felt slow" is unfalsifiable.
   The loop captures tool-call counts, blocked-move counts, target coverage,
   and wall-clock for every iteration — every change is graded against the
   last numbers.
2. **No bug-class isolation.** Run 004 caught a teleport-into-floor bug that
   the test suite's `FakeEngine` cannot catch by construction (the fake
   snaps state without physics). Live single-iteration runs are the only way
   to surface that class. The loop makes one mandatory before declaring
   any sim-crossing tool done.
3. **No memory across sessions.** PLAN.md is append-only, gitignore-immune,
   and the next operator reads it before the next run. Lessons that would
   have been forgotten ("yaw=0 → +Z, do not re-derive") become permanent.

## Architecture

```
operator
   │
   │   just harness::run photo-living-room
   ▼
harness/run-next.sh ──── auto-numbers next run_id ───┐
                                                     ▼
                                          harness/run.sh <id> <task> [cap]
                                                     │
                              ┌──────────────────────┼─────────────────────┐
                              ▼                      ▼                     ▼
                     tmux: just code::cc      .tmp/roboclaws-mcp/     output/runs/<ts>/
                       │                      server.log              trace.jsonl
                       │                                              snapshots/agent-0/
                       ▼
                Docker-backed Claude Code with bypass permissions
                       │ (sends tool calls via MCP)
                       ▼
                roboclaws MCP server
                       │
                       ▼
                  AI2-THOR engine
```

Each component owns one job:

- **`run-next.sh`** picks the next run_id by `max(harness/runs/*, '## Run NNN'
  headers in PLAN.md) + 1`. Errors out if no task is named — see [Design
  decisions](#design-decisions) below.
- **`run.sh`** spawns the tmux session, waits for the MCP to publish
  `Application startup complete`, sends the kickoff message via
  `tmux send-keys`, polls `output/runs/<ts>/trace.jsonl` for tool counts and
  the `done` request, and tears down at completion or cap.
- **`PLAN.md`** is the stable shell — how-to, template, active
  carry-forward queue, and a run-index table. It stops growing because
  the per-run details live in their own files under `runs-log/`.
- **`runs-log/<NNN>-<task-slug>.md`** is the curated per-run record:
  metrics, friction log, root cause, change applied, hypothesis for next
  run, carry-forward. One iteration = one file = one PR-able unit.
- **`runs/<NNN>/`** is raw artifacts — trace.jsonl, server.log, metrics.txt.
  Gitignored. Useful for the run that produced them and one follow-up
  debug session; safe to delete any time.

## Signal sources

The harness reads three places. Knowing which is authoritative for which
question matters when something goes wrong.

| Question | Source | Why |
|----------|--------|-----|
| Has MCP started? | `.tmp/roboclaws-mcp/server.log` | uvicorn startup banner |
| How many tool calls? | `trace.jsonl` `"event": "request"` lines | one record per tool, server-written, structured |
| How many blocked moves? | `trace.jsonl` `"result": "blocked"` | response bodies live here, not in server.log |
| Did the agent call done? | `trace.jsonl` `"tool": "done", "event": "request"` | the only definitive signal |
| What did the agent see? | `output/runs/<ts>/snapshots/agent-0/*.fpv.png` | labeled snapshots survive tmux teardown |

The harness used to scrape the Claude Code TUI via `tmux pipe-pane`. That
captured raw escape codes and was unparseable. Run 002 surfaced this; the
harness now ignores the TUI entirely.

## Design decisions

### Why `task` is required (no default)

The harness exists to surface *change*, not to be convenient. Re-running
yesterday's task by accident hides regressions. A required positional arg
forces the operator to think about what they're testing each time. `just`
enforces the requirement before our wrapper runs, so the error is clean.

If you genuinely want regression mode ("did anything break since yesterday on
the canonical task?"), name it explicitly: `just harness::run photo-living-room`.

### Why one change per run

Each `## Run NNN` block in PLAN.md attributes a metric delta to **one**
intentional change (skill edit, MCP tool addition, or task scope shift).
Bundling two changes makes deltas un-attributable. Run 003 (skill change
only) and Run 005 (skill change + new MCP tool) are deliberately separate;
attributing the 3.4× tool-call reduction across them required keeping the
variable separate.

### Why an append-only logbook

Editing prior run files breaks the chain of reasoning that justified
subsequent changes. If something in Run 003 turns out to have been wrong,
the right move is a new Run 010 that says "Run 003's hypothesis was wrong,
here's the corrected analysis", not a silent edit. Git history is the
secondary defense; the convention is the primary one.

The Layout-A split (one file per run under `runs-log/`) makes this
mechanical: each run is its own commit, atomic to revert. PLAN.md itself
is mutable — its **Active carry-forward** queue and **Run index** are
expected to evolve — but the per-run files are write-once.

### Why aborts are first-class

Run 004 was killed at t=272s the moment trace.jsonl revealed all 10 `goto`
calls were erroring with `Collided with: Floor`. Letting it run to the cap
would have generated 0 additional signal. The harness explicitly supports
abort-on-clear-infra-failure as a valid outcome — the next PLAN.md entry
records *why* the run was aborted, which is just as useful as a clean run.

## Worked example: 5 iterations on the photo task

Run 001–005 collectively reduced the same task from 127+ tool calls (manual,
3/9 targets) to 37 tool calls (autonomous, 9/9 targets, agent self-terminates).
Each iteration moved one variable:

| Run | Variable changed | Tool calls | Targets | Outcome |
|---|---|---:|---:|---|
| 001 | (manual baseline) | 127+ | 3/9 | user interrupt |
| 002 | none — pure measurement | 55 | 3/9 | done |
| 003 | + `scene_objects` MCP tool, + skill rewrite | 65 | 9/9 | timeout |
| 004 | + `goto` MCP tool (with bug) | aborted | — | aborted |
| 005 | goto y-coordinate fix | **37** | **9/9** | **done** |

The two big learnings:

- **Skill changes alone (002 → 003) tripled target coverage.** Code changes
  only help when the agent has the right plan to execute; the skill teaches
  the plan. This was the single highest-ROI change.
- **The `FakeEngine` test suite cannot replace a live probe.** The Run 004
  goto bug shipped with 5 passing tests because the fake snaps state without
  physics. For any tool that crosses the AI2-THOR boundary, the harness loop
  is the only test that catches y-coordinate-class bugs.

## When NOT to use the harness

- **Code review for style/typing/refactor.** Use ruff + pyright + tests.
- **Verifying a single tool's contract.** Use `pytest tests/contract/mcp/test_mcp_server.py`.
- **Quick interactive exploration.** Use `just code::cc` directly.
- **Anything that doesn't have a reasonable "is it better?" metric.** The
  harness is a measurement instrument; without a metric, it's just an
  expensive way to run an agent.

The harness pays off when there's a curated task with a known failure mode,
a hypothesis for what would help, and willingness to log the result before
chasing the next idea.

## See also

- [`harness/README.md`](../../../harness/README.md) — operational quick-start.
- [`harness/PLAN.md`](../../../harness/PLAN.md) — the actual run logbook.
- [`docs/human/coding-agent-nav-server.md`](../../human/coding-agent-nav-server.md) — the
  underlying MCP path the harness drives.
- [`skills/ai2thor-navigator/SKILL.md`](../../../skills/ai2thor-navigator/SKILL.md)
  — the skill being measured.
