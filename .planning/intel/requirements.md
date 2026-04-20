# Requirements

Synthesized from the two SPEC-classified docs (no PRDs in the ingest set).
Requirements are extracted from user-facing goals inside `docs/technical-design.md`
and `PLAN.md`; acceptance criteria are inherited from the same source and the
shipped state documented in the phase-2/2.1/2.2 retrospectives (DOC context).

Each entry links back to its source. Where acceptance criteria come from
multiple sources, all variants are preserved (the doc-conflict-engine forbids
silent merging of competing acceptance variants).

Precedence applied: SPEC beats DOC; no ADR constrains a requirement here.

---

## REQ-ai2thor-multi-agent-engine

- source: docs/technical-design.md § AI2-THOR Multi-Agent Technical Specs;
  docs/issues-roadmap.md Issue 1
- scope: `roboclaws/core/engine.py`
- description: Wrap the AI2-THOR Controller for multi-agent management.
  Support iTHOR scenes (FloorPlan1-430). Configurable `agentCount`, grid-based
  movement (`gridSize=0.25`, `rotateStepDegrees=90`, `snapToGrid=True`). Expose
  per-agent frame, metadata, position, rotation, `lastActionSuccess`. Include
  overhead camera via `GetMapViewCameraProperties` + `AddThirdPartyCamera`.
  Handle action failures gracefully.
- acceptance: pytest passes with a test that initializes 2+ agents, moves
  them, and reads frames.

## REQ-vlm-provider-pluggable

- source: docs/technical-design.md § VLM Strategy; docs/issues-roadmap.md
  Issue 2; PLAN.md § Task T29a (NvidiaProvider extension)
- scope: `roboclaws/core/vlm.py`
- description: `VLMProvider` protocol with implementations for:
  Kimi (Moonshot API, OpenAI-compatible), OpenAI (GPT-4o, GPT-4o-mini),
  MockProvider (returns random valid actions). All providers accept base64
  images + structured state JSON, return
  `{"reasoning": "...", "action": "..."}`. Support `--model` CLI flag.
  Log cumulative API cost per session. Anthropic provider optional.
- follow-on (PLAN.md T29a, not yet shipped): add `NvidiaProvider` against
  `https://integrate.api.nvidia.com/v1` with structured-output via instructor;
  canonical alias `"nvidia"` → current curated pick (`meta/...` or
  `nvidia/...-nano-vl-8b-v1`), final choice via live probe at T35 prep.
- acceptance (shipped portion): MockProvider works in CI; real providers work
  locally with API keys.
- acceptance (T29a portion): unit tests pass with mocked SDK; 3-image payload
  serializes to OpenAI image format; `ProviderStatus.to_dict()` shape parity
  with other providers; **live-probe gate** (per `feedback_live_probe_gate.md`)
  before merge.

## REQ-overhead-visualizer

- source: docs/technical-design.md § Overhead View; docs/issues-roadmap.md
  Issue 3
- scope: `roboclaws/core/visualizer.py`
- description: Generate 2D overhead grid map from AI2-THOR scene data showing
  agent positions (colored markers), claimed/unclaimed cells (territory),
  covered/uncovered areas (coverage). Composite first-person frames from all
  agents side-by-side with the overhead map. Output as PIL Image or numpy
  array. Support saving as PNG/GIF.
- acceptance: given mock game state, produces correct overhead visualization.

## REQ-soul-overlay-in-visualizer

- source: docs/retrospectives/phase-2.2.md § Task 19.8 (shipped per T17-T27);
  README.md Layer 3
- scope: `roboclaws/core/visualizer.py`
- description: When `--backend openclaw` is active and `AGENT_SOULS` is set,
  render per-agent SOUL name as a colored badge on each agent sprite in the
  overhead view, and tint each agent's trail by SOUL color.
  Palette: `aggressive=red`, `defensive=blue`, `cooperative=green`,
  `default=grey`.
- acceptance: `tests/test_visualizer_soul_overlay.py` — render with mock
  `agent_labels=["aggressive","defensive"]`, assert pixel sample at agent-0
  sprite location has red component dominant + agent-1 has blue dominant.
  (14 tests shipped per phase-2.2 retrospective.)

## REQ-territory-game

- source: docs/technical-design.md § Scenario A Territory Control;
  docs/issues-roadmap.md Issue 4
- scope: `roboclaws/games/territory.py`, `examples/territory_game.py`
- description: Grid-based territory claiming. Each agent claims cells it
  visits; claimed cells are locked. Track per-agent score, territory
  connectivity. Turn-based stepping (round-robin). Configurable max steps and
  scene. Compute metrics: cells per agent, connectivity ratio, blocking events
  detected. Termination when all reachable cells claimed or max steps reached.
  Example script supports `--backend {vlm,openclaw}` (default `vlm`) with
  `direct` as deprecated alias.
- acceptance (design): game runs with MockProvider, produces correct state
  transitions and final scores.
- acceptance-variant-A (technical-design.md original intent, field-of-view
  based VLM I/O): each VLM turn receives first-person camera frame + overhead
  grid map (marking self ★, opponents ●, claimed/unclaimed areas) + structured
  JSON state.
- acceptance-variant-B (05-real-model-smoke-validation observed shipped
  behavior, 2026-04-14): game loops call
  `provider.get_action(images=[], state=game_state)` — state-only, no images
  fed. **Known divergence from the design spec.** Tracked in issue #52.
  → NOTE: this is captured as a WARNING in INGEST-CONFLICTS.md because the
  design spec and the observed shipping behavior disagree about the image
  payload contract.

## REQ-coverage-game

- source: docs/technical-design.md § Scenario B Cooperative Coverage;
  docs/issues-roadmap.md Issue 5
- scope: `roboclaws/games/coverage.py`, `examples/coverage_game.py`
- description: Track which grid cells have been within any agent's field of
  view. Expose coverage percentage, per-agent contribution ratio, work balance
  metric. Termination when 95% coverage or max steps. Provide teammate
  positions and coverage map to each agent's prompt. Example script supports
  `--backend {vlm,openclaw}` mirroring REQ-territory-game.
- acceptance (design): coverage increases monotonically; 95% threshold is a
  meaningful termination condition; metrics computed correctly.
- acceptance-variant-A (technical-design.md): coverage is **field-of-view
  based** — cells within an agent's FoV are marked as "covered".
  95% target is reachable in 100 steps for 2-3 agents.
- acceptance-variant-B (05-real-model-smoke-validation shipped 2026-04-14):
  coverage is **visited-cells based**; after 100 steps only 21 / 234 cells
  (8.97%) were covered; termination was `max_steps`, never 95%. **Known
  divergence from the design spec.** Tracked in issue #52.
  → NOTE: this is captured as a WARNING in INGEST-CONFLICTS.md. The source
  doc (`05-real-model-smoke-validation.md`) explicitly says the follow-up
  (issue #52) must decide **one coherent story**: field-of-view or
  visited-cells, then update the other doc to match. Synthesis does NOT pick.

## REQ-game-replay-recorder

- source: docs/technical-design.md § Day 2 Deliverables;
  docs/issues-roadmap.md Issue 6
- scope: `roboclaws/core/replay.py`
- description: Record per-step data — all agent frames, overhead map, game
  state JSON, VLM prompts and responses. Save as directory of numbered frames
  + `replay.json` manifest. Support generating GIF via imageio. Generate
  summary report (final scores, total cost, step count).
- acceptance: replay directory structure correct; GIF generation works.

## REQ-ci-headless-ai2thor

- source: docs/issues-roadmap.md Issue 7; docs/contributing.md § CI overview
- scope: `.github/workflows/ci.yml`
- description: Install Xvfb + ai2thor. Cache `~/.ai2thor/` for Unity build
  (~1 GB). Run ruff lint + format check + pytest with MockProvider.
  AI2-THOR-touching tests use `xvfb-run`. Smoke test initializes multi-agent
  scene, steps each agent, verifies frames are non-empty numpy arrays. Jobs:
  `lint-and-mock` (every push + PR), `real-model-smoke` (push to main only,
  Kimi + real AI2-THOR), `openclaw-smoke` / `territory-openclaw-smoke` /
  `coverage-openclaw-smoke` (push to main only, `continue-on-error: true`),
  `publish-pages` (downloads artifacts → GitHub Pages).
- acceptance: CI passes green on push to main; Layer 1-2-3 reports publish to
  Pages at `miaodx.github.io/roboclaws/`.

## REQ-openclaw-gateway-bridge

- source: docs/technical-design.md § Phase 2; docs/issues-roadmap.md Issue 12;
  docs/retrospectives/phase-2.1.md Task 9; docs/openclaw-local.md
- scope: `roboclaws/openclaw/bridge.py`, `scripts/openclaw-bootstrap.sh`,
  `examples/openclaw_demo.py`
- description: Connect AI2-THOR sim to a local OpenClaw Gateway via its
  OpenAI-compatible `POST /v1/chat/completions` endpoint. Each simulation
  agent routes to its own named Gateway agent
  (`model="openclaw/<agent_prefix><id>"`) so per-agent SOUL, MEMORY, and auth
  are preserved independently. Frames flow inline as base64 data URLs.
  First-run setup via `scripts/openclaw-bootstrap.sh`. `OpenClawProvider`
  honors the standard `VLMProvider` contract; `get_action(images, state)`
  already reads `state["my_agent_id"]` for turn routing.
- acceptance: `openclaw-smoke` CI job runs `scripts/openclaw-bootstrap.sh` →
  `examples/openclaw_demo.py` → produces non-empty `report-openclaw` artifact
  published at `https://miaodx.github.io/roboclaws/openclaw/demo/report.html`
  (`HTTP/2 200`).

## REQ-openclaw-per-agent-souls

- source: docs/retrospectives/phase-2.2.md (Tasks T17–T27, shipped);
  docs/openclaw-local.md § Per-agent personalities; README.md Layer 3
- scope: `scripts/openclaw-bootstrap.sh`, `examples/territory_game.py`,
  `examples/coverage_game.py`, `skills/ai2thor-navigator/souls/*`,
  `roboclaws/core/visualizer.py`
- description: Bootstrap accepts `AGENT_SOULS` env var (csv positional or
  `agent-N:soul` dict form). Copies `<SOULS_DIR>/<soul>.md` into each named
  agent's workspace as `SOUL.md`. Length of csv must match `AGENTS`. Unknown
  soul name → fail fast. Stale `SOUL.md` from prior runs is `rm -f`'d before
  copy. Post-startup personality divergence probe: ask every agent the same
  strategy question; if two hashes collide, exit 5 (unless
  `PERSONALITY_PROBE=0` or all souls identical).
- acceptance: `tests/test_openclaw_bootstrap.py` asserts SOUL distribution
  contract; territory run with `aggressive,defensive` produces visually
  distinct trails (red vs blue) in the published GIF; coverage run with
  `cooperative,cooperative` runs cleanly with `PERSONALITY_PROBE=0`.

## REQ-view-experiment-ab (Phase 2.4 — not shipped)

- source: PLAN.md § Phase 2.4 Map representation & view composition A/B
- scope: `roboclaws/core/views.py` (new), `roboclaws/core/visualizer.py`
  (`render_structured_map`), `roboclaws/core/engine.py` (chase-cam API),
  `examples/view_experiment.py` (new), `scripts/analyze_view_experiment.py`
  (new), `docs/view-experiment-2026-04.md` (writeup)
- description: Run an A/B/C experiment across three image-input variants:
  - A (baseline): current 2 images — FPV + photo overhead
  - B (map-v2): FPV + structured grid-overhead (unreachable dark, reachable
    light, claimed-by-self/other distinct colors, agent-triangle arrow)
  - C (map-v2 + chase-cam): B + third-person chase-cam frame
    (~1.0 m behind, ~1.5 m above, ~20° pitch down, yaw-matched)
  Add `--views {baseline,map-v2,map-v2+chase}` to `openclaw_demo.py`,
  `territory_game.py`, `coverage_game.py`. Harness sweeps
  variants × seeds × scenes × games → `output/view-experiment/results.jsonl`.
  Analysis script emits summary with bootstrap 95% CIs and paired Wilcoxon
  signed-rank tests (paired by `(seed, scene, game)`).
- acceptance-primary: text/markdown summary in
  `docs/view-experiment-2026-04.md` with:
  - one-line verdict per question (map-v2 helps / doesn't, chase-cam helps /
    doesn't)
  - bootstrap 95% CIs per `(variant, game)` for primary metric
    (`cells_claimed_sum` for territory, `coverage_fraction` for coverage,
    `visited_cells` for navigation)
  - paired Wilcoxon p-values and effect sizes for {B vs A, C vs A, C vs B}
  - sample GIFs per variant on matching seed/scene
  - decision record: which variant(s) graduate to Phase 2.5 default
- acceptance-budget: Kimi workhorse sweep ≤ $15 via `--max-usd 15`;
  NVIDIA confirm ≤ $5 via `--max-usd 5`; hard cap $20 total.
- acceptance-gates: live probe gate on NvidiaProvider before overnight sweep
  (per `feedback_live_probe_gate.md`); cloud-session MUST NOT run T35 (local
  `KIMI_API_KEY` + `NVIDIA_API_KEY` + real AI2-THOR + wallclock required).

## REQ-development-topology-cloud-vs-local

- source: CLAUDE.md § Cloud vs local development; docs/contributing.md;
  AGENTS.md §7 (referenced)
- scope: contributor workflow, CI gating
- description: Two-topology dev: (a) cloud sessions (Claude Code web) — no
  API keys, no Unity, no GPU; validated by `lint-and-mock`. (b) local sessions
  (workstation) — real Kimi / real AI2-THOR / real Gateway. Every `local-dev`
  tagged task, every multi-round debug loop, every real-model validation
  starts locally. CI mirrors local proof continuously but is not where proof
  starts.
- acceptance: PRs whose core claim depends on real hardware or real VLM
  behavior document the local validation explicitly; otherwise a `local-dev`
  issue is filed (template: issue #50).
