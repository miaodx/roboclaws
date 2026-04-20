# Decisions (ADR-equivalent)

Synthesized from classified ADRs in the roboclaws ingest set (new-mode bootstrap,
MODE=new). Entries carry `locked: true|false` per the classifier output; locked
decisions cannot be auto-overridden by any other source. Non-locked decisions
documented here originated from retrospectives/SPEC/DOC content and are
preserved as reference points (not binding).

Precedence applied: ADR > SPEC > PRD > DOC.

---

## DEC-phase-2.3-decline-digest-pin

- source: docs/retrospectives/phase-2.3.md
- type: ADR
- locked: **true**
- status: Declined (decided 2026-04-20)
- scope: OpenClaw Gateway Docker image pinning strategy; CI image references;
  `OPENCLAW_IMAGE` repo-variable override
- decision: **Keep the date-shaped `:2026.4.14` tag for
  `ghcr.io/openclaw/openclaw` instead of pinning by `sha256:` digest.**
- rationale: The date-shaped tag (`2026.4.14`) reads as its release date at a
  glance in CI logs, PRs, and `docker pull` output. Digest pinning's
  immutability gain is real but modest — upstream re-tagging is a theoretical
  risk we haven't hit, and the `OPENCLAW_IMAGE` repo-variable override already
  provides the escape hatch to pin to a specific digest without a code change.
- for-the-record: The 2026-04-14 digest resolved via GHCR manifest API on
  2026-04-20 is
  `sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`
  (multi-arch manifest list). Dropping that into `OPENCLAW_IMAGE` is the
  one-click rollback if upstream ever re-tags.
- revisit-trigger: upstream actually re-tags `:2026.4.14`, OR the project moves
  to an appliance mode where bit-exact reproducibility matters more than log
  readability.

---

## Preserved-from-retrospectives (non-locked decisions)

These are design decisions captured in Phase 2 / 2.1 / 2.2 retrospectives. They
are **not** full ADRs and are included here for provenance only. They represent
"what shipped", not "what is locked".

### DEC-phase-2-gateway-pinned-image (non-locked, historical)

- source: docs/retrospectives/phase-2.md (Task 4, Task 5; review decision A3)
- scope: OpenClaw Gateway Docker image reference in CI and local docs
- decision: Pin the Gateway image to `ghcr.io/openclaw/openclaw:2026.4.14`
  (replaces the prior `:latest`); keep the `OPENCLAW_IMAGE` env override for
  forks.
- note: Superseded/confirmed by DEC-phase-2.3-decline-digest-pin — the
  date-shaped tag **stays** as the pin; no digest.

### DEC-phase-2.1-transport-is-chat-completions (non-locked, shipped)

- source: docs/retrospectives/phase-2.1.md
- scope: OpenClaw Gateway transport contract used by `roboclaws/openclaw/bridge.py`
- decision: The Gateway transport for roboclaws is
  `POST /v1/chat/completions` (OpenAI-compatible), **not** `POST /tools/invoke`.
- rationale: `/tools/invoke` in the pinned image dispatches only
  plugin-registered tools; workspace skills are prompt-injection hints consumed
  by the Gateway agent's system prompt. Chat-completions is the only path that
  actually steers a workspace skill end-to-end.
- related: DEC-phase-2.1-named-agent-routing.

### DEC-phase-2.1-named-agent-routing (non-locked, shipped)

- source: docs/retrospectives/phase-2.1.md
- scope: How multiple simulation agents are isolated inside one Gateway process
- decision: Each simulation agent routes to its own **named Gateway agent** via
  `model="openclaw/<agentId>"` (agentId regex `[a-z0-9][a-z0-9_-]{0,63}`).
  Bootstrap pre-creates N agents (env var `AGENTS`, default 2). Demos never
  call `openclaw agents add` themselves — single source of truth for agent
  config is `scripts/openclaw-bootstrap.sh`.
- alternatives-considered: `model: "openclaw" + x-openclaw-session-key` header
  (rejected — shares SOUL/MEMORY/auth across sim agents, breaking the per-agent
  isolation promise in `skills/ai2thor-navigator/SKILL.md`).

### DEC-phase-2-inline-image-transport (non-locked, shipped)

- source: docs/retrospectives/phase-2.1.md
- scope: How per-step FPV + overhead frames are delivered to the Gateway
- decision: Frames flow inline as base64 `data:image/jpeg;base64,...` URLs in
  the OpenAI `messages[]` payload. **No bind mount.** No `.openclaw-tmp`
  directory. No host/container path identity.
- consequence: Unblocks Issue 13 (remote/Railway Gateway relay) — transport no
  longer bind-mount-bound.

### DEC-phase-2.2-within-run-memory-scope (non-locked, shipped)

- source: docs/retrospectives/phase-2.2.md
- scope: "Long-running" definition for Gateway game runs
- decision: "Long-running" means **within a single game run** (one bootstrap →
  one Gateway container → 200+ turns across all agents → tear down at end). No
  cross-run MEMORY persistence; each game run starts with a fresh container.
  Within-run MEMORY.md persistence is whatever the Gateway does naturally; no
  explicit memory injection or summarization.
- user-challenge-outcome: UC2 (Persona Showdown cross-run memory) explicitly
  **REJECTED** at 2026-04-16 final gate; informational probe retained in
  validation for discovery value only.

### DEC-phase-2.2-matrix-not-showdown (non-locked, shipped)

- source: docs/retrospectives/phase-2.2.md (final gate, 2026-04-16)
- scope: Layer 3 README framing
- decision: Ship 3 Layer 3 tiles (nav/territory/coverage) symmetric with
  Layer 2; **reject** UC1 "Persona Showdown" framing.
- user-challenge-outcome: UC1 REJECTED. Subagent CEO critique documented but
  matrix preserved per user strategic call.

---

## Decisions NOT present in this ingest set

The following are architecture choices in the source docs but are **not**
formatted as ADRs and are captured under constraints.md or context.md
instead (per the doc-conflict-engine's content-type mapping):

- AI2-THOR over Isaac Lab for Phase 1-2 (technical-design.md § Technology
  Selection) — captured in constraints.md.
- iTHOR scenes vs ProcTHOR (ProcTHOR multi-agent is buggy) — captured in
  constraints.md.
- Phase-3 Isaac Lab target (two-level VLM + RL architecture) — captured in
  context.md.
