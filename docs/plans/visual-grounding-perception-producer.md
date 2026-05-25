# Visual Grounding Perception Producer

**Status:** Proposed reference plan; not yet ingested into `.planning/`
**Created:** 2026-05-25
**Source:** ADR-0126 model-declared observations, `docs/plans/agibot-g2-cleanup-support-pilot.md`,
`TODOS.md` "Async route perception during cleanup navigation", and a
research round on open-vocabulary detectors and grounding-capable VLMs for
edge deployment (RTX 3090, Jetson Thor).
**Workflow:** Pre-GSD reference plan. Captures the design decision space for a
dedicated perception service; concrete implementation should land its own
GSD phase or split into bounded `docs/plans/` slices.

> 中文备注：这份 plan 是 reference,不是立即 execute 的 GSD phase。 当某条 cleanup pilot
> 真的需要落地 grounding service 时,从这里拿决策路径和模型短名单。

## Problem

The current `realworld_cleanup_v1` contract supports two camera profiles:
`camera-labels`, where structured candidates come from a producer-side
inference model, and `camera-raw`, where the cleanup agent inspects raw FPV
image evidence and declares visual candidates through
`navigate_to_visual_candidate`. ADR-0126 ("Bridge Camera Evidence To Cleanup
Handles With Model-Declared Observations") makes this producer-agnostic: the
producer may be the cleanup agent itself, a separate camera inference model,
a detector, or a robot perception service, all using the same declaration
schema.

Today, only one producer is implemented end-to-end: the cleanup agent (Claude
Code or Codex, both multimodal) reasoning directly over raw FPV images. In
the simulator this is honest enough because resolution falls back to a
private scene graph. On a real robot — first target is Agibot G2 — two
concrete gaps appear:

1. **Latency.** Having the main coding agent inspect every FPV frame to find
   cleanup candidates is expensive in time and tokens. Active perception
   while the robot is moving between waypoints (`TODOS.md` "Async route
   perception during cleanup navigation") cannot be served by a single
   per-step main-agent call.

2. **No producer for `camera-labels` on real hardware.** The
   `camera-labels` profile has no concrete real-robot producer yet. Without
   one, the simulator's `camera-labels` cheat (private scene graph
   resolution) has no real-robot equivalent, and `camera-raw` becomes the
   only viable real-robot mode by default.

The missing piece is a **Perception Producer**: a small, dedicated service
that consumes the robot's camera stream at a higher frequency than the main
agent loop, emits Model-Declared Observations in the ADR-0126 schema, and
runs entirely on the robot's edge compute.

> 中文备注: 不是模型选型,是边界问题。 把 grounding 抽成独立 Producer 之后,模型可
> 替换、可双层、可异步,而 cleanup agent 面前的 MCP contract 不动一行。

## Goal

Define a Perception Producer that:

- Implements the ADR-0126 producer contract end-to-end on real hardware
  (initial target: Agibot G2 with head color camera).
- Runs on edge GPU (RTX 3090 desktop or Jetson AGX Thor) at a sustained
  **5–10 FPS** detection rate, with optional **1–2 FPS** semantic
  verification for higher-quality declarations.
- Emits observations in the existing `image_region` shapes
  (`type: bbox` or `type: point`) so the agent-facing MCP contract and
  cleanup loop do not change.
- Supports async route perception: declarations produced while the robot is
  navigating between waypoints must not block the navigation primitive and
  must be distinguishable in reports from deliberate observe-at-waypoint
  declarations.
- Keeps the cleanup agent free to fall back to its own raw-FPV reasoning if
  the producer fails, is disabled, or returns low confidence.

## Non-Goals

- Replacing the cleanup agent. The Perception Producer only proposes
  candidates; semantic decisions like "this pillow on the floor counts as
  misplaced" remain with the cleanup agent.
- Solving grasp affordance, segmentation masks for picking, or scene
  graph construction. Mask output is a future extension; the first slice
  only owns "where in the image is each candidate".
- A new agent-facing MCP tool surface. The producer plugs in behind the
  existing `realworld_mcp_server` and feeds the same observed-handle table.
- Fine-tuning the grounding model on Agibot-specific data in the first
  slice. Use off-the-shelf zero-shot performance first; measure before
  fine-tuning.
- Cross-robot generalization. First slice targets Agibot G2 head color
  camera; extending to other backends comes after the Producer contract is
  proven.

## Decisions Locked

- The Perception Producer is a **separate process** from
  `realworld_mcp_server` and from the cleanup agent. It communicates with
  the server through the existing model-declared observation registration
  path; the server owns the public observed-handle table.
- The first slice targets the **`camera-labels` profile** on real hardware.
  `camera-raw` remains the documented fallback for agents that want full
  raw-image reasoning without a producer.
- Declarations use the existing `image_region` schema. **`bbox` is the
  default** for first-slice detectors; `point` is acceptable for
  pointing-style producers (Molmo family) and requires no schema change.
- The producer runs **on-robot at the edge**. Hosted APIs (Gemini, GDINO
  1.5 Pro, Molmo Playground) are allowed only as offline reference for
  ground-truth labeling and weekly accuracy comparison, never as the
  deployment path.
- The producer is **stateless across runs** but maintains short-term
  identity across frames using a lightweight tracker (ByteTrack or
  OC-SORT). Persistent cross-session memory is out of scope.
- Reports must label each declaration's `producer_type` and `producer_id`
  (ADR-0126 fields) so post-run review can attribute false positives and
  false negatives to the right producer version.

> 中文备注: bbox 优先是为了零 schema 改动 + 跟 ByteTrack 直接对接;point 路径留给未
> 来想用 Molmo 系列时不需要再改一遍。

## Architecture

The Producer is structured in two optional layers. A single-layer deployment
is allowed and recommended for the first slice; the second layer is added
when semantic verification quality becomes the bottleneck.

```
  Robot head color camera (10–30 Hz)
       |
       v
  +----------------------------------------------+
  | Layer 1: Fast open-vocabulary grounder       |   bbox + score
  | Target: 5–10 FPS sustained on Jetson Thor    |   -> image_region(type=bbox)
  +----------------------------------------------+
       |
       v
  +----------------------------------------------+
  | ByteTrack / OC-SORT short-term identity      |   stable handle_id across frames
  +----------------------------------------------+
       |
       | Trigger conditions:
       |   (a) new handle appears
       |   (b) layer-1 confidence below threshold
       |   (c) cleanup agent explicitly queries a candidate
       v
  +----------------------------------------------+
  | Layer 2 (optional): semantic verifier VLM    |   point/bbox + evidence_note
  | Target: 1–2 FPS, semantic + spatial reasoning|   -> producer fills source_fixture_id,
  +----------------------------------------------+      evidence_note, confidence
       |
       v
  ADR-0126 ModelDeclaredObservation
  registered through realworld_mcp_server
       |
       v
  Cleanup agent (Claude Code / Codex), unchanged MCP surface
```

**Why two layers, not one:** a fast bbox-only grounder cannot decide
whether a candidate is misplaced (a book on a desk is fine, a book on the
floor needs cleanup). A 1–2 FPS VLM verifier fills the
`evidence_note` field with that semantic judgment, which is exactly the
ADR-0126 field intended for it. **Single-layer first slice is fine:** ship
Layer 1, let the cleanup agent itself absorb the semantic judgment from the
raw frame, and add Layer 2 only if observed false-positive rate justifies
the cost.

> 中文备注: 第一版别上 Layer 2。 先把 Producer 这个角色跑通,Layer 2 是 quality 不够
> 时才加的余量。

### Async route perception

The Producer runs as an independent process consuming the camera stream
continuously. The cleanup agent's `navigate_to_waypoint` primitive does not
block on the Producer. New handles produced mid-navigation are appended to
the observed-handle table and surface in the next `observe` response with
an explicit provenance field (e.g. `discovered_during=navigation` vs
`discovered_during=waypoint_observe`). Reports distinguish the two so
post-run review can tell deliberate observations from route observations.

This directly implements the `TODOS.md` entry "Async route perception
during cleanup navigation". When this plan is accepted, that TODO should
point here.

## Model Candidates (first-slice short list)

Detailed comparison and benchmark data live separately (see Sources). The
short list for first-slice deployment is intentionally small:

**Layer 1 (fast open-vocabulary grounder, bbox output):**

- **Grounding DINO 1.5 Edge** (Apache 2.0). IDEA Research reports >10 FPS
  on Jetson Orin NX at 640×640, 36.2 AP on LVIS-mini. Mature TensorRT path.
  *Safe default first pick.*
- **YOLOE-v8-S / YOLOE26-L** (AGPL-3.0). Ultralytics one-click TRT
  export, ~160 FPS on T4. Faster than GDINO Edge at comparable LVIS
  accuracy. *Choose if Layer 1 needs higher throughput headroom.*
- **MM-Grounding-DINO Tiny** (Apache 2.0). LVIS-mini 41.4 AP, MMDetection
  fine-tune chain. *Fallback if zero-shot quality is the constraint and we
  decide to fine-tune.*

**Layer 2 (semantic verifier VLM, when needed):**

- **Qwen2.5-VL-7B** with FP4 + Eagle speculative decoding on Jetson Thor.
  NVIDIA Jetson Thor blog reports 252 output tok/s, 3.5× faster than AGX
  Orin W4A16. Outputs normalized bbox coordinates and points; structured
  output requires JSON schema enforcement (vLLM grammar mode).
- **Molmo-7B-D** (Apache 2.0). Native pointing output aligns with
  `image_region(type=point)`. Aligns naturally with the MolmoSpaces
  simulator and the MolmoAct lineage.
- **Molmo 2-4B / 8B** (Apache 2.0, released 2025-12-16). Video-native
  pointing + multi-object tracking with persistent IDs. Lets us drop
  ByteTrack later if the model proves stable.

Hosted-API references (offline only, never deployed on robot):
Grounding DINO 1.5 Pro, Gemini 3 Flash Agentic Vision, Molmo Playground.

> 中文备注: 选 GDINO 1.5 Edge 作为第一版唯一 producer 是最快上线的路径。 其他都是当某
> 个具体指标不达标时才换上。

## Staged Rollout

**Stage 0 — Baseline measurement (1–2 days, no contract changes):**

- Capture ~200 real FPV frames from an Agibot G2 dry-run session covering
  the cleanup category set (`food`, `dish`, `book`, `linen`, `toy`,
  `electronics`, `pillow`, plus current run's specifics).
- Run Grounding DINO 1.5 Edge and YOLOE-v8-S on the 3090 desktop against
  the same frames. Record: per-category recall, bbox stability across
  adjacent frames, TRT FP16 latency.
- Use Qwen2.5-VL-7B (vLLM, INT4) offline to generate ground-truth labels
  on the same 200 frames. This produces a seed evaluation set the project
  can reuse for every future producer change.

**Stage 1 — Layer 1 producer wired through ADR-0126 (single bounded
slice):**

- Implement a `PerceptionProducer` process that subscribes to the Agibot
  head color stream and registers Model-Declared Observations through the
  existing producer path.
- Detector choice driven by Stage 0 data: pick whichever of GDINO 1.5
  Edge or YOLOE has higher recall on the seed set (or pick GDINO if
  recall is within 5% — Apache 2.0 is the boring default).
- Wire ByteTrack for short-term handle ID stability.
- Producer runs on the same edge box as the cleanup agent (3090 in dev,
  Jetson Thor on target hardware).
- Report instrumentation: every declaration carries `producer_type`,
  `producer_id`, `producer_version`, and `discovered_during`.

**Stage 2 — Layer 2 semantic verifier (only if Stage 1 false-positive
rate is high enough to justify the cost):**

- Wire Qwen2.5-VL-7B (vLLM, INT4 or FP4 on Thor) as a verifier triggered
  on Layer 1's new-handle and low-confidence events.
- Producer fills `evidence_note` and `source_fixture_id` from the VLM
  output.
- Async, 1–2 FPS target; never blocks Layer 1 throughput.

**Stage 3 — Video-native producer (exploratory):**

- Evaluate Molmo 2 (4B or 8B) on the seed set. If video pointing and
  built-in tracking match or exceed the Stage 1+2 pipeline, replace both
  Layer 1's detector and ByteTrack with a single Molmo 2 process.

### Rollback / change triggers

- Layer 1 per-category recall on the seed set drops below 0.80 → switch
  detector (try the next short-list candidate before fine-tuning).
- Layer 2 end-to-end latency exceeds 1.5 s including vLLM queueing → keep
  Layer 1 only, let the cleanup agent absorb semantic judgment.
- Jetson Thor sustained temperature > 80 °C or power draw > 100 W under
  load → drop Layer 1 to 5 FPS and convert Layer 2 to on-demand-only.
- Producer raises identity collisions (same physical object surfaces as
  two different handles in one run) above 1 per minute → tune ByteTrack
  thresholds before considering tracker replacement.

## Acceptance Criteria

A Stage 1 implementation is acceptance-ready when:

- The Producer process runs continuously alongside `realworld_mcp_server`
  and the cleanup agent on a single edge box without crashing for ≥30
  minutes of real Agibot G2 navigation.
- Every declared observation passes through the ADR-0126 model-declared
  observation registration path and carries `producer_type`,
  `producer_id`, `producer_version`, and `discovered_during` fields.
- `image_region` is emitted in one of the existing accepted shapes
  (`bbox` or `point`); the agent-facing MCP contract is unchanged.
- The producer achieves ≥5 FPS sustained throughput on the target edge
  device (3090 in dev, Thor at deployment) during a real navigation
  episode.
- Reports distinguish route observations from waypoint observations.
- A cleanup run on a small fixed seed produces a recognizable improvement
  over the `camera-raw`-only baseline on either (a) successful cleanup
  count, or (b) time-to-first-actionable-handle. Either alone is enough;
  this is not a benchmark contest.
- The Stage 0 200-frame seed set lives in the repo (or a clearly
  documented sibling artifact) so any future producer change can be
  re-evaluated against the same baseline.

## Risks and Open Questions

- **No public benchmark for any candidate on Jetson Thor.** Thor launched
  in 2025 and NVIDIA's own benchmarks cover Qwen2.5-VL and π0.5, not
  Grounding DINO / YOLOE / Molmo. Stage 0 must produce our own numbers
  before any selection is final.
- **Multi-instance grounding.** Qwen2.5-VL is known to sometimes return a
  single bbox when multiple instances exist (upstream issue tracked). This
  is one of the reasons Layer 1 is a real detector and Layer 2 is a
  verifier, not the other way around.
- **Identity stability under aggressive camera motion.** ByteTrack works
  well at 30 Hz; at 5 FPS effective output rate, identity may drift. The
  rollback rule above is the first guardrail; Molmo 2's built-in tracking
  is the Stage 3 escape hatch.
- **Where in the repo does the Producer live?** First implementation
  should land under `roboclaws/perception/` (new package) with an entry
  point under `scripts/perception/`. ADR could formalize this after Stage 1
  ships if the boundary holds.
- **Should the Producer share a process with the MCP server?** First slice
  keeps them separate to make failure modes obvious. If process count
  becomes a hardware constraint on Thor, revisit.

## Workflow

This is a reference plan. To implement:

1. Open a GitHub issue (or a `docs/plans/` slice file) for Stage 0 —
   measurement only, no contract change. Land its evidence as a
   retrospective.
2. After Stage 0 evidence exists, open the Stage 1 phase under GSD
   (`/gsd-plan-phase`) referencing this plan as the source. Stage 1 is
   one self-contained slice: producer process + ADR-0126 wiring + report
   fields + one passing real-robot dry run.
3. Update `TODOS.md` "Async route perception during cleanup navigation"
   to point here once this file lands.
4. If Stage 2 or Stage 3 is needed, each is its own GSD phase. Do not
   merge them.

## Sources

- ADR-0126: `docs/adr/0126-bridge-camera-evidence-to-cleanup-handles-with-model-declared-observations.md`
- Retrospective: `docs/retrospectives/plans/molmospaces-model-declared-observations-raw-fpv-cleanup.md`
- Agibot pilot: `docs/plans/agibot-g2-cleanup-support-pilot.md`
- Nav2 cleanup pilot: `docs/plans/real-robot-nav2-cleanup-pilot.md`
- TODOS entry being implemented: `TODOS.md` "Async route perception
  during cleanup navigation"
- External research backing the model short list:
  - Grounding DINO 1.5 Edge — arXiv 2405.10300v2 (IDEA Research)
  - YOLOE — ICCV 2025 paper, Ultralytics docs
  - MM-Grounding-DINO — arXiv 2401.02361
  - Dynamic-DINO — arXiv 2507.17436
  - Qwen2.5-VL / Qwen3-VL — QwenLM/Qwen3-VL repo, vllm-project issue #24728
  - Molmo / Molmo 2 — Ai2 blog `allenai.org/blog/molmo2`,
    `allenai.org/blog/molmoact2`
  - Edge benchmarks — NVIDIA Jetson Thor developer blog, NanoOWL +
    EfficientViT pipeline (Park et al. 2025, PMC12583037), L4 edge
    deployment (arXiv 2601.14921)
  - OK-Robot OVMM baseline — arXiv 2401.12202
