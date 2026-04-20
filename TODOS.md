# TODOs

Deferred work that a future maintainer (or future-you, or a different AI agent on
a clean checkout) can pick up without rereading the whole history.

One entry = one self-contained item. If you start it, check it out first:
`git log --grep=<item-keyword>` usually surfaces whether someone already
kicked it off. Start points are written so that a fresh session — no prior
context, no hidden notes — can resume directly.

---

## Phase 2.2 — shipped (2026-04-16)

The following two items (formerly items 1 + 2) shipped together as Phase 2.2
("Long-running OpenClaw games — territory + coverage") in commits
`950087a` and earlier in the same run. See `PLAN.md § Phase 2.2 retrospective`
for the detailed writeup.

- ~~**Item 1**: Phase 2.2 — Per-agent SOUL preset distribution~~
- ~~**Item 2**: Phase 2.5 — Two long-running Gateway game demos (territory + coverage)~~

---

## 1. Phase 2.3 — Pin OpenClaw Gateway image by digest, not tag

**What:** After the first green `openclaw-smoke` CI run with
`ghcr.io/openclaw/openclaw:2026.4.14`, replace the tag pin in
`.github/workflows/ci.yml` with the image digest:
`ghcr.io/openclaw/openclaw@sha256:<digest>`.

**Why:** Tags are mutable. Upstream can re-tag `2026.4.14` and silently
change behavior. Digests are immutable content references. The Phase 2.1
commit message already captures the digest for future reference, so this
is mostly about promoting that record into an active pin.

**Pros:**
- True reproducibility (immutable content reference)
- Eliminates the "image silently changed under us" failure class entirely
- CI becomes bit-exact reproducible even across registry garbage collection

**Cons:**
- If upstream GCs the digest from the registry, `docker pull` fails hard
  until we re-pin to a new digest
- Tag pin is more forgiving (keeps working as long as the tag exists)

**Context:** Phase 2 plan Task 4 pins to `ghcr.io/openclaw/openclaw:2026.4.14`
as a tag. Task 5 records the digest in the merge commit for future reference.
This TODO promotes that record into an active `.github/workflows/ci.yml` edit.

**Depends on / blocked by:** First green CI run against `:2026.4.14`
producing a stable digest.

**Start point:**
`docker inspect ghcr.io/openclaw/openclaw:2026.4.14 --format '{{index .RepoDigests 0}}'`
→ copy the output (e.g. `ghcr.io/openclaw/openclaw@sha256:abc...`) →
replace `OPENCLAW_IMAGE` default in `.github/workflows/ci.yml` → commit.
