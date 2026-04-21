# TODOs

Deferred work that a future maintainer (or future-you, or a different AI agent on
a clean checkout) can pick up without rereading the whole history.

One entry = one self-contained item. If you start it, check it out first:
`git log --grep=<item-keyword>` usually surfaces whether someone already
kicked it off. Start points are written so that a fresh session — no prior
context, no hidden notes — can resume directly.

---

## Shipped

- **Phase 2.2** (2026-04-16) — Per-agent SOUL preset distribution + two
  long-running Gateway game demos (territory + coverage). Shipped as a
  single run; see `PLAN.md § Phase 2.2 retrospective`. Original items 1
  + 2.

## Declined

- **Phase 2.3 — Pin OpenClaw Gateway image by digest** (decided
  2026-04-20). Evaluated and rejected in favour of the existing
  `:2026.4.14` tag. Rationale: the date-shaped tag reads as its release
  date at a glance, which is more useful for humans skimming CI logs /
  PRs / `docker pull` output than an opaque `sha256:7ea0...`. The
  immutability gain from digest pinning is real but modest — upstream
  re-tagging is a theoretical risk we haven't hit, and the `OPENCLAW_IMAGE`
  repo-variable override already covers the escape hatch if we ever need
  to pin to a specific digest. Revisit only if upstream actually re-tags.

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

_If this list empties, next work should come from a new plan or issue._
