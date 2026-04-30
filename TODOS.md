# TODOs

Deferred work that a future maintainer (or future-you, or a different AI agent on
a clean checkout) can pick up without rereading the whole history.

One entry = one self-contained item. If you start it, check it out first:
`git log --grep=<item-keyword>` usually surfaces whether someone already
kicked it off. Start points are written so that a fresh session — no prior
context, no hidden notes — can resume directly.

Shipped phases are tracked under `docs/retrospectives/` (see `CLAUDE.md`),
not here.

---

## Queue policy

`TODOS.md` is the active roadmap. Work it from top to bottom unless a user,
phase plan, or production incident changes priority.

Append speculative ideas, future experiments, and parked items to
[`THOUGHTS.md`](THOUGHTS.md) instead. Promote an item back here only after
reviewing it and deciding it should affect the current dev roadmap.

---

## Active queue

### 1. Mode safety envelope documentation

Source: `docs/research-checkpoints/2026-04.md` §6.3 item 10.

Document each operating mode's safety boundary before broader production-style
deployment. Cover Mode 1 local VLM calls, Mode 2 OpenClaw
loopback/token/skill-source review, Mode 3 direct MCP exposure, and Mode 4
Railway appliance auth/reset surface. Link the result from `ARCHITECTURE.md`
or the relevant runbook.

Why first: docs-only, high leverage, and it makes future OpenClaw / appliance
work safer to evaluate.

### 2. MCP latency budget measurement

Source: checkpoint §7 Q6.

Quantify whether MCP round-trip overhead is material relative to a simulated
30 Hz step budget. Instrument `observe`, `move`, and `done` timings around
`roboclaws/openclaw/mcp_server.py`, separate simulator time from RPC/server
overhead, and document the maximum practical control frequency for Mode 3.

Why second: bounded technical credibility work for the coding-agent MCP path.

### 3. Phase 2.6 deferred-items sweep

Source: plan 02.6-05,
`.planning/phases/02.6-openclaw-mcp-tools-integration/deferred-items.md`.

5 ruff check errors + 6 format diffs in unrelated Phase 2.2 / Kimi-era files
surfaced during the phase-wide gate. Resolve as a standalone
`chore: ruff cleanup` PR.

Why third: mechanical cleanup that removes known repo friction.

### 4. MolmoSpaces migration spike

Source: checkpoint §6.3 item 6 and §7 Q14.

Answer whether MolmoSpaces can host the next roboclaws substrate before picking
a VLA. Reproduce one minimal navigation task, document whether multi-agent
support is mature enough for territory / coverage games, estimate the porting
work for current `MultiAgentEngine` assumptions, and record blocker classes in
the checkpoint or a new phase plan.

Start point: read the MolmoSpaces links in checkpoint appendix A.9, then
compare its scene/task API against `roboclaws/core/engine.py`.

Why fourth: this is the main strategic next step after the quick credibility
work is cleared.

### 5. Smolagents CodeAgent benchmark vs Mode 3

Source: checkpoint §6.3 item 7 and §7 Q1/Q16.

Determine whether code-as-action reduces LLM steps on AI2-THOR navigation, not
just on coding benchmarks. Run the same small task through current Mode 3 MCP
and a Smolagents CodeAgent prototype, compare step count, success, tool errors,
elapsed time, and prompt/token cost, then decide whether this path should
become part of the main harness story.

Why fifth: useful comparison, but it should not distract from the substrate
decision.

### 6. First-party ecosystem refresh for the May checkpoint

Source: checkpoint §7 Q13.

Replace weak C/D-source claims such as star counts and "X% of Y has Z" with
first-party data where possible. Use GitHub API or first-party release pages
for stars, dates, licenses, and activity status, mark any remaining third-party
claims explicitly, and update the May 2026 checkpoint source-quality notes.

Why sixth: improves research quality, but it is bookkeeping unless the May
checkpoint is the active task.

### 7. Mode productivity and Phase-2 readiness review

Source: checkpoint §7 Q11/Q12.

Decide which of the four roboclaws modes is producing the most useful artifacts
and whether Phase 2 is complete enough to shift toward manipulation tasks.
Compare recent outputs across Mode 1/2/3/4, define the N=4 territory-control
success-rate threshold, and recommend whether to continue Phase 2 hardening or
start the operation-task transition.

Why seventh: best answered after a few more concrete artifacts exist.

---

_If this list empties, review [`THOUGHTS.md`](THOUGHTS.md), promote the next
actionable item, or start a new plan._
