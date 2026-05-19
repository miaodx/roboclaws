# roboclaws

## What This Is

Multiple VLM / OpenClaw agent instances simultaneously controlling multiple
AI2-THOR simulated robots in competition (territory) and cooperation
(coverage) games. A thin, focused demo repository — not a framework — that
validates the core hypothesis: given enough context in the per-step prompt
(FPV + overhead map + structured state), a good model can navigate and make
strategic decisions end-to-end. Published as a live three-layer demo matrix
at `miaodx.github.io/roboclaws/`.

## Core Value

First public demonstration of multiple OpenClaw agent instances simultaneously
controlling multiple simulated robots in competition and cooperation, with
visible output (GIFs, report.html) for every feature.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. Source: retros phase-2, 2.1, 2.2. -->

- [x] **REQ-ai2thor-multi-agent-engine** — shipped Phase 1
- [x] **REQ-vlm-provider-pluggable** (Mock + OpenAI + Anthropic + Kimi) — shipped Phase 1
- [x] **REQ-overhead-visualizer** — shipped Phase 1
- [x] **REQ-territory-game** (image-payload contract under review, see Decisions) — shipped Phase 1
- [x] **REQ-coverage-game** (coverage semantics under review, see Decisions) — shipped Phase 1
- [x] **REQ-game-replay-recorder** — shipped Phase 1
- [x] **REQ-ci-headless-ai2thor** (Layer 1 + Layer 2 + Layer 3 jobs) — shipped Phase 1 → 2.2
- [x] **REQ-development-topology-cloud-vs-local** — shipped as contributor convention
- [x] **REQ-openclaw-gateway-bridge** (`/v1/chat/completions` + inline base64 + named-agent routing) — shipped Phase 2.1
- [x] **REQ-openclaw-per-agent-souls** (aggressive/defensive/cooperative) — shipped Phase 2.2
- [x] **REQ-soul-overlay-in-visualizer** (SOUL badges + tinted trails) — shipped Phase 2.2

### Active

<!-- Current scope. Building toward these. -->

- [x] **REQ-view-experiment-ab** — historical Phase 2.4 view experiment scope.
      The repo standardized on `map-v2+chase` on 2026-04-24 and archived the
      Phase 2.4 execution bundle under
      `.planning/milestones/v1.98-phases/02.4-view-experiment-ab/`.
- [ ] **REQ-vlm-provider-pluggable — NvidiaProvider extension** — extend the
      provider protocol with a fourth curated provider (`nvidia/nvidia/nemotron-nano-12b-v2-vl`)
      for the A/B NVIDIA confirm arm. Subsumed under REQ-vlm-provider-pluggable.
- [x] **Image-payload contract resolution (issue #52 prerequisite)** — shipped
      2026-04-15 pre-ingest (`ddfb523`); no longer blocks Phase 2.4 planning.
- [x] **Coverage semantics resolution (issue #52 prerequisite)** — shipped
      pre-ingest; field-of-view accounting is the canonical shipped behavior.

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- ProcTHOR scenes — multi-agent unresolved bugs (AI2-THOR #1169, #1265).
  iTHOR only.
- MolmoSpaces — no multi-agent support despite 230K+ scenes.
- Habitat 3.0 / PARTNR — setup complexity exceeds the thin-demo scope.
- Isaac Lab migration — deferred to Phase 3 (requires GPU + custom USD scenes
  + 1-2 week setup vs AI2-THOR's half-day).
- Cross-run MEMORY persistence — "long-running" scoped to within a single
  game run per DEC-phase-2.2-within-run-memory-scope.
- Persona Showdown cross-run framing (UC1/UC2 REJECTED at Phase 2.2 final
  gate) — Layer 3 ships as a symmetric 3-tile matrix.
- Digest pinning of the Gateway image — DECLINED 2026-04-20 (see LOCKED
  decision below); keep date-shaped tag with `OPENCLAW_IMAGE` override as
  one-click rollback.
- `:free` OpenRouter model endpoints — no tool-use support, Gateway agent
  edge returns 404.
- Aggressive-tool-calling VLMs on the webchat channel — deadlock per
  `defaultMessageChannel: "webchat"` gotcha.
- Object-interaction actions (`PickupObject`, `PutObject`, `OpenObject`,
  `CloseObject`, `ToggleObjectOn/Off`) — Phase 3 only.

## Context

- **Positioning.** Roboclaws is a thin demo, not a framework. The core
  hypothesis is "enough context in the prompt + a good model = autonomous
  navigation + strategic play." As of April 2026, no one in the OpenClaw
  community has publicly shipped multi-instance multi-robot competition +
  cooperation. Roboclaws is the first.
- **Three-layer live demo matrix** (README.md § Live Visualization):
  - Layer 1 — mock engine, every push, `miaodx.github.io/roboclaws/{territory,coverage}/`.
  - Layer 2 — Kimi + real AI2-THOR, push-to-main, `miaodx.github.io/roboclaws/smoke/{territory,coverage}/`.
  - Layer 3 — OpenClaw + Kimi with per-agent SOULs, push-to-main,
    `miaodx.github.io/roboclaws/openclaw/{demo,territory,coverage}/`.
  SOUL badges + tinted trails (red/blue/green/grey) are the only visual
  differentiator between Layer 2 and Layer 3 GIFs.
- **Dual-topology workflow.** gstack owns pre-plan deliberation (`docs/`,
  `PLAN.md`). GSD owns execution (`.planning/`). Cloud sessions
  (Claude Code web) run `lint-and-mock`-validated work only. Local
  sessions own every `local-dev` task, every real-model validation, and
  every multi-round debug loop.
- **Live-probe rule.** New external HTTP surfaces (new provider, new
  Gateway endpoint) require a real upstream probe pre-merge. Mocked tests
  alone are insufficient. This is the Phase 2.1 lesson hardened into an
  iron rule (`feedback_live_probe_gate.md`).
- **Curated provider list.** Deliberately narrow — one verified-end-to-end
  model per provider (`nvidia/...nemotron-nano-12b-v2-vl`, `kimi/k2p5`).
  Excluded models documented with rejection reasons. Re-enabling requires
  lifting curation + rerunning `tests/test_openclaw_bootstrap.py`.
- **Cost envelope.** Dev default GPT-4o-mini (~$0.018/game). CI real-model
  smoke is Kimi coding-tier (~$0.10 per 100-step 2-game run). Phase 2.4
  wallet gates: `--max-usd 15` Kimi sweep, `--max-usd 5` NVIDIA confirm,
  $20 hard cap.
- **Issue #52 prerequisites are resolved.** The original ingest warning
  around image flow-through + coverage semantics was verified stale on
  2026-04-20; the shipped code already matched the intended Phase 2.4
  contract before GSD planning.

## Constraints

- **Platform (selection)**: iTHOR scenes only (FloorPlan1-30, 201-230,
  301-330, 401-430) — ProcTHOR multi-agent is broken (AI2-THOR issues
  #1169, #1265).
- **Tech stack**: Python 3.10+, AI2-THOR controller, OpenClaw Gateway
  Docker image `ghcr.io/openclaw/openclaw:2026.4.14` (date-shaped tag,
  LOCKED — see decisions), VLM providers via OpenAI SDK (GPT-4o),
  Anthropic SDK (Claude), Anthropic SDK + custom `base_url` (Kimi Coding).
- **AI2-THOR control model**: turn-based — `controller.step(action=...,
  agentId=i)` moves one agent per call; `event.events[i]` holds per-agent
  state. No native simultaneous actions. Agents physically collide.
- **VLM I/O schema**: per-step reply must be JSON-parseable
  `{"reasoning": "...", "action": "<one of NAVIGATION_ACTIONS>"}`. Invalid
  actions coerce to `MoveAhead` with a warning. Object-interaction actions
  are Phase 3.
- **Gateway transport**: `POST /v1/chat/completions` with `model =
  "openclaw/<agentId>"` (regex `[a-z0-9][a-z0-9_-]{0,63}`). `POST
  /tools/invoke` is forbidden (plugin-only, not workspace-skill).
- **Per-agent isolation**: each Gateway agent owns its workspace under
  `/home/node/.openclaw/workspaces/<agentId>/` including its own
  `auth-profiles.json`, `SOUL.md`, `skills/`, and MEMORY in `state/`.
- **Image transport**: frames flow inline as `data:image/jpeg;base64,...`
  in the OpenAI `messages[]` payload. No bind mount; no host/container
  path identity.
- **Headless Linux**: AI2-THOR requires X server or `xvfb-run` with
  `ai2thor[headless]`. Unity binary (~1 GB) caches in `~/.ai2thor/` on
  first run.
- **Cost**: per-game envelope with 2 images/step × 3 agents × 200 steps —
  GPT-4o-mini ~$0.018, GPT-4o ~$0.24, Claude Sonnet ~$0.36, Kimi ~$0.10
  per 100-step 2-game run.
- **Live-probe gate**: any new external HTTP surface must be probed
  against the real upstream before merge.
- **Dev topology**: cloud sessions cannot run `local-dev` tagged tasks;
  real-API-key / real-Unity / real-Gateway proof starts locally, CI keeps
  it continuous.
- **Curated models**: one verified model per provider, not a catalog.

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

<decisions>

### LOCKED

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **DEC-phase-2.3-decline-digest-pin** (LOCKED, 2026-04-20). Keep the date-shaped `:2026.4.14` tag for `ghcr.io/openclaw/openclaw`; do **not** pin by `sha256:` digest. | Date-shaped tag reads as release date at a glance in CI logs / PRs / `docker pull`. Digest pinning's immutability gain is modest — upstream re-tagging is a theoretical risk we haven't hit, and the `OPENCLAW_IMAGE` repo-variable override already provides the escape hatch. Recorded rollback digest: `sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`. Revisit trigger: upstream actually re-tags `:2026.4.14`, or the project moves to an appliance mode where bit-exact reproducibility matters more than readability. | — Pending (revisit only on trigger) |

</decisions>

### Non-locked (historical, preserved for provenance)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **DEC-phase-2-gateway-pinned-image**. Pin Gateway to `ghcr.io/openclaw/openclaw:2026.4.14`; keep `OPENCLAW_IMAGE` override. | Replaced `:latest` with a known-good release. Superseded/confirmed by the LOCKED phase-2.3 ADR. | ✓ Good |
| **DEC-phase-2.1-transport-is-chat-completions**. Gateway transport is `POST /v1/chat/completions`, not `POST /tools/invoke`. | `/tools/invoke` dispatches only plugin-registered tools; chat-completions is the only path that steers a workspace skill end-to-end. | ✓ Good |
| **DEC-phase-2.1-named-agent-routing**. Each sim agent routes to its own named Gateway agent via `model="openclaw/<agentId>"`; bootstrap pre-creates N agents. | Session-key header would share SOUL / MEMORY / auth across sim agents, breaking the per-agent isolation promise. | ✓ Good |
| **DEC-phase-2-inline-image-transport**. Frames flow inline as base64 `data:` URLs in OpenAI `messages[]`; no bind mount. | Unblocks remote/Railway Gateway relay — transport no longer bind-mount-bound. | ✓ Good |
| **DEC-phase-2.2-within-run-memory-scope**. "Long-running" = within a single game run (one bootstrap → one container → 200+ turns → tear down). No cross-run MEMORY persistence. | UC2 Persona Showdown cross-run memory explicitly rejected at 2026-04-16 final gate; informational probe retained for discovery value only. | ✓ Good |
| **DEC-phase-2.2-matrix-not-showdown**. Ship 3 symmetric Layer 3 tiles (nav / territory / coverage); reject UC1 "Persona Showdown" framing. | User strategic call at 2026-04-16 final gate despite subagent CEO critique. | ✓ Good |

---
*Last updated: 2026-05-19 after v1.98 planning archive*
