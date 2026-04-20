# Phase 2.3 — Pin OpenClaw Gateway image by digest (declined 2026-04-20)

**Decision:** keep `:2026.4.14` instead of pinning by digest.

**Rationale:** the date-shaped tag reads as its release date at a glance
(2026-04-14). That's more useful when skimming CI logs, PRs, or
`docker pull` output than an opaque `sha256:7ea0...`. Digest pinning's
immutability gain is real but modest — upstream re-tagging is a
theoretical risk we haven't hit, and the `OPENCLAW_IMAGE` repo-variable
override already provides the escape hatch if we ever need to pin to a
specific digest without a code change.

**For the record** — the 2026-04-14 digest resolved via the GHCR
manifest API on 2026-04-20 was
`sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`
(multi-arch manifest list). Future-us can drop that into the
`OPENCLAW_IMAGE` repo variable as a one-click rollback if upstream ever
re-tags.

**Revisit trigger:** upstream actually re-tags `:2026.4.14`, or we move
to an appliance mode where bit-exact reproducibility matters more than
log readability.
