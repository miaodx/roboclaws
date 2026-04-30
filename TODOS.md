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

## How to pick work

Default queue:

1. `Now`: bounded, high-leverage work that can close without a new research phase.
2. `Strategic next`: work that decides the next technical direction.
3. `May checkpoint`: research bookkeeping for the next monthly checkpoint.
4. `Later`: useful but dependent on more data or a prior spike.
5. `Parked`: do not open unless the trigger condition happens.

---

## Now: quick closure / bounded credibility

- **P0 quick win — mode safety envelope documentation** (from
  `docs/research-checkpoints/2026-04.md` §6.3 item 10). Document each
  operating mode's safety boundary before broader production-style deployment.
  Acceptance criteria: cover Mode 1 local VLM calls, Mode 2 OpenClaw
  loopback/token/skill-source review, Mode 3 direct MCP exposure, and Mode 4
  Railway appliance auth/reset surface; link the result from `ARCHITECTURE.md`
  or the relevant runbook.

- **P1 bounded measurement — MCP latency budget** (from checkpoint §7 Q6).
  Quantify whether MCP round-trip overhead is material relative to a simulated
  30 Hz step budget. Acceptance criteria: instrument `observe`, `move`, and
  `done` timings around `roboclaws/openclaw/mcp_server.py`, separate simulator
  time from RPC/server overhead, and document the maximum practical control
  frequency for Mode 3.

- **P1 mechanical cleanup — Phase 2.6 deferred-items sweep** (from plan
  02.6-05; see
  `.planning/phases/02.6-openclaw-mcp-tools-integration/deferred-items.md`).
  5 ruff check errors + 6 format diffs in unrelated Phase 2.2 / Kimi-era files
  surfaced during the phase-wide gate. Resolve as a standalone
  `chore: ruff cleanup` PR.

---

## Strategic next: direction-setting spikes

- **P0 strategic — MolmoSpaces migration spike** (from checkpoint §6.3 item 6
  and §7 Q14). Answer whether MolmoSpaces can host the next roboclaws substrate
  before picking a VLA. Acceptance criteria: reproduce one minimal navigation
  task, document whether multi-agent support is mature enough for territory /
  coverage games, estimate the porting work for current `MultiAgentEngine`
  assumptions, and record blocker classes in the checkpoint or a new phase
  plan. Start point: read the MolmoSpaces links in checkpoint appendix A.9,
  then compare its scene/task API against `roboclaws/core/engine.py`.

- **P1 strategic — Smolagents CodeAgent benchmark vs Mode 3** (from checkpoint
  §6.3 item 7 and §7 Q1/Q16). Determine whether code-as-action reduces LLM
  steps on AI2-THOR navigation, not just on coding benchmarks. Acceptance
  criteria: run the same small task through current Mode 3 MCP and a
  Smolagents CodeAgent prototype, compare step count, success, tool errors,
  elapsed time, and prompt/token cost, then decide whether the experiment
  should precede or follow the MolmoSpaces spike.

---

## May checkpoint: source quality and roadmap review

- **P2 checkpoint hygiene — first-party ecosystem refresh** (from checkpoint
  §7 Q13). Replace weak C/D-source claims such as star counts and "X% of Y has
  Z" with first-party data where possible. Acceptance criteria: use GitHub API
  or first-party release pages for stars, dates, licenses, and activity status,
  mark any remaining third-party claims explicitly, and update the May 2026
  checkpoint source-quality notes.

- **P2 roadmap review — mode productivity and Phase-2 readiness** (from
  checkpoint §7 Q11/Q12). Decide which of the four roboclaws modes is producing
  the most useful artifacts and whether Phase 2 is complete enough to shift
  toward manipulation tasks. Acceptance criteria: compare recent outputs across
  Mode 1/2/3/4, define the N=4 territory-control success-rate threshold, and
  recommend whether to continue Phase 2 hardening or start the operation-task
  transition.

---

## Later: useful after the next substrate / Mode 3 decisions

- **P2 optional interface — LeRobotDataset rollout export** (from checkpoint
  §6.3 item 8). Decide whether replay data should optionally export in
  LeRobotDataset format for future GR00T / openpi / VLA work. Acceptance
  criteria: map current replay fields to LeRobotDataset v3.0 concepts,
  identify missing action/state/camera metadata, and either add a narrow
  exporter or document why this should wait until after the substrate spike.

- **P2/P3 research spike — multi-agent harness expansion** (from checkpoint
  §6.3 item 9 and §7 Q2/Q15). Explore what breaks when `harness/` moves from
  one coding agent driving one robot to multiple coding agents driving multiple
  robots in the same sim. Acceptance criteria: identify the minimum
  lock/context/state isolation model, test whether generated skills transfer
  across agents or overfit to one SOUL, and produce a concrete design note
  before implementation.

- **P3 experiment — memory-depth ablation for territory control** (from
  checkpoint §7 Q3). Measure whether the full SOUL → MEMORY → FTS → vector
  memory stack helps short-horizon high-frequency territory tasks. Acceptance
  criteria: define at least three memory configurations, run the same scenario
  under each, compare success / coverage / stuck recovery / cost, and decide
  whether roboclaws needs all four layers or only SOUL + MEMORY for now.

- **P3 UX polish — autonomous-nav `report.html` parity with VLM report**
  (flagged 2026-04-21 while reviewing Phase 2.6 Probe 4 artifact). The VLM
  report has per-step reasoning and frame back/forward controls. The OpenClaw
  autonomous-nav report lacks both because Gateway reasoning is opaque and the
  current layout is a single scroll. Start point: diff
  `scripts/render_autonomous_replay.py` against `roboclaws/core/visualizer.py`,
  then pick a contract that works despite Gateway opacity.

- **P3 OpenClaw simplification — benchmark `minimal+alsoAllow:[bundle-mcp]`
  vs `coding` tool profile** (flagged 2026-04-27 while fixing the OpenClaw
  2026.4.25-beta.11 MCP regression). Current choice keeps `minimal` and splices
  `bundle-mcp` through `alsoAllow`; `coding` might simplify bootstrap but
  broadens the tool surface. Acceptance criteria: compare photo and territory
  probes under both profiles, measure success rate/action diversity/tool-misuse
  errors, then update `docs/openclw/openclaw-tool-profiles.md` with the verdict.

---

## Parked: conditional only

- **OpenClaw cold-start: close the remaining ~89s gap** (flagged 2026-04-28
  after shipping commit `bd5037b`, which cut 348s → 136s). Per-phase trace in
  `docs/retrospectives/openclaw-cold-start-2026-04-28.md` shows the remaining
  cost is `sidecars.session-locks` (65s) + `sidecars.channels` (39.5s). Open
  this only if a future image bump regresses cold-start past 136s; otherwise
  leave parked.

_If this list empties, next work should come from a new plan or issue._
