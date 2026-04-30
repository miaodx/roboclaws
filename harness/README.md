# Roboclaws Navigator Self-Improvement Harness

A scripted loop that runs the AI2-THOR navigator skill end-to-end on a named
task, captures structured metrics, and writes them to an append-only logbook
(`PLAN.md`). Each iteration spawns a fresh Claude Code agent in tmux by
default, drives it through the MCP, monitors the trace, and tears down — no
human in the inner loop. Codex is available as an opt-in comparison agent.

This README is the operational quick-start. For why the harness exists and
how it's been used to tune skill + MCP design, read
[`docs/harness-self-improvement-loop.md`](../docs/harness-self-improvement-loop.md).

## Quick start

```bash
just harness::list-tasks            # what's available
just harness::run <task_name>       # run one iteration (auto-numbered)
just harness::run <task_name> 900 codex
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
├── PLAN.md            ← STABLE shell: how-to + template + active carry-forward
│                        + run-index table. Stays ~200 lines forever.
├── README.md          ← this file
├── run.sh             ← one iteration end-to-end (explicit run_id form)
├── run-next.sh        ← thin wrapper that auto-numbers the next run
├── tasks/             ← task prompts; one .txt file per task
│   └── photo-living-room.txt
├── runs-log/          ← curated per-run analysis, ONE file per iteration
│   ├── 0001-photo-living-room.md
│   ├── 0002-photo-living-room.md
│   └── ...
└── runs/              ← per-run RAW artifacts (gitignored)
    └── <NNN>/
        ├── metrics.txt
        ├── trace.jsonl
        └── server.log
```

The split: `runs-log/` is the curated record (committed); `runs/` is raw
artifacts (gitignored, can be deleted any time). PLAN.md is the stable
shell — it stops growing because per-run details live in their own files.

## Adding a new task

1. Drop a single-paragraph prompt at `harness/tasks/<name>.txt`. Plain text;
   any language; what you'd type as the operator's message.
2. `just harness::run <name>`.
3. After the run, create `harness/runs-log/<NNN>-<task-slug>.md` using the
   template in PLAN.md. Cite tool counts, friction points, root cause, and
   one bounded change.
4. Append a row to PLAN.md's **Run index** table in `H: predicted | A:
   actual` format. Update **Active carry-forward** — tick boxes for items
   the run resolved, add new items it uncovered.
5. Make exactly one atomic git commit for the completed loop: run log +
   PLAN.md update + the one bounded change applied, if any. Raw
   `harness/runs/<NNN>/` artifacts stay gitignored.

That's the loop. Don't run the same task twice without changing one
intentional variable in between (skill, MCP code, or task scope) — re-running
identical setups only measures model variance, not progress.

## Reading the logbook

PLAN.md is the entry point: read **Active carry-forward** for what the next
run owns, then the **Run index** for the trajectory at a glance. Click into
`runs-log/<NNN>-...md` for full analysis on a specific run.

Each per-run file has the same shape:

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

Runs 001–005 are worth reading in order as a worked example of what a
useful entry looks like.

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
tmux kill-session -t roboclaws-harness-<NNN>-<agent>
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
