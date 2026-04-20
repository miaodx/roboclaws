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

_No active TODOs. Next work should come from a new plan or issue._
