# Roadmap: roboclaws

## Overview

Roboclaws delivers the first public demonstration of multiple OpenClaw
agent instances simultaneously controlling multiple simulated robots in
competition and cooperation. The journey: first prove the VLM-drives-a-robot
core hypothesis directly against AI2-THOR (Phase 1), then layer CI +
dev-topology to keep the demo continuously alive (Phase 1.5), then route
control through an OpenClaw Gateway (Phases 2 → 2.1 → 2.2), then validate
whether better map representations help a VLM win harder games (Phase 2.4)
and, in parallel, test a different architectural bet — let the agent drive
via tool calls instead of the push model (Phase 2.5). Phase 3 (Isaac Lab)
is deferred indefinitely.

Phases 1 → 2.2 have shipped. Phase 2.3 was evaluated and declined. Phase 2.4
is drafted in `PLAN.md` and awaiting `/gsd-plan-phase 2.4`. Phase 2.5 is
drafted in `docs/plans/phase-2.5-autonomous-nav.md`, eng-reviewed, and
ready for plan ingestion. Phase 3 remains deferred indefinitely.

## Milestones

- ✅ **v1.0 Core + OpenClaw** - Phases 1, 1.5, 2, 2.1, 2.2 (shipped 2026-04-16)
- ⛔ **Phase 2.3 (Digest pin)** - DECLINED 2026-04-20 (LOCKED ADR)
- 🚧 **v1.1 Better Views** - Phase 2.4 (drafted, awaiting plan)
- 📋 **v1.2 Autonomous OpenClaw Loop** - Phase 2.5 (drafted, ready for plan)
- 📋 **v2.0 Isaac Lab** - Phase 3 (deferred indefinitely)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2, 2.3, 2.4, 2.5): Sub-phases within Milestone 2 (OpenClaw integration track)

- [x] **Phase 1: Core simulation + games** - Direct-VLM multi-agent territory + coverage on AI2-THOR (shipped)
- [x] **Phase 1.5: CI + dev topology** - Three-layer demo matrix + cloud/local workflow (shipped)
- [x] **Phase 2: OpenClaw Gateway bridge (original)** - First Gateway integration via standalone demo (shipped)
- [x] **Phase 2.1: Transport correction** - `/v1/chat/completions` + named-agent routing + inline base64 (shipped)
- [x] **Phase 2.2: Long-running OpenClaw games** - Per-agent SOULs + SOUL overlay + territory/coverage through Gateway (shipped)
- [⛔] **Phase 2.3: Gateway digest pin** - DECLINED; keep date-shaped `:2026.4.14` tag (LOCKED)
- [ ] **Phase 2.4: View-experiment A/B** - Map-v2 + chase-cam variants measured against baseline (issue #52 prereqs shipped pre-ingest 2026-04-15)
- [ ] **Phase 2.5: Autonomous OpenClaw loop (v1 single-agent nav + human steer)** - Pull-model architecture test: agent drives `observe`/`move`/`done` tools over local HTTP; stdin-based human interjection; runs parallel to Phase 2.4's push-model A/B (`docs/plans/phase-2.5-autonomous-nav.md`)
- [ ] **Phase 3: Isaac Lab migration** - Humanoid + multi-embodiment nav via VLM → RL locomotion (deferred indefinitely)

## Phase Details

<details>
<summary>✅ Phase 1: Core simulation + games — SHIPPED</summary>

### Phase 1: Core simulation + games
**Goal**: Validate the core hypothesis — a VLM with FPV + overhead + structured state can navigate and play competition/cooperation games on real AI2-THOR scenes.
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06
**Success Criteria** (what must be TRUE):
  1. A user can run `python examples/single_agent_explore.py` and see a VLM-driven agent produce a GIF of movement through `FloorPlan201`.
  2. A user can run `python examples/territory_game.py --agents 3` and watch three VLM-driven agents compete for grid cells, with a final report showing per-agent scores and a GIF.
  3. A user can run `python examples/coverage_game.py --agents 3` and watch agents cooperatively explore a scene, with coverage fraction and per-agent contribution in the final report.
  4. Replay artifacts (numbered frames + `replay.json` + summary report) are produced deterministically for every run.
**Plans**: 6 plans (historical, retrofit from issues 1–6 in `docs/issues-roadmap.md`)

Plans:
- [x] 01-01: AI2-THOR multi-agent engine wrapper (`roboclaws/core/engine.py`)
- [x] 01-02: Pluggable VLM provider protocol (`roboclaws/core/vlm.py`) — Mock / OpenAI / Anthropic / Kimi
- [x] 01-03: Overhead visualizer + frame composite (`roboclaws/core/visualizer.py`)
- [x] 01-04: Territory game (`roboclaws/games/territory.py`, `examples/territory_game.py`)
- [x] 01-05: Coverage game (`roboclaws/games/coverage.py`, `examples/coverage_game.py`)
- [x] 01-06: Game replay recorder (`roboclaws/core/replay.py`)
**UI hint**: yes

### Phase 1.5: CI + dev topology
**Goal**: Keep the demo continuously alive on GitHub Pages and codify the cloud-vs-local developer workflow.
**Depends on**: Phase 1
**Requirements**: CI-01, CI-02
**Success Criteria** (what must be TRUE):
  1. Every push to `main` publishes fresh Layer 1 + Layer 2 GIFs + reports to `miaodx.github.io/roboclaws/`.
  2. `lint-and-mock` runs on every push + PR and gates merges on ruff + format + pytest + mock-engine HTML demo.
  3. Contributors can tell at a glance from `CLAUDE.md` whether a task belongs in a cloud session or a local `local-dev` session.
**Plans**: 2 plans (historical, retrofit)

Plans:
- [x] 015-01: Headless-AI2-THOR CI workflow (`.github/workflows/ci.yml`) with Xvfb + `~/.ai2thor/` cache + `publish-pages` job
- [x] 015-02: Cloud-vs-local workflow documentation (CLAUDE.md § Cloud vs local, `docs/contributing.md`, `local-dev` issue template in #50)
**UI hint**: yes

### Phase 2: OpenClaw Gateway bridge (original)
**Goal**: Route one simulated agent through a local OpenClaw Gateway and prove the end-to-end path produces a visible artifact.
**Depends on**: Phase 1.5
**Requirements**: OC-01 (initial transport attempt — corrected in Phase 2.1)
**Success Criteria** (what must be TRUE):
  1. A contributor can run `scripts/openclaw-bootstrap.sh` followed by `examples/openclaw_demo.py` on a workstation and get a report.html for one OpenClaw-driven agent.
  2. A dedicated `openclaw-smoke` CI job publishes a `report-openclaw` artifact to `miaodx.github.io/roboclaws/openclaw/demo/` on push to main.
  3. The Gateway image is pinned to `ghcr.io/openclaw/openclaw:2026.4.14` (date-shaped tag, `OPENCLAW_IMAGE` override available).
**Plans**: Historical — superseded by Phase 2.1 transport correction.

Plans:
- [x] 02-01: First-pass OpenClaw bridge (used `/tools/invoke` — wrong endpoint, see Phase 2.1 retrospective)
- [x] 02-02: Standalone `examples/openclaw_demo.py` + `scripts/openclaw-bootstrap.sh` + `openclaw-smoke` CI job
- [x] 02-03: Pin Gateway image to `:2026.4.14` (DEC-phase-2-gateway-pinned-image)

### Phase 2.1: Transport correction (INSERTED)
**Goal**: Replace the wrong-endpoint `/tools/invoke` transport with the actually-working OpenAI-compatible `/v1/chat/completions`, plus per-agent isolation via named-agent routing.
**Depends on**: Phase 2
**Requirements**: OC-01 (corrected)
**Success Criteria** (what must be TRUE):
  1. `OpenClawProvider.get_action` routes to `model = "openclaw/<agentId>"` and the request hits `POST /v1/chat/completions`.
  2. Each named Gateway agent owns its own workspace, `SOUL.md`, `auth-profiles.json`, and MEMORY — no cross-agent leakage.
  3. Frames flow inline as base64 `data:` URLs with no bind mount; the Railway/remote-Gateway path is no longer bind-mount-bound.
**Plans**: Historical — see `docs/retrospectives/phase-2.1.md` (7 tasks T1–T7).

Plans:
- [x] 021-01: Swap transport to `/v1/chat/completions` with `model="openclaw/<agentId>"` routing (DEC-phase-2.1-transport-is-chat-completions, DEC-phase-2.1-named-agent-routing)
- [x] 021-02: Inline base64 image transport — remove bind mount, remove `.openclaw-tmp` (DEC-phase-2-inline-image-transport)
- [x] 021-03: Add real-upstream probe pre-merge (live-probe gate hardened into `feedback_live_probe_gate.md`)

### Phase 2.2: Long-running OpenClaw games
**Goal**: Run the territory and coverage games end-to-end through the Gateway with per-agent SOULs for visible personality differentiation.
**Depends on**: Phase 2.1
**Requirements**: OC-02, OC-03
**Success Criteria** (what must be TRUE):
  1. `make openclaw-territory` produces a GIF where agent trails are visibly tinted by SOUL color (aggressive=red, defensive=blue).
  2. `make openclaw-coverage` runs cleanly with `AGENT_SOULS=cooperative,cooperative` + `PERSONALITY_PROBE=0` and publishes a coverage report.
  3. Two new CI jobs (`territory-openclaw-smoke`, `coverage-openclaw-smoke`) publish Layer 3 tiles to `miaodx.github.io/roboclaws/openclaw/{territory,coverage}/`.
  4. Bootstrap's personality-divergence probe fails fast (exit 5) when two named agents report the same strategy hash, unless explicitly skipped.
**Plans**: Historical — see `docs/retrospectives/phase-2.2.md` (tasks T17–T27).

Plans:
- [x] 022-01: `AGENT_SOULS` distribution in `scripts/openclaw-bootstrap.sh` with fail-fast validation + personality probe
- [x] 022-02: SOUL overlay in visualizer (badges + tinted trails) with `tests/test_visualizer_soul_overlay.py`
- [x] 022-03: Add `territory-openclaw-smoke` + `coverage-openclaw-smoke` CI jobs + Layer 3 tiles in README
**UI hint**: yes

### Phase 2.3: Gateway digest pin — DECLINED
**Goal**: *Evaluate* whether to pin the Gateway image by `sha256:` digest instead of `:2026.4.14` tag.
**Depends on**: Phase 2.2
**Requirements**: none (pure ops decision)
**Success Criteria** (what must be TRUE):
  1. A documented decision exists on record (either "pin by digest" + PR, or "decline with rationale" + ADR).
**Outcome**: DECLINED 2026-04-20. Keep date-shaped `:2026.4.14`. LOCKED ADR recorded in `PROJECT.md` as `DEC-phase-2.3-decline-digest-pin`. One-click rollback digest preserved for emergency use:
`sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`
**Plans**: 1 plan

Plans:
- [x] 023-01: Write + record LOCKED ADR declining digest pin (`docs/retrospectives/phase-2.3.md`)

</details>

#### 🚧 v1.1 Better Views (Phase 2.4) — Active

**Milestone Goal:** Decide whether a richer per-step view (structured
grid-overhead, optionally plus chase-cam) produces measurably better VLM
play across territory / coverage / navigation, with defensible statistics
and ≤$20 spend.

### Phase 2.4: View-experiment A/B
**Goal**: Measure whether map-v2 (structured overhead) and map-v2+chase-cam help VLM agents outperform the baseline (FPV + photo overhead) across territory, coverage, and navigation games, then produce a decision record on which variant(s) graduate to the default.
**Depends on**: Phase 2.2. Issue #52 prereqs (image-payload contract + coverage semantics) were shipped pre-ingest in commit `ddfb523` (2026-04-15); both initial ingest WARNINGs verified stale and resolved 2026-04-20 — see `.planning/INGEST-CONFLICTS.md` "UPDATE 2026-04-20" header.
**Requirements**: A-03, A-04 (A-01 and A-02 shipped pre-ingest, marked Complete in REQUIREMENTS.md traceability)
**Success Criteria** (what must be TRUE):
  1. A contributor can run `examples/openclaw_demo.py --views {baseline,map-v2,map-v2+chase}` (and the same flag on `territory_game.py` / `coverage_game.py`) and observe distinct overhead rendering + optional chase-cam frame in the resulting artifacts.
  2. After the overnight Kimi sweep + NVIDIA confirm, `output/view-experiment/results.jsonl` contains runs across variants × seeds × scenes × games within the `$20` hard cap; total spend is logged per `--max-usd` gate (Kimi `$15`, NVIDIA `$5`).
  3. `docs/view-experiment-2026-04.md` ships a decision record: one-line verdict per question (map-v2 helps / doesn't, chase-cam helps / doesn't), bootstrap 95% CIs per `(variant, game)` for the primary metric, paired Wilcoxon p-values + effect sizes for {B vs A, C vs A, C vs B}, and sample GIFs per variant on a matching seed/scene.
**Plans**: TBD — awaiting `/gsd-plan-phase 2.4`. Expected shape (pre-plan draft in root `PLAN.md`):

Plans:
- [ ] 024-01: NvidiaProvider extension (A-03) — structured-output via instructor, live-probe gate pre-merge
- [ ] 024-02: `roboclaws/core/views.py` + `render_structured_map` + chase-cam API (A-04 build)
- [ ] 024-03: Overnight Kimi workhorse sweep (`--max-usd 15`) + NVIDIA confirm (`--max-usd 5`) at local workstation (T35 local-dev only)
- [ ] 024-04: Analysis script + `docs/view-experiment-2026-04.md` decision record
**UI hint**: yes

#### 📋 v1.2 Autonomous OpenClaw Loop (Phase 2.5) — Drafted, ready for plan

### Phase 2.5: Autonomous OpenClaw loop (v1 single-agent nav + human steer)
**Goal**: Invert the OpenClaw integration. Instead of pushing FPV/overhead into the agent per step, let the agent drive — one kickoff `/v1/chat/completions` call with a long wall-clock budget, and the agent pulls `observe`/`move`/`done` from a local HTTP tool server as needed. Adds stdin-based human interjection that piggybacks on tool responses.
**Depends on**: Phase 2.2 (OpenClawBridge + skill infra). Runs in parallel to Phase 2.4 — different architectural bet; does not share code paths in v1.
**Requirements**: A-06 (new — agent-driven tool loop; to be added to REQUIREMENTS.md at plan time)
**Source**: `docs/plans/phase-2.5-autonomous-nav.md` (reviewed, eng-cleared)
**Success Criteria** (what must be TRUE):
  1. `python examples/openclaw_nav_autonomous.py --scene FloorPlan201 --max-moves 50 --wall-budget 300` runs end-to-end locally; agent calls `observe` within 30 s of kickoff, takes at least one `move`, terminates via `done` or wall-clock, produces `replay.gif` + `report.html` with 👁 (seen) and 🚶 (server-side) frame badges.
  2. Human interjection mid-run (stdin line) appears in `trace.jsonl` on a tool response, in `report.html`'s tool-call log, and the agent's subsequent reasoning references it.
  3. Back-to-back runs against a long-lived Gateway show a fresh agent state on the second run (per-run workspace reset works — regression guard for `[fixed-session-prefix-leaks-memory]`).
  4. `OpenClawBridge.step()` still honors its 180 s default timeout after a `start_run(wall_budget_s=600)` call (shared-client timeout-isolation regression guard).
**Plans**: 8 tasks (T49 spike → T50-T54 build → T55 local-dev probes). See source plan for full detail.

Plans:
- [ ] 025-01 (T49): Pre-build spike — long-poll + tool-format de-risk (local-dev; gates T50-T54)
- [ ] 025-02 (T50): `roboclaws/openclaw/sim_server.py` — local HTTP tool server with frame-capture trace
- [ ] 025-03 (T51): `skills/ai2thor-navigator/SKILL.md` tool declarations (observe/move/done + human_message)
- [ ] 025-04 (T52): `OpenClawBridge.start_run(...)` — kickoff + blocking wait + workspace reset + shared-client timeout isolation
- [ ] 025-05 (T53): `examples/openclaw_nav_autonomous.py` — stdin reader + SIGINT teardown + artifact render
- [ ] 025-06 (T53-bis): `scripts/openclaw-bootstrap.sh` updates (SIM_SERVER_URL, --add-host, docs)
- [ ] 025-07 (T54): Trace → `scripts/render_autonomous_replay.py` — `replay.gif` + `report.html` with 👁/🚶 badges
- [ ] 025-08 (T55): Local-dev validation — 6 probes against real Gateway + Kimi (live-probe gate per `feedback_live_probe_gate.md`)
**UI hint**: yes

#### 📋 v2.0 Isaac Lab (Phase 3) — Deferred indefinitely

### Phase 3: Isaac Lab migration
**Goal**: Migrate from AI2-THOR to Isaac Lab for humanoid (Unitree G1) and multi-embodiment navigation, with a two-level architecture (OpenClaw VLM planner at 1–5 Hz producing `(vx, vy, ωz)` consumed by a pre-trained RL locomotion policy at 200 Hz).
**Depends on**: Phase 2.4 (decision record from view-experiment A/B — the winning view variant informs what Phase-3 scenes need to render) **and** availability of indoor USD scenes + GPU hardware + 1–2 weeks of ramp-up time. (Original dep on old-Phase-2.5 "ship winning view" is obsolete — that phase was replaced by the autonomous-nav track; the underlying decision record still lives in Phase 2.4.)
**Requirements**: P3-01, P3-02, P3-03, P3-04, P3-05 (v2 requirements)
**Success Criteria** (what must be TRUE):
  1. A contributor can run an Isaac Lab demo of one Unitree G1 navigating an indoor USD scene under OpenClaw-VLM high-level control + a pre-trained RL locomotion policy.
  2. The ROSClaw (or equivalent direct-Python) bridge carries `(vx, vy, ωz)` commands from the VLM planner to the locomotion policy at a verified rate (≥1 Hz planner, ≥200 Hz locomotion).
  3. The published Layer 3 demo matrix adds a Phase-3 tile showing the Isaac Lab run alongside the AI2-THOR tiles.
**Plans**: TBD — explicitly deferred per `docs/technical-design.md` § Phase 3. Revisit when GPU + indoor USD scenes are available.

Plans:
- [ ] 03-01: Ramp Isaac Lab toolchain (AGILE, COMPASS, GR00T N1.6) on target GPU
- [ ] 03-02: Build or source an indoor USD scene compatible with G1 navigation
- [ ] 03-03: Wire OpenClaw VLM planner ↔ RL locomotion bridge
- [ ] 03-04: Integrate object-interaction action set (P3-05)
- [ ] 03-05: Publish Phase-3 tile in the live demo matrix

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 1.5 → 2 → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 3

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core simulation + games | v1.0 | 6/6 | Complete | 2026-04 (pre-Phase-2) |
| 1.5. CI + dev topology | v1.0 | 2/2 | Complete | 2026-04 (pre-Phase-2) |
| 2. OpenClaw Gateway bridge (original) | v1.0 | 3/3 | Complete | 2026-04 |
| 2.1. Transport correction | v1.0 | 3/3 | Complete | 2026-04 |
| 2.2. Long-running OpenClaw games | v1.0 | 3/3 | Complete | 2026-04-16 |
| 2.3. Gateway digest pin | — | 1/1 | Declined | 2026-04-20 |
| 2.4. View-experiment A/B | v1.1 | 0/6 | Not started (drafted, awaiting plan) | - |
| 2.5. Autonomous OpenClaw loop | v1.2 | 0/8 | Not started (drafted, ready for plan) | - |
| 3. Isaac Lab migration | v2.0 | 0/5 | Deferred | - |
