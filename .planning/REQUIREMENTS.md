# Requirements: roboclaws

**Defined:** 2026-04-20 (new-mode ingest bootstrap)
**Core Value:** First public demonstration of multiple OpenClaw agent
instances simultaneously controlling multiple simulated robots in
competition and cooperation, with visible output for every feature.

## v1 Requirements

Requirements for the first public demo. Each maps to exactly one roadmap
phase. Source: `.planning/intel/requirements.md` (11 requirements extracted
from SPEC docs + 1 continuation requirement surfaced by intel).

### Core simulation + games

- [x] **CORE-01** (REQ-ai2thor-multi-agent-engine): Wrap AI2-THOR Controller
      for multi-agent management on iTHOR scenes. Config: `agentCount`,
      `gridSize=0.25`, `rotateStepDegrees=90`, `snapToGrid=True`. Expose
      per-agent frame / metadata / position / rotation / `lastActionSuccess`
      on `event.events[i]`. Overhead camera via
      `GetMapViewCameraProperties` + `AddThirdPartyCamera`.
- [x] **CORE-02** (REQ-vlm-provider-pluggable — shipped subset):
      `VLMProvider` protocol with MockProvider + OpenAI (GPT-4o /
      GPT-4o-mini) + Anthropic (Claude) + Kimi (Moonshot via custom
      `base_url`). Accepts base64 images + structured state JSON, returns
      `{"reasoning": "...", "action": "..."}`. `--model` CLI flag.
      Cumulative API cost logged per session.
- [x] **CORE-03** (REQ-overhead-visualizer): 2D overhead grid map showing
      agent positions, claimed/unclaimed cells (territory), covered/uncovered
      areas (coverage). Side-by-side composite with per-agent FPV. PNG/GIF
      output.
- [x] **CORE-04** (REQ-territory-game): Grid-based territory claiming. Each
      agent claims cells it visits (locked). Per-agent score, connectivity,
      blocking-events. Round-robin turns, configurable max_steps + scene.
      `--backend {vlm,openclaw}`.
- [x] **CORE-05** (REQ-coverage-game): Cooperative coverage with per-agent
      contribution + work-balance metrics. Provide teammate positions +
      coverage map to each agent's prompt. `--backend {vlm,openclaw}`.
      Field-of-view coverage accounting (`coverage.py:185-211`, yaw +
      half-FOV angle math). Stale-ingest WARNING on semantics resolved
      2026-04-20 — issue #52 closed 2026-04-15T05:13:18Z.
- [x] **CORE-06** (REQ-game-replay-recorder): Record per-step all-agent
      frames + overhead + state JSON + VLM prompts/responses. Directory of
      numbered frames + `replay.json`. GIF via imageio. Summary report
      (scores, cost, step count).

### CI + dev topology

- [x] **CI-01** (REQ-ci-headless-ai2thor): Install Xvfb + ai2thor, cache
      `~/.ai2thor/`. Jobs: `lint-and-mock` (every push+PR), `real-model-smoke`
      (push to main, Kimi + real AI2-THOR), `openclaw-smoke` /
      `territory-openclaw-smoke` / `coverage-openclaw-smoke` (push to main,
      `continue-on-error`), `publish-pages` → GitHub Pages at
      `miaodx.github.io/roboclaws/`.
- [x] **CI-02** (REQ-development-topology-cloud-vs-local): Cloud sessions
      validated by `lint-and-mock`; local sessions own every `local-dev`
      task. PRs whose core claim depends on real hardware document local
      validation or file a `local-dev` issue (template: #50).

### OpenClaw integration

- [x] **OC-01** (REQ-openclaw-gateway-bridge): `OpenClawProvider` talks to a
      local Gateway via `POST /v1/chat/completions`, `model =
      "openclaw/<agent_prefix><id>"`, inline base64 frames in
      `messages[]`. Bootstrap via `scripts/openclaw-bootstrap.sh`.
      `openclaw-smoke` CI publishes `report-openclaw` artifact to Pages.
- [x] **OC-02** (REQ-openclaw-per-agent-souls): Bootstrap accepts
      `AGENT_SOULS` (csv or dict form). Copies
      `<SOULS_DIR>/<soul>.md` into each named agent workspace as `SOUL.md`.
      Fail-fast on length mismatch or unknown soul. Stale `SOUL.md` removed.
      Post-startup personality divergence probe (hash collision ⇒ exit 5)
      unless `PERSONALITY_PROBE=0` or all souls identical.
- [x] **OC-03** (REQ-soul-overlay-in-visualizer): When `--backend openclaw`
      + `AGENT_SOULS` set, render per-agent SOUL name as a colored badge and
      tint each agent's trail by SOUL color. Palette:
      `aggressive=red`, `defensive=blue`, `cooperative=green`, `default=grey`.

### Active / Deferred

- [x] **A-01** (image-payload contract): SHIPPED 2026-04-15 via commit
      `ddfb523` — `examples/territory_game.py:316` and
      `examples/coverage_game.py:357` both pass `images=prompt_images`
      through `game.decide()`. Stale-ingest WARNING resolved 2026-04-20;
      issue #52 closed 2026-04-15T05:13:18Z.
- [x] **A-02** (coverage semantics): SHIPPED — `coverage.py:185-211`
      uses field-of-view accounting (yaw + half-FOV angle math).
      Stale-ingest WARNING resolved 2026-04-20; issue #52 closed.
- [ ] **A-03** (REQ-vlm-provider-pluggable — NvidiaProvider extension): Add
      `NvidiaProvider` against `https://integrate.api.nvidia.com/v1` with
      structured output (instructor). Canonical alias `"nvidia"` →
      `nvidia/nvidia/nemotron-nano-12b-v2-vl` (final pick via live probe
      at T35 prep). Live-probe gate before merge.
- [x] **A-04** (REQ-view-experiment-ab): RESOLVED 2026-04-24. The repo
      standardized on `map-v2+chase`; the old multi-variant live sweep is
      historical only. Phase artifacts are archived under
      `.planning/milestones/v1.98-phases/02.4-view-experiment-ab/`.
- [ ] **A-05** (ship winning variant as default): DEFERRED 2026-04-20.
      After A-04's decision record, would wire the winning variant into the
      default `--views`. Was mapped to old Phase 2.5 ("ship winning view");
      that phase was replaced by Phase 2.5 autonomous-nav (see A-06). A-05
      is not dropped — it graduates to a new phase if/when Phase 2.4's
      decision record lands. Scope: default `--views` switch + README +
      CI smoke refresh.
- [x] **A-06
** (agent-driven tool loop): Invert the OpenClaw integration.
      Instead of the push model (`bridge.step()` shoves FPV+overhead per
      step), one long-lived kickoff `/v1/chat/completions` call with
      `wall_budget_s`; the agent pulls three tools (`observe`,
      `move(direction)`, `done(reason)`) as needed. Stdin-based human
      interjection piggybacks on tool responses via `human_message`.
      Per-run workspace reset wipes
      `/home/node/.openclaw/workspaces/agent-<id>/state/` before each
      kickoff. Trace + `report.html` with 👁 (seen) / 🚶 (server-side) frame
      badges. Shared bridge-client 180s timeout preserved (regression-
      tested). Additive — does not touch push-model code paths.
      **Tool-surface contract (locked 2026-04-21 after Phase 2.5 superseded)**:
      the three tools are exposed as **first-class MCP tools** served over
      streamable-http from roboclaws; the agent runs under Gateway tool
      `profile: minimal` (no `exec`, no generic `image`, no `curl`-via-shell)
      so its only path to the world is the MCP surface. The earlier
      Phase 2.5 contract (agent curls the HTTP server from `exec`) is
      explicitly out of scope — see Phase 2.5 in ROADMAP.md for the lesson.
      Live-probe gate: container → host MCP streamable-http probe + agent
      verifies `observe` returns multimodal images (spike baseline 2026-04-21).

- [⛔] **A-07** (REQ-split-model-navigation): CANCELLED 2026-06-04. Originally:
      enable text-only reasoning models to drive autonomous OpenClaw navigation
      by intercepting image-bearing `roboclaws__observe` results at the MCP
      server layer and converting them to text via a vision model. Cancelled
      because the repo standardized on the vision-capable `mimo-v2.5` as the
      single supported MiMo route; the text-only main-model premise and the
      shipped text-bridge foundation were removed in the same change. Reopen
      only if a text-only main-model requirement returns.

- [x] **A-08** (REQ-refactor-regression-safety): Add refactor-safety harnesses
      that freeze the critical direct-VLM / territory / coverage / OpenClaw
      contracts with tiny fixtures and tests, capture append-only
      `results.jsonl` rows plus replay artifacts from the existing runners,
      and compare baseline vs candidate runs by stable coordinates with
      threshold-based gates instead of exact reasoning-text equality.
      Completed in GSD Phase 4; archived under
      `.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/`.

- [x] **A-09** (REQ-generic-mcp-entrypoint-semantic-capabilities): Add a
      metadata-first generic MCP entrypoint/router that loads exactly one
      backend/domain-specific contract profile, declares semantic capability
      families and provenance expectations, represents existing AI2-THOR
      navigation and MolmoSpaces cleanup contracts, and fails closed if
      canonical profiles expose simulator accelerators or Molmo private
      evaluator truth. Completed in GSD Phase 136 from
      `docs/retrospectives/plans/generic-mcp-entrypoint-semantic-capabilities.md`.

## v2 Requirements

Deferred to Phase 3 (Isaac Lab).

### Phase 3 — Isaac Lab migration

- **P3-01**: Migrate to Isaac Lab (Unitree G1 + multi-embodiment nav).
- **P3-02**: Two-level architecture — OpenClaw VLM planner (1-5 Hz) →
  `(vx, vy, ωz)` → pre-trained RL locomotion policy (200 Hz).
- **P3-03**: Bridge via ROSClaw or direct Python integration.
- **P3-04**: Integrate AGILE (G1 velocity tracking), COMPASS
  (cross-embodiment nav), GR00T N1.6 (Cosmos-Reason-2B VLM + diffusion).
- **P3-05**: Object-interaction action set (`PickupObject`, `PutObject`,
  `OpenObject`, `CloseObject`, `ToggleObjectOn/Off`).

## Out of Scope

| Feature | Reason |
|---------|--------|
| ProcTHOR scenes | Multi-agent unresolved bugs (AI2-THOR #1169, #1265) |
| MolmoSpaces | No multi-agent support |
| Habitat 3.0 / PARTNR | Setup exceeds thin-demo scope |
| Digest-pinning the Gateway image | DECLINED (LOCKED ADR 2026-04-20); `OPENCLAW_IMAGE` override is the rollback |
| Cross-run MEMORY persistence | DEC-phase-2.2-within-run-memory-scope |
| Persona Showdown / UC1-UC2 framing | REJECTED at 2026-04-16 final gate |
| `:free` OpenRouter endpoints | No tool-use support (Gateway edge returns 404) |
| Aggressive-tool-calling VLMs on webchat | Deadlock per `isKnownChannel` gotcha |
| Object-interaction actions | Phase 3 only |

## Traceability

Which phases cover which requirements. Status reflects shipped state at
2026-04-20 per retrospectives.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Complete |
| CORE-02 | Phase 1 | Complete |
| CORE-03 | Phase 1 | Complete |
| CORE-04 | Phase 1 | Complete |
| CORE-05 | Phase 1 | Complete (FOV accounting confirmed 2026-04-20) |
| CORE-06 | Phase 1 | Complete |
| CI-01 | Phase 1.5 | Complete |
| CI-02 | Phase 1.5 | Complete |
| OC-01 | Phase 2 (+ 2.1 transport correction) | Complete |
| OC-02 | Phase 2.2 | Complete |
| OC-03 | Phase 2.2 | Complete |
| A-01 | Phase 2.4 | Complete (shipped 2026-04-15 pre-ingest) |
| A-02 | Phase 2.4 | Complete (shipped 2026-04-15 pre-ingest) |
| A-03 | Phase 2.4 (harness dependency) | Pending |
| A-04 | Phase 2.4 | Complete / superseded by `map-v2+chase` decision lock |
| A-05 | (deferred — formerly Phase 2.5 "ship winning view"; awaits a new phase) | Deferred |
| A-06 | Phase 2.6 (autonomous-nav, MCP tool surface; Phase 2.5 superseded 2026-04-21) | Complete (shipped 2026-04-21) |
| A-07 | Phase 2.8 | Cancelled 2026-06-04 (standardized on vision-capable `mimo-v2.5`) |
| A-08 | Phase 4 | Complete |
| A-09 | Phase 136 | Complete |

**Coverage:**
- v1 requirements: 19 total (A-09 added 2026-05-14)
- Mapped to phases: 18 active + 1 deferred
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-05-19 after v1.98 planning archive*
