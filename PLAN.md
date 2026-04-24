# Roboclaws — Active Plan

This file holds the **current phase** only. Shipped phases live under
[`docs/retrospectives/`](docs/retrospectives/):

- [`phase-2.md`](docs/retrospectives/phase-2.md) — Phase 2: OpenClaw Integration (completion plan)
- [`phase-2.1.md`](docs/retrospectives/phase-2.1.md) — Phase 2.1 Amendment: Transport Correction + retrospective
- [`phase-2.2.md`](docs/retrospectives/phase-2.2.md) — Phase 2.2: Long-running OpenClaw games + autoplan review + retrospective
- [`phase-2.3.md`](docs/retrospectives/phase-2.3.md) — Phase 2.3: Digest pinning (declined 2026-04-20)

---

> **Status (2026-04-21):** Phase 2.4 has been ingested into GSD at
> [`.planning/phases/02.4-view-experiment-ab/`](.planning/phases/02.4-view-experiment-ab/).
> This root file now serves as the pre-GSD source draft. The authoritative
> execution order lives in the GSD phase files, with `02.4-01` explicitly
> landing the single-agent `examples/openclaw_demo.py` path first before
> territory/coverage and the experiment harness.
>
> **Update (2026-04-24):** The original multi-variant A/B/C study is now
> historical context only. Product/runtime direction is locked to
> `map-v2+chase`; the main examples no longer support `baseline` or `map-v2`
> as live runtime modes. See
> [`docs/view-experiment-2026-04.md`](docs/view-experiment-2026-04.md).

# Phase 2.4 — Map representation & view composition A/B (Source Draft)

## Problem Statement

VLM agents currently receive two images per step: a first-person camera
frame and a photorealistic top-down overhead with grid tints + agent
dots. Two open questions the team wants answered with data, not vibes:

1. **Does a structured occupancy-grid-style overhead beat the photo
   overhead?** The current top-down leans on VLM segmentation: the model
   has to re-infer walls and free space every step from pixels. AI2-THOR
   already exposes ground-truth reachability via
   `GetReachablePositions` — we can pre-render walls/free/claimed as
   distinct regions. Open question: does that actually help the model,
   or does the photo prior win?
2. **Does adding a third over-the-shoulder chase-cam view improve
   navigation decisions?** Prior user projects saw real gains from a
   slightly-elevated behind-the-agent view for near-obstacle turn
   decisions. Want to reproduce that here and, specifically, separate
   its contribution from the map-v2 contribution so we know which lever
   matters.

The deliverable is a measured answer (with CIs and paired significance
tests), not a shipped feature. If variant C wins, Phase 2.5 ships it as
the default. If variant A wins, we stop spending tokens on a second
image.

## Scope

### In scope

- Three image-input variants for existing games:
  - **A (baseline)**: current 2 images — FPV + `render_overhead_map`
    with photorealistic top-down + cell tints + agent dots.
  - **B (map-v2)**: 2 images — FPV + **structured overhead**: pure grid
    rendering driven by `GetReachablePositions`. Unreachable = solid
    dark; reachable-unclaimed = light; claimed-by-self, claimed-by-
    other-i, covered = distinct colors. Agent marker = arrow in heading
    direction, not circle.
  - **C (map-v2 + chase-cam)**: 3 images — FPV + map-v2 + third-person
    over-the-shoulder view via a per-agent `AddThirdPartyCamera`
    (~1.0 m behind, ~1.5 m above, ~20° pitch down) with per-step
    `UpdateThirdPartyCamera` to follow the active agent.
- Three game paths must support the `--views` flag: `openclaw_demo.py`
  (navigation), `territory_game.py`, `coverage_game.py`.
- A/B harness `examples/view_experiment.py` that sweeps variants × seeds
  × scenes × games and emits `output/view-experiment/results.jsonl` +
  per-run replay directories.
- Analysis script `scripts/analyze_view_experiment.py`: reads the JSONL,
  emits a summary table with bootstrap 95% CIs and paired Wilcoxon
  signed-rank tests (paired by `(seed, scene, game)` tuple).
- Writeup in `docs/view-experiment-2026-04.md` with sample GIFs
  per variant and a one-line verdict per question.
- A new `NvidiaProvider` that talks to `https://integrate.api.nvidia.com/v1`
  (OpenAI-compatible surface) so we can drive NVIDIA-hosted VLMs with
  the same `get_action(images, state)` contract. Specific model choice
  is a T29a sub-decision (probably `meta/llama-4-maverick-17b-128e-instruct`
  or `nvidia/llama-3.1-nemotron-nano-vl-8b-v1`, probed live).
- Local-dev execution: 5 seeds × 3 scenes × 2 games × 3 variants = 90
  runs on `kimi-for-coding` as the workhorse (reuses the existing
  `KimiCodingProvider` + its circuit-breaker machinery from Phase 2.2);
  12-run confirm set on the chosen NVIDIA model comparing the top two
  variants from the Kimi study.

### Not in scope

- Integrating a real ROS2-nav / NavMap occupancy-grid service. Map-v2
  is an AI2-THOR-native overlay, not a general navigation stack.
- Per-agent chase-cam tuning per SOUL (e.g., aggressive gets lower FOV).
  Single fixed pose for all agents.
- Changing the **action space** or game rules. This phase only touches
  image inputs, not the decision model.
- Shipping the winning variant as the default. That is a follow-up
  phase (Phase 2.5) gated on the results here.
- Running the experiment on GPT-4o / Claude Sonnet. Those models are
  parked this phase; if a variant wins decisively on Kimi + NVIDIA,
  Phase 2.5 can optionally re-confirm on them.
- Multi-model cross-product on the full grid. Only Kimi runs all 90
  cells; NVIDIA only runs the 12-cell confirm. Full cross is a
  Phase 2.5 option if results are close.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  view_experiment.py (driver)                    │
│  variants × seeds × scenes × games → N runs                     │
│                      │                                          │
│                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TerritoryGame / CoverageGame / openclaw_demo loop       │   │
│  │                                                          │   │
│  │  prompt_images = view_builder(variant, engine, game)     │   │
│  │                  ┌──────────────┬─────────────┐          │   │
│  │                  │ "baseline"   │ "map-v2"    │"...+chase"│  │
│  │                  └──────────────┴─────────────┘          │   │
│  │                      │                                   │   │
│  │                      ▼                                   │   │
│  │   provider.get_action(images=prompt_images, state=...)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                      │                                          │
│                      ▼                                          │
│             ReplayRecorder → replay.json + GIF                  │
│             + results.jsonl row tagged with `variant`           │
└─────────────────────────────────────────────────────────────────┘
```

The view-builder is the only new prompt seam. Providers are unchanged:
`get_action(images: list[str], …)` already accepts N images. No new
contract.

## Implementation Plan

### Task T29a: Add `NvidiaProvider` to `roboclaws/core/vlm.py`

**Files:** `roboclaws/core/vlm.py`, `tests/test_nvidia_provider.py`,
`docs/openclaw-local.md` (env-var table addition).

1. New class `NvidiaProvider` that follows `OpenAIProvider`'s shape:
   uses the `openai` SDK with `base_url="https://integrate.api.nvidia.com/v1"`,
   `api_key=os.environ["NVIDIA_API_KEY"]`, and `instructor.from_openai`
   for structured output via the same `_build_agent_action_model()`.
2. Add canonical-alias entries to `_MODEL_ALIASES`:
   - `"nvidia"` → `"meta/llama-4-maverick-17b-128e-instruct"`
     (default pick; a live probe during T35 prep can swap to
     `nvidia/llama-3.1-nemotron-nano-vl-8b-v1` if latency/quality is
     better).
   - Every full model name we want to address, so
     `create_provider("meta/...")` and
     `create_provider("nvidia/...")` both route to `NvidiaProvider`.
3. Add `_COST_PER_M` entries for the chosen models (price lookup from
   NVIDIA's published per-model rates; leave `{0, 0}` fallback if
   unpublished so `cumulative_cost` reports 0 rather than crash).
4. **Live probe** (local-dev step during T35 prep, not a CI gate):
   build `NvidiaProvider(model="meta/llama-4-maverick-17b-128e-instruct")`,
   send one real `get_action(images=[small_b64], state={"hello":"world"})`
   call, assert the returned `action` is in `NAVIGATION_ACTIONS`. This
   is the "new external HTTP surface" live-probe gate — per
   `feedback_live_probe_gate.md`, before merge.
5. Unit tests (mocked SDK):
   - `_COST_PER_M` hit + miss paths don't crash.
   - `get_action` with a 3-image payload serialises to the OpenAI image
     format (2 images baseline, 3 images for variant C).
   - `ProviderStatus.to_dict()` shape parity with other providers.

### Task T30: Structured map renderer (`render_structured_map`)

**Files:** `roboclaws/core/visualizer.py`, `tests/test_visualizer_structured.py`

1. Add `GameVisualizer.render_structured_map(*, agent_positions,
   agent_rotations, reachable_cells, claimed_cells, covered_cells,
   world_bbox) -> PIL.Image`. Pure rendering — no AI2-THOR imports.
2. Rendering contract:
   - Fixed 2 px/cell margin around `world_bbox` for legibility.
   - Unreachable (any cell in bbox not in `reachable_cells`) → `(60,60,60)`.
   - Reachable-unclaimed-uncovered → `(230,230,230)`.
   - Covered (coop coverage) → `(180,230,180)`.
   - Claimed by agent i → SOUL colour (fallback agent palette) at
     `alpha=255` — solid, not tinted — so the boundary is crisp.
   - Agent marker: filled triangle pointing in `rotation['y']` direction,
     height ≈ 1.4 × cell size, outlined black. Agent id label inside.
3. Keep `render_overhead_map` as-is — baseline uses it verbatim.
4. Tests (5+):
   - Unreachable cells render as dark when passed an incomplete
     `reachable_cells` set.
   - Agent triangle points in 4 cardinal directions for
     `y ∈ {0, 90, 180, 270}` — assert dominant non-background pixels
     sit in the expected quadrant of each agent's cell.
   - Three agents at distinct SOULs render in three distinct colours
     (same `assert not np.array_equal` approach as T26).
   - Empty `claimed_cells` and empty `covered_cells` both render cleanly.
   - Output size matches `world_bbox` × `cell_px` within the 2 px margin.

### Task T31: Chase-cam integration in `MultiAgentEngine`

**Files:** `roboclaws/core/engine.py`, `tests/test_engine_chase_cam.py`

1. Add `MultiAgentEngine.add_chase_cam(agent_id: int) -> int` that
   registers a third-party camera and returns its stable index. Pose is
   computed once at registration; the first frame will still look wrong
   until `update_chase_cam` runs.
2. Add `MultiAgentEngine.update_chase_cam(agent_id: int)` that issues
   `UpdateThirdPartyCamera` with pose:
   - position = agent pos + rotation-rotated `(0, 1.5, -1.0)` offset
     (metres; behind + above the agent in agent-local frame).
   - rotation = `(20°, agent_y, 0°)` — pitch down 20°, match agent yaw.
3. Add `MultiAgentEngine.get_chase_cam_frame(agent_id: int) -> np.ndarray`.
4. **Smoke test (local-dev, not CI):** verify per-step pose updates
   actually render (AI2-THOR's third-party camera API may not accept
   `Update` mid-step on all engine versions; fallback is to remove +
   re-add per step, more expensive but always works).
5. Unit test with a mocked controller verifies the position/rotation
   math for 4 cardinal agent headings.

### Task T32: `--views` flag + view-builder dispatch

**Files:** `roboclaws/core/views.py` (new), `examples/openclaw_demo.py`,
`examples/territory_game.py`, `examples/coverage_game.py`,
`tests/test_views.py`

1. New `roboclaws/core/views.py` exports
   `build_prompt_images(variant, *, engine, game, active_agent_id,
   overhead_bg, world_bbox) -> list[np.ndarray]`.
   - `variant="baseline"` → current 2 frames.
   - `variant="map-v2"` → FPV + `render_structured_map(...)` as numpy.
   - `variant="map-v2+chase"` → the map-v2 pair + the chase-cam frame
     for the active agent. Requires `engine.update_chase_cam(active)`
     to have been called this step.
2. Add `--views {baseline,map-v2,map-v2+chase}` CLI flag (default
   `baseline`) to all three examples.
3. Replace `prompt_images = [active_state.frame, map_frame]` in
   `openclaw_demo.py` with the view-builder call. Same wiring in the
   two games.
4. Tests: for each variant, assert `len(build_prompt_images(...))` is
   the expected count (2, 2, 3) and each element is a valid
   `(H, W, 3) uint8` array.

### Task T33: A/B experiment harness

**Files:** `examples/view_experiment.py`, `tests/test_view_experiment.py`

1. CLI: `--variants baseline,map-v2,map-v2+chase --seeds 1,2,3,4,5
   --scenes FloorPlan201,FloorPlan205,FloorPlan210 --games
   territory,coverage --model kimi-coding --agents 3
   --output-dir output/view-experiment --max-usd 15`. `--max-usd` is a
   cumulative wallet cap across all runs in the sweep — if
   `sum(cumulative_cost)` crosses it, the harness aborts cleanly
   (writes what it has, prints remaining runs).
2. For each `(variant, seed, scene, game)` cross-product run:
   - Seed `random.seed(seed)`, `np.random.seed(seed)`.
   - Construct provider with `reset_cost()`.
   - Run the game; capture: scores per agent, total_steps,
     termination_reason, cumulative USD, wallclock seconds, blocking
     events, `provider_status.to_dict()`.
   - Append one JSONL row to `results.jsonl` tagged with all experiment
     coordinates.
   - Save the full replay under
     `output/view-experiment/<variant>/<game>/<scene>-seed<N>/`.
3. A failed run (provider circuit opens, AI2-THOR crashes) logs a row
   with `status=error` and the error kind; the harness continues.
4. Test: smoke with `MockProvider`, 1 variant × 1 seed × 1 scene × 1
   game, assert `results.jsonl` has exactly 1 well-formed row.

### Task T34: Analysis script

**Files:** `scripts/analyze_view_experiment.py`,
`tests/test_analyze_view_experiment.py`

1. Input: `--input output/view-experiment/results.jsonl`.
2. Output: printed table + `output/view-experiment/summary.md` with:
   - Mean + bootstrap 95% CI of the primary metric per `(variant, game)`.
     Primary = `cells_claimed_sum` for territory, `coverage_fraction`
     for coverage, `visited_cells` for navigation.
   - Secondary metrics: mean USD/run, mean wallclock, mean blocking
     events, mean steps-to-termination.
   - Paired Wilcoxon signed-rank test comparing
     `{B vs A, C vs A, C vs B}` per game, paired on `(seed, scene)`.
     Report `p` and effect size.
   - Bold the best variant per game if `p < 0.05`.
3. No plotting dependency — text/markdown output only.
4. Test with synthetic JSONL (dummy runs) asserting the table
   renders and p-value columns appear for each comparison.

### Task T35: Local-dev execution run

**Owner:** local-dev session.
**Guardrail:** cloud session MUST NOT run this task — it depends on
real `KIMI_API_KEY` + `NVIDIA_API_KEY`, real AI2-THOR, and real
wallclock. See `CLAUDE.md § cloud vs local development` + `AGENTS.md §7`.

1. **Pre-flight**: one-call live probe against each provider
   (`NvidiaProvider` is new this phase; `KimiCodingProvider` is already
   live-probed but confirm after any SDK bumps). Per
   `feedback_live_probe_gate.md`: do this before the overnight sweep.
2. **Kimi workhorse sweep**: from a local checkout,
   `python examples/view_experiment.py
   --variants baseline,map-v2,map-v2+chase --seeds 1,2,3,4,5
   --scenes FloorPlan201,FloorPlan205,FloorPlan210
   --games territory,coverage --model kimi-coding --agents 3
   --max-usd 15`. Expected runtime: ~90 games × ~4-6 min/game ≈
   7-9 hours (Kimi Coding's tail latency is ~40-60 s per VLM call —
   slower than GPT-mini). Run overnight. Budget: ~$10-15 on
   `kimi-for-coding` (cost varies with `reasoning_effort=low` reasoning
   token usage; the `--max-usd` gate catches tail cost blowups). The
   existing circuit breaker + per-seed isolation means any one run
   tripping `consecutive_failures_exceeded` logs `status=error` and the
   sweep continues.
3. On completion, run `scripts/analyze_view_experiment.py`, save the
   summary.
4. **NVIDIA confirm set**: pick the top two variants from step 3, run
   3 seeds × 1 scene (FloorPlan201) × 2 games × 2 variants = 12 runs
   on the NVIDIA model chosen in T29a. Budget: variable by model
   (Maverick vs. Nemotron Nano pricing diverges by ~10×); use
   `--max-usd 5` as a guardrail. Confirms the ordering holds across
   model families and on a non-Kimi transport.

### Task T36: Results writeup

**Files:** `docs/view-experiment-2026-04.md`, `README.md` (results tile),
sample GIFs under `docs/img/view-experiment/`.

1. One-line verdict per question (map-v2 helps / doesn't; chase-cam
   helps / doesn't).
2. Full results table copied from `summary.md`.
3. One GIF per variant on the same seed/scene for visual comparison.
4. Decision record: which variant(s) graduate to Phase 2.5 as the
   default, or `declined` with rationale if neither beats baseline.

### Task T37: Phase 2.4 retrospective + TODOS.md update

**Files:** `PLAN.md` (append retrospective), `TODOS.md`.

Shipped / dropped / lessons, same template as Phase 2.2. Promote the
winning variant to a Phase 2.5 "ship as default" item if applicable, or
close with `declined` on both fronts.

## Test Plan

The test diagram maps to the codepaths introduced here:

| New codepath | Test | Location |
|---|---|---|
| `NvidiaProvider` OpenAI-SDK wiring | mocked SDK, assert request shape, cost accounting, image-count support | `tests/test_nvidia_provider.py` |
| `NvidiaProvider` 3-image payload | mocked SDK, assert 3 `image_url` blocks in messages for variant C | `tests/test_nvidia_provider.py` |
| `create_provider("nvidia")` alias | assert returns `NvidiaProvider` instance | `tests/test_nvidia_provider.py` |
| `render_structured_map` arrow direction | pixel-quadrant assertion for 4 cardinal headings | `tests/test_visualizer_structured.py` |
| `render_structured_map` SOUL tint | `assert not np.array_equal` per T26 pattern | `tests/test_visualizer_structured.py` |
| `render_structured_map` unreachable render | dark-pixel assertion in known walled cells | `tests/test_visualizer_structured.py` |
| `add_chase_cam` pose math | mocked controller, verify position + rotation for 4 headings | `tests/test_engine_chase_cam.py` |
| `update_chase_cam` pose per step | mocked controller, assert step-over-step pose change matches agent move | `tests/test_engine_chase_cam.py` |
| `build_prompt_images` variant dispatch | assert image count per variant | `tests/test_views.py` |
| `view_experiment.py` harness smoke | MockProvider, 1x1x1x1, assert JSONL row shape | `tests/test_view_experiment.py` |
| `analyze_view_experiment.py` | synthetic JSONL, assert table + p-values render | `tests/test_analyze_view_experiment.py` |
| Chase-cam `Update` succeeds on live AI2-THOR | **local-dev** smoke, not CI | T31 step 4 |
| `NvidiaProvider` live probe | **local-dev** one-call probe per `feedback_live_probe_gate.md` | T29a step 4 |
| Kimi Coding end-to-end with 3-image prompt (variant C) | **local-dev** 1 seed × 1 scene × 1 game smoke | T35 step 1 |

The CI `lint-and-mock` job must pass across all new tests with
`MockProvider`. Kimi / NVIDIA / Anthropic / OpenAI paths stay mocked
per existing convention.

## Error & Rescue Registry

| Failure | Rescue |
|---|---|
| AI2-THOR rejects `UpdateThirdPartyCamera` mid-step (engine version drift) | T31 step 4: fall back to `delete + AddThirdPartyCamera` per step; local-dev probes this before CI. |
| Kimi Coding rate-limit / circuit-breaker trips mid-sweep | Existing `KimiCodingProvider` circuit opens, per-run `status=error` row, sweep continues. Re-run failed rows by filtering `results.jsonl`. |
| Variant C's 3rd image breaks Kimi `json_schema` path (empty `content`, all answer in `reasoning_content`) | `_extract_action_json` already scans both; if it still fails, T35 step 1 smoke gates before the full overnight sweep. If smoke fails, drop variant C from the Kimi sweep and run it only on NVIDIA. |
| `NvidiaProvider` is a new HTTP surface that passes in cloud but fails live | `feedback_live_probe_gate.md` rule: T29a step 4 live probe is a merge gate; we don't rely on mocked tests alone. |
| Chase-cam pose looks wrong in the GIF (agent not centred) | Log full pose per step during T31 smoke; iterate pose offsets before T35 run. |
| p-values look non-significant but variant C has visible qualitative improvements | Writeup reports both the stat result and the qualitative observation; we don't conflate absence-of-evidence with evidence-of-absence. |

## Failure Modes

- **AI2-THOR non-determinism leaks through seed control.** Even with
  `seed=N`, Unity-side physics has jitter. Mitigation: paired stats (we
  compare variant-B to variant-A on matched `(seed, scene, game)`), not
  absolute means.
- **Chase-cam obscures critical FPV info.** If the model learns to rely
  on the chase-cam and the FPV gets downweighted, variant C wins at
  navigation but loses at object-identification-heavy games. Not
  measurable this phase (games are navigation-dominant) but a flag to
  raise for Phase 3+.
- **Map-v2 is prettier but less informative than the photo.** If the
  structured grid strips out texture cues that helped the model
  disambiguate "chair vs. table", variant B can regress. Writeup
  examines blocking-event rate + qualitative GIF review.
- **Study under-powered at n=5 per (scene, game).** With 5 seeds × 3
  scenes = 15 paired samples per comparison, Wilcoxon can detect medium
  effects (d≈0.7) at α=0.05 with ~80% power. Small true effects would
  require n=30+ seeds. Writeup states the detectable effect size.

## Effort Estimate

| Task | Where | Estimate |
|---|---|---|
| T29a NvidiaProvider + mocked tests | cloud | 1-2 hrs |
| T29a NVIDIA live probe | local | 15 min |
| T30 visualizer + tests | cloud | 2-3 hrs |
| T31 chase-cam math + mocked tests | cloud | 1-2 hrs |
| T31 live chase-cam smoke | local | 30-60 min |
| T32 view-builder + wiring | cloud | 1-2 hrs |
| T33 harness + smoke test (incl. wallet cap) | cloud | 2 hrs |
| T34 analysis script + tests | cloud | 1-2 hrs |
| T35 Kimi sweep (90 games) + NVIDIA confirm (12 games) | local | ~9 hrs wallclock, ~30 min attended |
| T36 writeup + GIFs | local | 1 hr |
| T37 retro + TODOS | cloud or local | 30 min |

**Total engineering**: ~1.5-2 days cloud + ~1 local evening.
**Compute budget**: ~$10-15 (Kimi sweep) + ~$3-5 (NVIDIA confirm) = **~$15-20**,
capped at $20 hard via `--max-usd` wallet gates.

## What already exists (reuse, don't rebuild)

- `MultiAgentEngine.get_reachable_positions` — ground-truth occupancy
  set, already cached after first call.
- `MultiAgentEngine._setup_overhead_camera` pattern — T31's chase-cam
  registration follows the same `AddThirdPartyCamera` shape.
- `GameVisualizer.composite_frame` / `save_gif` / `save_png` — unchanged.
- `ReplayRecorder` — extend to tag each run with `variant`, no shape
  change.
- All VLM provider `get_action(images=..., state=...)` signatures —
  **unchanged**; they already accept variable-length `images: list`.
- `KimiCodingProvider` circuit-breaker + retry machinery — reused
  verbatim for the T35 workhorse sweep. Budget handles Kimi Coding's
  observed 429-burst behaviour without a new implementation.
- `OpenAIProvider` class shape — `NvidiaProvider` is a near-copy with
  `base_url` and `api_key` env-var swap; no new structured-output
  machinery (instructor + `_build_agent_action_model()` carry over).
- `CI lint-and-mock` job — picks up new tests automatically; no
  NVIDIA/Kimi live calls in CI.
- Territory + Coverage game modules — untouched logic; only the
  prompt-image assembly inside their example drivers changes.

## Worktree parallelization strategy

Sequential. T30-T32 all touch `roboclaws/core/`; T33 depends on T32;
T34 depends on T33's JSONL shape. No fan-out wins here. Keep on `main`.
