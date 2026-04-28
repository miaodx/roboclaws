# Roboclaws Navigator Self-Improvement Harness

A scripted loop that runs the AI2-THOR navigator skill end-to-end on a named
task, captures structured metrics, and writes them to an append-only logbook
(`PLAN.md`). Each iteration spawns a fresh Claude Code agent in tmux, drives
it through the MCP, monitors the trace, and tears down — no human in the
inner loop.

This README is the operational quick-start. For why the harness exists and
how it's been used to tune skill + MCP design, read
[`docs/harness-self-improvement-loop.md`](../docs/harness-self-improvement-loop.md).

## Quick start

```bash
just harness::list-tasks            # what's available
just harness::run <task_name>       # run one iteration (auto-numbered)
just harness::history               # recent runs + summary table
```

`task_name` is the file stem under `harness/tasks/` — e.g. `photo-living-room`
for `harness/tasks/photo-living-room.txt`. The task is **required**; running
the harness on yesterday's task by accident is exactly the regression-hiding
behavior the loop is built to surface, so there is no default.

After a run, the just recipe prints metrics inline. Detailed artifacts live
in `harness/runs/<NNN>/` (gitignored — only curated PLAN.md entries land in
git).

## File layout

```
harness/
├── PLAN.md            ← append-only logbook; each ## Run NNN block is one
│                        iteration with metrics + root cause + queued change
├── README.md          ← this file
├── run.sh             ← one iteration end-to-end (explicit run_id form)
├── run-next.sh        ← thin wrapper that auto-numbers the next run
├── tasks/             ← task prompts; one .txt file per task
│   └── photo-living-room.txt
└── runs/              ← per-run artifacts (gitignored)
    └── <NNN>/
        ├── metrics.txt
        ├── trace.jsonl
        └── server.log
```

## Adding a new task

1. Drop a single-paragraph prompt at `harness/tasks/<name>.txt`. Plain text;
   any language; what you'd type as the operator's message.
2. `just harness::run <name>`.
3. After the run, append a `## Run NNN` block to `PLAN.md` using the template
   at the top of that file. Cite tool counts, friction points, root cause,
   and one bounded change to apply before the next run.

That's the loop. Don't run the same task twice without changing one
intentional variable in between (skill, MCP code, or task scope) — re-running
identical setups only measures model variance, not progress.

## Reading PLAN.md

Each `## Run NNN` block has the same shape:

- **Metrics** — tool calls, blocked moves, snapshots, wall-clock,
  per-tool breakdown.
- **Friction log (top 3)** — concrete, step-numbered. Generic ("agent got
  confused") is not actionable; "10/10 gotos errored with `Collided with:
  Floor` because y was target.bbox.y not agent.y" is.
- **Root cause** — one paragraph. What was missing from the agent's
  information or tooling? Distinguish "model made a mistake" (uninteresting)
  from "skill/MCP couldn't have helped" (the only kind worth fixing).
- **Change applied this run** — one scoped change OR `none (deferred)`.
  Avoid bundling — the loop only attributes deltas cleanly when one variable
  moves at a time.
- **Carry-forward** — the queue for the next run. Tick boxes when items land.
- **Hypothesis for next run** — predicted metric values. Stating it before
  the next run prevents post-hoc rationalization.

The first six runs (Run 001–006 plus the closure) are worth reading as a
worked example of what a useful entry looks like.

## When to abort vs. iterate

- **Abort** when the trace.jsonl shows a clear infrastructure failure (every
  `goto` returning the same error, MCP not registered, empty visible_objects
  on every observe). Don't burn the cap watching the agent flail. Run 004 was
  killed at t=272s for exactly this reason.
- **Iterate** (let the run finish) when the agent is making slow progress
  but obviously trying. Even a timeout has signal — the trace shows where
  the budget went.

In neither case do you need to babysit. The default 900s cap is the
backstop; in practice clean runs finish in <5min.

## Artifacts and gitignore

`harness/runs/<NNN>/` is gitignored intentionally. The full server.log can
be tens of MB and the trace.jsonl carries embedded JPEG frames. PLAN.md is
the curated record; the raw artifacts are local-only and may be deleted at
any time.

## Common tasks

```bash
# Stop a stuck harness run:
tmux kill-session -t roboclaws-harness-<NNN>
just mcp::down

# List recent runs without launching anything:
just harness::history

# Inspect a specific run's trace post-hoc:
ls output/runs/   # find the most recent timestamp dir
python3 -c "import json
for L in open('output/runs/<TS>/trace.jsonl'):
    d=json.loads(L); t=d.get('tool'); e=d.get('event')
    print(t,e,d.get('request') or '')" | head -30
```
