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

## Active

- **Autonomous-nav `report.html` parity with VLM report** (flagged 2026-04-21
  while reviewing Phase 2.6 Probe 4 artifact). The VLM implementation's
  `report.html` has per-step reasoning (from the assistant's JSON
  `reasoning` field) and the frame viewer has back/forward arrows to step
  through scenes. The OpenClaw autonomous-nav report (plan 02.6-04 →
  `scripts/render_autonomous_replay.py`) lacks both:
    - No reasoning surface — OpenClaw's Gateway hides the model's
      per-turn thinking inside the session; the bridge only sees
      tool-call JSON and the final assistant text. A future report
      could surface an explicit "reasoning trace" by either (a)
      instructing the agent in its kickoff prompt to emit a short
      `<reason>...</reason>` tag before each tool call and extracting
      those for display, or (b) querying Gateway logs post-hoc for the
      per-turn `assistant_reasoning` internal field if the Gateway
      exposes one.
    - No frame-by-frame navigation — current layout is a single scroll
      with all frames inline. A "◀ Prev | N/M | Next ▶" control on a
      single active frame would match the VLM report's UX.
  Start point: diff `scripts/render_autonomous_replay.py` (OpenClaw) vs.
  `roboclaws/core/visualizer.py` report generation (VLM) to see how the
  VLM side surfaces reasoning; pick the contract that works for OpenClaw
  given the Gateway's opacity.

- **Phase 2.6 deferred-items sweep** (from plan 02.6-05 — see
  `.planning/phases/02.6-openclaw-mcp-tools-integration/deferred-items.md`).
  5 ruff check errors + 6 format diffs in unrelated Phase 2.2 / Kimi-era
  files surfaced during the phase-wide gate. Scoped out of 2.6 to keep
  the sim_server deletion commit focused. Resolve as a standalone
  `chore: ruff cleanup` PR.

- **Benchmark `minimal+alsoAllow:[bundle-mcp]` vs `coding` tool profile**
  (flagged 2026-04-27 while fixing the OpenClaw 2026.4.25-beta.11 MCP
  regression — see `docs/openclw/openclaw-tool-profiles.md` for the full diff and
  why we picked the splice over the profile switch). The new image gave
  us a fork in the road: keep `minimal` and splice in `bundle-mcp` via
  `alsoAllow` (current choice — preserves the locked-down core surface),
  or switch the default to `coding` (gets MCP for free but broadens the
  core tool surface to include bash, file I/O, etc.). We picked the
  conservative path without comparing them head-to-head. If `coding`
  doesn't actually hurt agent behavior on our scenarios, we can simplify
  the bootstrap by dropping the `alsoAllow` workaround and the
  `if tool_profile == "minimal": ... memoryFlush.enabled=False` branch
  in `scripts/openclaw-bootstrap.sh`.
  Start point:
    1. Enumerate what `coding` actually grants us beyond `minimal`:
       `docker exec openclaw-gateway sh -lc 'grep -A50 "CORE_TOOL_DEFINITIONS" /app/dist/tool-policy-*.js | grep -B1 -A4 "profiles:"'`
       — note which tools have `coding` but not `minimal` in their
       `profiles` array.
    2. Pick probes with the most behavioral signal:
       `just openclaw::probe game=photo` and `just openclaw::probe game=territory`.
    3. Run each twice (3+ trials each for variance):
       once with current bootstrap (`minimal` + `alsoAllow`),
       once with `ROBOCLAWS_TOOL_PROFILE=coding just openclaw::probe ...`
       (and temporarily drop the `alsoAllow` splice for the `coding` run
       so we're testing the profile alone, not profile + splice).
    4. Compare: success rate, action diversity, any tool-misuse errors
       (model trying to call a `coding`-only tool inappropriately).
    5. Decide whether to flip the default at
       `scripts/openclaw-bootstrap.sh:153`. Update
       `docs/openclw/openclaw-tool-profiles.md` with the verdict either way.

- **OpenClaw cold-start: close the remaining ~89s gap** (flagged 2026-04-28
  after shipping commit `bd5037b` which cut 348s→136s). Per-phase trace in
  `docs/retrospectives/openclaw-cold-start-2026-04-28.md` shows the
  remaining cost is `sidecars.session-locks` (65s) + `sidecars.channels`
  (39.5s). The session-locks number is anomalous — same code runs in 2.2ms
  on the standalone gateway image (also captured in that doc), so the 65s
  is event-loop starvation from concurrent appliance work, not the
  cleanup itself. Next steps and a reproduction recipe (with pinned image
  digest + repo commit) are in the doc's "What remains" section. Open this
  only if a future image bump regresses cold-start past 136s and we need
  the next lever; otherwise leave parked.

- **Research checkpoint 2026-04: MolmoSpaces migration spike** (from
  `docs/research-checkpoints/2026-04.md` §6.3 item 6 and §7 Q14).
  Answer whether MolmoSpaces can host the next roboclaws substrate before
  picking a VLA. Acceptance criteria: reproduce one minimal navigation task,
  document whether multi-agent support is mature enough for territory /
  coverage games, estimate the porting work for current `MultiAgentEngine`
  assumptions, and record blocker classes in the checkpoint or a new phase
  plan. Start point: read the MolmoSpaces links in checkpoint appendix A.9,
  then compare its scene/task API against `roboclaws/core/engine.py`.

- **Research checkpoint 2026-04: Smolagents CodeAgent benchmark vs Mode 3**
  (from §6.3 item 7 and §7 Q1/Q16). Determine whether code-as-action reduces
  LLM steps on AI2-THOR navigation, not just on coding benchmarks. Acceptance
  criteria: run the same small task through current Mode 3 MCP and a
  Smolagents CodeAgent prototype, compare step count, success, tool errors,
  elapsed time, and prompt/token cost, then decide whether the experiment
  should precede or follow the MolmoSpaces spike.

- **Research checkpoint 2026-04: multi-agent harness expansion spike** (from
  §6.3 item 9 and §7 Q2/Q15). Explore what breaks when `harness/` moves from
  one coding agent driving one robot to multiple coding agents driving
  multiple robots in the same sim. Acceptance criteria: identify the minimum
  lock/context/state isolation model, test whether generated skills transfer
  across agents or overfit to one SOUL, and produce a concrete design note
  before implementation.

- **Research checkpoint 2026-04: memory-depth ablation for territory control**
  (from §7 Q3). Measure whether the full SOUL → MEMORY → FTS → vector memory
  stack helps short-horizon high-frequency territory tasks. Acceptance
  criteria: define at least three memory configurations, run the same scenario
  under each, compare success / coverage / stuck recovery / cost, and decide
  whether roboclaws needs all four layers or only SOUL + MEMORY for now.

- **Research checkpoint 2026-04: MCP latency budget measurement** (from §7
  Q6). Quantify whether MCP round-trip overhead is material relative to a
  simulated 30 Hz step budget. Acceptance criteria: instrument `observe`,
  `move`, and `done` timings around `roboclaws/openclaw/mcp_server.py`,
  separate simulator time from RPC/server overhead, and document the maximum
  practical control frequency for Mode 3.

- **Research checkpoint 2026-04: optional LeRobotDataset rollout export**
  (from §6.3 item 8). Decide whether replay data should optionally export in
  LeRobotDataset format for future GR00T / openpi / VLA work. Acceptance
  criteria: map current replay fields to LeRobotDataset v3.0 concepts,
  identify missing action/state/camera metadata, and either add a narrow
  exporter or document why this should wait until after the substrate spike.

- **Research checkpoint 2026-04: mode productivity and Phase-2 readiness
  review** (from §7 Q11/Q12). Decide which of the four roboclaws modes is
  producing the most useful artifacts and whether Phase 2 is complete enough
  to shift toward manipulation tasks. Acceptance criteria: compare recent
  outputs across Mode 1/2/3/4, define the N=4 territory-control success-rate
  threshold, and recommend whether to continue Phase 2 hardening or start
  the operation-task transition.

- **Research checkpoint 2026-04: first-party ecosystem refresh for May
  checkpoint** (from §7 Q13). Replace weak C/D-source claims such as star
  counts and "X% of Y has Z" with first-party data where possible.
  Acceptance criteria: use GitHub API or first-party release pages for stars,
  dates, licenses, and activity status, mark any remaining third-party claims
  explicitly, and update the May 2026 checkpoint source-quality notes.

- **Research checkpoint 2026-04: mode safety envelope documentation** (from
  §6.3 item 10). Document each operating mode's safety boundary before any
  broader production-style deployment. Acceptance criteria: cover Mode 1
  local VLM calls, Mode 2 OpenClaw loopback/token/skill-source review, Mode 3
  direct MCP exposure, and Mode 4 Railway appliance auth/reset surface; link
  the result from `ARCHITECTURE.md` or the relevant runbook.

_If this list empties, next work should come from a new plan or issue._
