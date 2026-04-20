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
      **Semantics under review — see Active requirement A-02 (issue #52).**
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

### Active (issue #52 + Phase 2.4)

- [ ] **A-01** (image-payload contract resolution): Fix game loops in
      `roboclaws/games/{territory,coverage}.py` to pass
      `images=[fpv, overhead]` through to `provider.get_action`. Currently
      `images=[]`. Required for the A/B sweep to measure anything
      image-related. Tracked via issue #52; ingest WARNING (2 of 2).
- [ ] **A-02** (coverage semantics resolution): Pick ONE coherent coverage
      definition between field-of-view (SPEC) and visited-cells (shipped).
      Tracked via issue #52; ingest WARNING (1 of 2). Documentation must
      match the final code choice. Smoke expectations updated accordingly.
- [ ] **A-03** (REQ-vlm-provider-pluggable — NvidiaProvider extension): Add
      `NvidiaProvider` against `https://integrate.api.nvidia.com/v1` with
      structured output (instructor). Canonical alias `"nvidia"` →
      `nvidia/nvidia/nemotron-nano-12b-v2-vl` (final pick via live probe
      at T35 prep). Live-probe gate before merge.
- [ ] **A-04** (REQ-view-experiment-ab): A/B/C experiment — variant A
      baseline (FPV + photo overhead), variant B map-v2 (FPV + structured
      grid overhead with reachable/claimed/agent-arrow encoding), variant C
      B + chase-cam frame (~1.0 m behind, ~1.5 m above, ~20° pitch). Add
      `--views {baseline,map-v2,map-v2+chase}` to
      `openclaw_demo.py`, `territory_game.py`, `coverage_game.py`. Harness
      sweeps variants × seeds × scenes × games →
      `output/view-experiment/results.jsonl`. Bootstrap 95% CIs + paired
      Wilcoxon tests. Wallet gates: Kimi `--max-usd 15`, NVIDIA `--max-usd 5`,
      $20 hard cap. Decision record: which variant graduates to default.
- [ ] **A-05** (ship winning variant as default): After A-04's decision
      record, wire the winning variant into the default `--views` of
      `openclaw_demo.py` / `territory_game.py` / `coverage_game.py`. Update
      README Layer 3 narrative + CI job configs to exercise the new default.
      Archive the losing variants behind an explicit `--views` flag for
      reproducibility.

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
| CORE-04 | Phase 1 | Complete (semantics-clean pending A-01) |
| CORE-05 | Phase 1 | Complete (semantics-clean pending A-01, A-02) |
| CORE-06 | Phase 1 | Complete |
| CI-01 | Phase 1.5 | Complete |
| CI-02 | Phase 1.5 | Complete |
| OC-01 | Phase 2 (+ 2.1 transport correction) | Complete |
| OC-02 | Phase 2.2 | Complete |
| OC-03 | Phase 2.2 | Complete |
| A-01 | Phase 2.4 (prereq task, gates the sweep) | Pending |
| A-02 | Phase 2.4 (prereq task, gates the sweep) | Pending |
| A-03 | Phase 2.4 (harness dependency) | Pending |
| A-04 | Phase 2.4 | Pending |
| A-05 | Phase 2.5 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-20 after new-mode ingest bootstrap*
