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
  Re-check the deferred-items file before starting. The architecture cleanup on
  2026-05-07 left `ruff check .`, `ruff format --check .`, `git diff --check`,
  and `./scripts/run_pytest_standalone.sh -q` clean, so this item may now be
  partly or fully obsolete. Close it with evidence if no Kimi-era / Phase 2.2
  lint drift remains.

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

_If this list empties, next work should come from a new plan or issue._
