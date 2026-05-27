# MolmoSpaces HTTP Visual Grounding Service

**Status:** Proposed source plan
**Created:** 2026-05-25
**Source:** Molmo cleanup visual-grounding design discussion and ADR-0133
**Workflow:** Pre-GSD plan. Ingest or pass to `gsd-plan-phase` before
implementation.

## Problem

Molmo cleanup now has two camera-related profiles:

- `camera-raw`: the cleanup agent receives RAW_FPV evidence and declares a
  candidate only when acting on it.
- `camera-labels`: a separate camera producer registers structured candidates
  through `declare_visual_candidates`.

The current `camera-labels` implementation is still a deterministic
simulator-state producer. That is useful as a control lane, but it does not tell
us whether a real detector or multimodal model can replace the sim-only
candidate API using the same RAW_FPV evidence.

We need a pluggable visual-grounding pipeline that can compare bbox proposers
such as Grounding DINO, YOLOE, and fixed/custom YOLO, plus refiners such as
Qwen3-VL and MiMo v2 Omni, without changing the public cleanup MCP contract.

This plan owns the HTTP pipeline and benchmark integration for MolmoSpaces and
live coding-agent cleanup. The more robot-specific
`docs/research/06-visual-grounding-perception-producer.md` is a useful reference for
edge deployment, async route perception, and real Agibot G2 producer rollout.

## Goals

- Keep `world-labels`, `camera-raw`, and `camera-labels` as the user-facing
  input-contract profiles.
- Add a pipeline/provenance axis for `camera-labels`, starting with `sim`,
  fake HTTP, proposer-only, proposer-plus-refiner, and direct-producer routes.
- Route real visual grounding through an External Visual Grounding Service so
  model dependencies and GPUs can live on another machine.
- Build a perception-isolated benchmark harness so proposer/refiner selection
  does not depend only on expensive end-to-end cleanup runs.
- Keep Live Codex support in the first implementation path: Codex calls
  `observe` and `declare_visual_candidates`; Roboclaws calls the external HTTP
  service server-side.
- Preserve the existing normalized candidate shape, including public destination
  hints such as `candidate_fixture_id`, `cleanup_recommended`, and
  `recommended_tool`.
- Separate Visual Grounding Quality from Destination Hint Quality and from
  end-to-end cleanup success.
- Design for Qwen3-VL and MiMo v2 Omni first as refiner adapters. Also allow
  them as direct-producer comparisons, but do not make direct Qwen3-VL execution
  a first-phase requirement.
- Keep the design compatible with a future continuous Perception Producer that
  runs during navigation, emits `discovered_during` provenance, and uses
  short-term tracking for stable handles.

## Non-Goals

- Do not add a new public MCP visual-grounding tool.
- Do not expose image artifact paths, grounding service credentials, or
  provider host details to Codex/Claude/OpenClaw agents.
- Do not add `transformers`, model weights, vLLM, or SGLang dependencies to the
  core cleanup runtime for the first implementation.
- Do not silently fall back to simulator labels when an HTTP producer fails.
- Do not ask the visual model to own final cleanup destination selection. The
  Destination Hint Resolver remains the source of normalized candidate
  destinations.

## Proposed Operator Shape

The public profile stays `camera-labels`. Visual grounding selection is a
pipeline id:

```bash
just task::run molmo-cleanup direct camera-labels visual_grounding=sim
just task::run molmo-cleanup mcp-smoke camera-labels visual_grounding=fake-http
just task::run molmo-cleanup direct camera-labels visual_grounding=grounding-dino
just task::run molmo-cleanup direct camera-labels visual_grounding=yoloe
just task::run molmo-cleanup direct camera-labels visual_grounding=grounding-dino+mimo-v2-omni
just task::run molmo-cleanup direct camera-labels visual_grounding=yoloe+mimo-v2-omni
just task::run molmo-cleanup direct camera-labels visual_grounding=grounding-dino+qwen3-vl
just task::run molmo-cleanup direct camera-labels visual_grounding=mimo-v2-omni-direct
just task::run molmo-cleanup direct camera-labels visual_grounding=qwen3-vl-direct
```

Recommended environment variables:

```text
VISUAL_GROUNDING_BASE_URL=http://127.0.0.1:18880
VISUAL_GROUNDING_API_KEY=...
VISUAL_GROUNDING_TIMEOUT_S=20
VISUAL_GROUNDING_PIPELINE_ID=grounding-dino+mimo-v2-omni
VISUAL_GROUNDING_PROPOSER_ID=grounding-dino
VISUAL_GROUNDING_PROPOSER_MODEL_ID=IDEA-Research/grounding-dino-tiny
VISUAL_GROUNDING_REFINER_ID=mimo-v2-omni
VISUAL_GROUNDING_REFINER_MODEL_ID=mimo-v2-omni
```

`visual_grounding=sim` requires no HTTP service and stays the pipeline-control
baseline. Any non-sim pipeline should fail visibly if the HTTP service is not
configured or returns an error.

`visual_grounding` is a runner/server configuration value, not an MCP tool
argument. Live Codex, Claude, or OpenClaw agents should keep calling
`declare_visual_candidates(observation_id)` after `observe`; the cleanup runtime
decides whether that registration uses the simulator baseline or an injected
HTTP visual-grounding client. Agents should not see the pipeline id unless it is
reported back as provenance/evidence.

The first HTTP transport should use JSON with base64-encoded image bytes. That
keeps the service contract simple, testable, and independent of local artifact
paths. Benchmark harnesses may read local files internally, but the formal
service request should send bytes so remote deployments and isolated Codex
workspaces do not need shared filesystems. Multipart upload or signed artifact
URLs can be added later only if payload size or throughput becomes a measured
problem.

Default service behavior:

- timeout: `VISUAL_GROUNDING_TIMEOUT_S`, default 20 seconds;
- retries: one short retry for connection setup errors only;
- inference timeout: no automatic retry, record pipeline failure evidence;
- authentication: optional `Authorization: Bearer $VISUAL_GROUNDING_API_KEY`;
- reports: never include the key, only auth mode such as `none` or
  `bearer_configured`.

## Sidecar Packaging

The first sidecar service code can live in this repo so schema, client, fake
service, benchmark harness, and producer/refiner adapters evolve together. Keep
heavy model dependencies out of the core cleanup runtime:

- core cleanup runtime: HTTP client, schemas, report/checker metadata only;
- sidecar base extra: lightweight HTTP service dependencies and fake pipeline;
- proposer extras: `visual-grounding-dino`, `visual-grounding-yoloe`, and
  `visual-grounding-omdet`;
- refiner extras: `visual-grounding-qwen3vl` for local/open Qwen3-VL probes;
- hosted refiner routes such as MiMo v2 Omni use provider env/config rather
  than local model weights.

The service should expose one HTTP schema and one configurable service binary.
Deployments may run separate instances per pipeline or machine, but Roboclaws
should only need `VISUAL_GROUNDING_BASE_URL` plus the selected `pipeline_id`.

Model weights must not be implicitly downloaded by normal Roboclaws cleanup,
benchmark, or CI recipes. Provide explicit setup or `pull-model` style commands
for local model probes. Fake HTTP and small benchmark fixtures should be enough
for CI-style contract checks; real Grounding DINO, YOLOE, Qwen3-VL, and hosted
MiMo runs remain local/dev gates.

YOLOE and YOLO-family adapters are optional sidecar probes until licensing and
redistribution boundaries are reviewed. Do not bundle YOLO weights in the repo
or default runtime. Grounding DINO remains the conservative first open-vocabulary
proposer baseline while YOLOE is evaluated for speed/latency tradeoffs.

## HTTP Contract

The first endpoint can stay narrow:

```text
POST /v1/visual-grounding/candidates
```

Request fields:

```json
{
  "schema": "visual_grounding_request_v1",
  "run_id": "seed-7",
  "observation_id": "raw_fpv_001",
  "waypoint_id": "wp_kitchen_01",
  "room_id": "kitchen",
  "capture_context": {
    "discovered_during": "waypoint_observe"
  },
  "image": {
    "mime_type": "image/jpeg",
    "bytes_base64": "...",
    "width": 640,
    "height": 480
  },
  "category_hints": ["food", "dish", "book", "linen", "toy", "electronics", "pillow"],
  "fixture_hints": [
    {"fixture_id": "sink_01", "room_id": "kitchen", "affordances": ["surface", "inside"]}
  ],
  "pipeline_request": {
    "pipeline_id": "grounding-dino+mimo-v2-omni",
    "proposer": {
      "producer_id": "grounding-dino",
      "model_id": "IDEA-Research/grounding-dino-tiny"
    },
    "refiner": {
      "producer_id": "mimo-v2-omni",
      "model_id": "mimo-v2-omni"
    }
  }
}
```

Response fields:

```json
{
  "schema": "visual_grounding_response_v1",
  "status": "ok",
  "pipeline": {
    "pipeline_id": "grounding-dino+mimo-v2-omni",
    "stages": [
      {
        "stage": "proposer",
        "producer_id": "grounding-dino",
        "model_id": "IDEA-Research/grounding-dino-tiny",
        "version": "service-build-or-model-revision",
        "latency_ms": 95
      },
      {
        "stage": "refiner",
        "producer_id": "mimo-v2-omni",
        "model_id": "mimo-v2-omni",
        "version": "provider-model-version",
        "latency_ms": 420
      }
    ]
  },
  "candidates": [
    {
      "category": "dish",
      "image_region": {"type": "bbox", "value": [0.42, 0.51, 0.16, 0.10]},
      "confidence": 0.74,
      "evidence_note": "white bowl-like object on counter",
      "source_fixture_id": "counter_01",
      "destination_hint": {"candidate_fixture_id": "sink_01", "confidence": 0.52},
      "tracking": {
        "track_id": "optional_short_term_track_id",
        "tracker": "optional_bytetrack_or_ocsort"
      }
    }
  ]
}
```

Failure response shape:

```json
{
  "schema": "visual_grounding_response_v1",
  "status": "failed",
  "pipeline": {
    "pipeline_id": "grounding-dino",
    "stages": [
      {
        "stage": "proposer",
        "producer_id": "grounding-dino",
        "model_id": "IDEA-Research/grounding-dino-tiny",
        "status": "timeout",
        "latency_ms": 20000
      }
    ]
  },
  "candidates": [],
  "error": {
    "reason": "timeout",
    "message": "visual grounding proposer timed out"
  }
}
```

Inside `declare_visual_candidates`, a valid HTTP pipeline failure should be
recorded as an observation-level grounding result with zero candidates and
explicit pipeline failure evidence, not as a simulator fallback. The tool call
can still return `ok=true` so the agent can continue the waypoint sweep. Schema
errors, malformed candidate responses, missing raw observations, or bad request
construction remain contract errors and should return `ok=false`.

Empty-candidate producer registration applies only to `camera-labels`. In
`camera-raw`, an empty `declare_visual_candidates(observation_id)` call should
not trigger the simulator baseline or external producer; return a clear no-op or
contract error so raw-FPV runs cannot accidentally receive structured labels.
HTTP pipeline failures should stay observation-level evidence and should not add
synthetic cleanup-worklist objects. The Cleanup Worklist remains object-centric;
pipeline failures belong in tool/report evidence with zero candidates.

`bbox` should be the default first-slice `image_region` because it maps directly
to detector output and report overlays. `point` remains a valid existing
`image_region` shape for pointing-style producers or Molmo-family comparisons.
Bounding boxes should be normalized `[x, y, width, height]` in `[0, 1]` at the
HTTP boundary. Provider adapters may consume or emit pixel boxes internally, but
Roboclaws should store normalized boxes plus source image dimensions so report
overlays and checker logic are stable across resolutions.

The service can expose intermediate stage evidence for benchmark/report use:
raw proposals, refined candidates, rejected proposals, rejection reasons, and
stage latencies. Roboclaws should keep that evidence in artifacts and report
diagnostics without exposing private scorer truth to the agent.

The response may include `destination_hint`, but Roboclaws treats it as
pipeline evidence only. The public Destination Hint Resolver owns the final
`candidate_fixture_id`, `cleanup_recommended`, and `recommended_tool` fields
exposed through the existing candidate shape.

When a refiner changes category, region, confidence, or evidence text, keep the
full pipeline/stage status at the observation level and store the final accepted
producer lineage on each normalized candidate. Raw proposals, rejected
proposals, and refiner rejection reasons are Visual Grounding Diagnostic
Evidence and should stay in report artifacts, not Agent View candidate payloads.

## Implementation Phases

### Phase A: Contract, Fake HTTP Pipeline, And Codex Path

Phase A is a plumbing and contract slice. It should not implement real
Grounding DINO, YOLOE, Qwen3-VL, or MiMo quality comparisons.

- Add request/response schema validation and a small HTTP client inside the
  cleanup runtime.
- Add a `VisualGroundingClient`-style dependency object and inject it into
  `RealWorldCleanupContract` or its construction path. Direct runs, MCP smoke,
  and live MCP server routes should share this client rather than duplicating
  HTTP logic.
- Add a fake HTTP service or test fixture that returns deterministic success and
  failure responses from public request metadata only.
- Put first-slice code near the Molmo cleanup contract, such as
  `roboclaws/molmo_cleanup/visual_grounding.py`, with helper entry points under
  `scripts/visual_grounding/`. Promote to a broader `roboclaws/perception/`
  package only after reuse beyond Molmo cleanup is proven.
- Wire `camera-labels visual_grounding=fake-http` behind
  `declare_visual_candidates` for direct, MCP smoke, and live Codex routes.
- Preserve current explicit manual declarations: when a caller passes
  `candidates=[...]`, register those declarations directly. When
  `candidates` is empty in `camera-labels` mode, treat it as producer
  registration and route to `sim` or the configured HTTP pipeline.
- Do not treat empty candidate lists in `camera-raw` as producer registration;
  make that path an explicit no-op or contract error to preserve the raw-FPV
  input contract.
- Preserve the current `visual_grounding=sim` baseline unchanged except for
  explicit pipeline provenance metadata.
- Record `visual_grounding_pipeline.pipeline_id=sim` and a
  `simulated_camera_model` stage for the simulator baseline so reports and
  benchmark comparison do not need special-case metadata.
- Keep Phase A free of duplicate suppression, tracking, or identity stitching.
  Record duplicate-rate metadata where available, but defer real dedupe/tracker
  behavior to the proposer benchmark or continuous producer phases.
- Update reports/checkers to show pipeline id, stage id, model id, status, latency,
  candidate count, unresolved count, duplicate rate, and failure reason.
- Add contract tests proving HTTP failure is visible and does not fall back to
  sim labels.
- Add focused tests for timeout, connection retry, optional bearer auth
  redaction, and failure-response handling.
- Update the live `camera-labels` kickoff prompt only enough to say that the
  agent should call `declare_visual_candidates` after each raw FPV observation
  and that candidates may come from the configured visual-grounding pipeline.
  Do not mention service URLs, credentials, image paths, or model hosts.
- Add only benchmark skeletons or fake fixtures if useful for validating
  artifact shape. Full proposer ranking and benchmark corpus work belongs to
  Phase B.

Hard gate: unit/contract tests cover a mock client, and at least one direct run
plus one MCP smoke run exercise a real fake HTTP service over the transport.
Local live Codex is a best-effort Phase A confidence check, not a hard gate:
include it if the local provider route is healthy because the integration point
is server-side and should not require agent changes beyond the existing
`declare_visual_candidates` call.

### Phase B: Proposer Adapters And Perception Benchmark

- Implement separately runnable proposer adapters outside the core cleanup
  runtime:
  - Grounding DINO as the conservative open-vocabulary bbox proposer.
  - YOLOE as a promptable/open-vocabulary YOLO-family proposer and likely
    latency/throughput challenger.
  - Fixed/custom YOLO only when a closed cleanup ontology or trained weights
    are available.
- Keep service dependencies in a sidecar environment or optional extra, not in
  the default `uv sync --extra dev` path.
- Add a perception-isolated benchmark corpus from stored RAW_FPV observations,
  public waypoint metadata, public fixture hints, and private evaluation labels.
- Start with simulator-only MolmoSpaces frames so RAW_FPV observations, public
  context, and private labels stay synchronized. Real Agibot G2 head-camera
  frames should be added later as a documented sibling artifact, not as a
  blocker for the first benchmark harness.
- Label category/object presence first. Add bbox or segmentation labels only for
  a small reviewed subset until annotation cost and usefulness are proven.
- Benchmark proposer-only pipelines before running expensive cleanup probes or
  adding refiners.
- Validate direct and MCP smoke reports for the best proposer, then collect at
  least one local Codex `camera-labels visual_grounding=<best-proposer>`
  artifact.

Hard gate: benchmark output ranks Grounding DINO vs YOLOE on the same images
with candidate recall, false-positive rate, duplicate rate, available bbox or
overlay quality, latency, and failure rate. Reports show real stage provenance
and image-region overlays, and the checker distinguishes Visual Grounding
Quality from Destination Hint Quality. Numeric promotion thresholds such as
`recall >= 0.80` are advisory rollout triggers until the corpus is stable enough
for hard pass/fail gates.

When moving from MolmoSpaces fixtures to real robot deployment, add a Stage-0
real-frame measurement pass before choosing a deployed proposer: capture a
fixed Agibot G2 head-camera seed set, run the same proposer candidates on the
same frames, and record per-category recall, bbox stability across adjacent
frames, and edge latency on the intended hardware. Use this evidence before
fine-tuning or locking in a detector.

### Phase C: Refiner Adapters And Pipeline Comparison

- Add MiMo v2 Omni as a refiner under the same HTTP contract. It receives full
  FPV context plus proposer crops/boxes and returns accepted/rejected candidates,
  normalized categories, evidence notes, and optional box/verbal-region
  corrections.
- Add a Qwen3-VL refiner design stub and optional local probe. The optional
  probe may use Transformers, vLLM, or SGLang if local model access and memory
  are available. If not available, record the blocker and keep the adapter
  unimplemented.
- Do not let Qwen3-VL block Phase A or Phase B. Qwen3-VL remains a target
  contract and comparison candidate until access/performance is proven.
- Compare `grounding-dino`, `yoloe`, `grounding-dino+mimo-v2-omni`,
  `yoloe+mimo-v2-omni`, and optional Qwen3-VL refiner variants using identical
  RAW_FPV frames and hints.

Hard gate: the comparison table can answer which pipeline found candidates,
which candidates became actionable handles, which destination hints were useful,
and how much latency/cost each stage added.

Refiner deployment should stay conditional. If proposer-only false-positive
rate is acceptable, keep the first deployed path single-layer and let the
cleanup agent handle remaining semantic judgment. Add a VLM refiner only when
benchmark evidence shows it improves actionability enough to justify latency,
cost, and reliability risk.

### Phase D: Direct VLM Producer And End-To-End Promotion

- Add direct MiMo v2 Omni and optional direct Qwen3-VL producer comparison
  modes, where the VLM proposes candidates without a detector proposer.
- Promote only the best one or two perception pipelines from the benchmark to
  full end-to-end cleanup runs.
- Keep direct VLM modes experimental unless they beat proposer-plus-refiner
  pipelines on recall, precision, latency, and structured-output stability.

Hard gate: an end-to-end comparison includes the sim baseline, the best
proposer-only pipeline, the best proposer-plus-refiner pipeline, and at most one
direct VLM pipeline.

### Phase E: Continuous Perception Producer For Real Robot Routes

This is a later real-robot extension, not a blocker for Phase A-D.

- Run the visual-grounding service continuously beside the cleanup MCP server
  and register candidates without blocking `navigate_to_waypoint`.
- Mark candidate provenance with `discovered_during=waypoint_observe` or
  `discovered_during=navigation` so reports distinguish deliberate waypoint
  observations from route perception.
- Add short-term identity with ByteTrack, OC-SORT, or an equivalent tracker
  before promoting continuous output into stable observed handles.
- Keep the producer stateless across runs; persistent visual memory is a later
  capability.
- For real Agibot G2 targets, measure sustained edge throughput and thermals on
  the intended hardware before calling the route producer production-ready.

Hard gate: route perception improves either time-to-first-actionable-handle or
successful cleanup count over a `camera-raw`-only baseline without adding
agent-facing tools or leaking private labels.

## Benchmark Harness

Add a non-E2E harness before the full cleanup probe matrix:

```bash
just agent::harness molmo-visual-grounding-benchmark pipeline=grounding-dino
just agent::harness molmo-visual-grounding-benchmark pipeline=yoloe
just agent::harness molmo-visual-grounding-benchmark pipeline=grounding-dino+mimo-v2-omni
```

Expected artifact shape:

```text
visual_grounding_benchmark_result.json
visual_grounding_benchmark_report.html
visual_grounding_predictions.jsonl
overlays/<observation_id>/<pipeline_id>.jpg
```

Benchmark corpus requirements:

- fixed RAW_FPV frames from MolmoSpaces cleanup observations;
- public waypoint id, room id, camera dimensions, category hints, and fixture
  hints;
- private category/object-presence labels for scoring only, never returned to
  the producer or agent;
- bbox or segmentation labels for only a small reviewed subset in the first
  corpus, with broader region annotation added after overlay review proves it
  worth the cost;
- enough hard negatives and cluttered scenes to measure false positives;
- stable seeds so new producers can be replayed without rerunning the simulator.
- store the canonical benchmark working set under `harness/visual_grounding/`;
- allow small, stable smoke fixtures in that directory to become git-tracked
  once size and privacy boundaries are acceptable;
- keep larger image corpora and generated comparison outputs as local or
  published artifacts, not normal source files.
- allow a later real-camera seed set, for example Agibot G2 head-color frames,
  to live as a documented sibling artifact when too large for git.

Benchmark result requirements:

- per-pipeline summary and per-stage summary;
- proposal recall and precision against private labels;
- category-family accuracy;
- bbox quality where private boxes/segments are available, plus required overlay
  review when exact IoU is unavailable;
- duplicate rate and near-duplicate grouping;
- short-term identity stability across adjacent frames when frame sequences are
  available;
- identity collision rate for tracker-backed continuous producers;
- cleanup relevance reject/accept quality for refiners;
- rejected proposal records for refiner diagnostics, kept in benchmark artifacts
  rather than agent-facing candidate outputs;
- structured-output parse failure rate;
- latency, timeout rate, memory profile where available, and API cost where
  applicable;
- recommendation for which pipelines deserve end-to-end cleanup probes.

Report and artifact requirements:

- intermediate proposals, rejected proposals, rejection reasons, crops, and
  overlays are Visual Grounding Diagnostic Evidence;
- diagnostic evidence may appear in benchmark reports and normal cleanup report
  diagnostics, but not in MCP responses or Agent View candidate lists;
- normal cleanup reports should show accepted candidates, pipeline summary,
  failure evidence, and relative links to overlays rather than dumping every
  private benchmark label;
- benchmark reports may show private scoring summaries by default, but
  per-item private label details require an explicit option such as
  `--include-private-label-details`;
- normal cleanup run overlays should live under
  `<run_dir>/visual_grounding/overlays/`;
- benchmark overlays should live under benchmark output, for example
  `harness/visual_grounding/...` generated output or `output/.../overlays/`.

Checker requirements:

- require pipeline id, stage metadata, status, latency, and candidate counts for
  non-sim visual-grounding runs;
- require `visual_grounding_pipeline.pipeline_id=sim` and
  `stage=simulated_camera_model` for the simulator baseline;
- prove non-sim pipeline failures do not fabricate simulator fallback labels;
- prove API keys, bearer tokens, and raw credentials are absent from artifacts,
  trace, and reports;
- prove accepted candidates keep the existing normalized Model-Declared
  Observation candidate shape;
- prove private benchmark labels are absent from Agent View and MCP trace;
- require visible failure evidence when the service returns a valid failure
  response or times out.
- require `discovered_during` provenance for any async or continuous route
  perception candidate.

The first benchmark corpus should be generated from fixed MolmoSpaces sim runs
so RAW_FPV observations, public context, and private labels stay synchronized.
Manual annotations and harder real-camera frames can be added later, but they
should not block the first harness.

The first Phase B comparison should stay proposer-only: `grounding-dino` versus
`yoloe` on identical frames and hints. Add MiMo v2 Omni, Qwen3-VL, or direct VLM
routes only after the proposer table shows a measured false-positive,
normalization, or actionability problem that a refiner is expected to solve.

Useful rollout/change triggers from the real-robot reference plan:

- proposer per-category recall below 0.80 on the seed set means try the next
  proposer before fine-tuning;
- refiner end-to-end latency above 1.5 seconds means keep the proposer-only
  path and let the cleanup agent absorb semantic judgment;
- sustained edge thermals or power beyond the target budget means lower
  proposer FPS and make the refiner on-demand-only;
- identity collisions above 1 per minute mean tune tracking before replacing
  the tracker.

## Comparison Matrix

| Lane | Profile | Pipeline | Primary Question |
| --- | --- | --- | --- |
| World labels | `world-labels` | simulator/world state | How strong is the current structured cleanup baseline? |
| Raw FPV | `camera-raw` | main cleanup agent | Can the live agent act from raw camera evidence without pre-labels? |
| Sim camera labels | `camera-labels` | `sim` | Does the camera-label pipeline work when perception is controlled? |
| Detector camera labels | `camera-labels` | `grounding-dino` | Can a conservative open-vocabulary bbox proposer replace sim labels? |
| YOLO-family camera labels | `camera-labels` | `yoloe` or fixed/custom YOLO | Can a YOLO-family proposer beat DINO on speed while preserving enough recall? |
| Detector + hosted refiner | `camera-labels` | `grounding-dino+mimo-v2-omni` or `yoloe+mimo-v2-omni` | Does a VLM refiner reduce false positives and normalize categories enough to justify latency/cost? |
| Detector + local/open refiner | `camera-labels` | `grounding-dino+qwen3-vl` or `yoloe+qwen3-vl` | Can a local/open VLM refiner match the hosted refiner if access is viable? |
| Direct VLM camera labels | `camera-labels` | `mimo-v2-omni-direct` or `qwen3-vl-direct` | Can a VLM replace the proposer entirely, and is that stable enough? |

## Metrics

Perception-isolated metrics:

- candidate count by waypoint;
- proposal recall and precision on the Visual Grounding Benchmark Corpus;
- resolved / ambiguous / unresolved grounding status;
- duplicate candidate rate;
- category agreement against hidden evaluation labels, reported only in private
  evaluation sections;
- image-region quality, including bbox overlay review and optional IoU-like
  private diagnostic where available;
- service latency and failure rate;
- structured-output parse failure rate;
- model/provider cost when applicable.

Destination metrics:

- `candidate_fixture_id` presence and confidence;
- placement tool recommendation correctness against public fixture affordances;
- target plausibility, separate from private exact target truth.

End-to-end metrics:

- cleanup success;
- successful cleanup chain count;
- waypoint coverage;
- disturbance/restoration score;
- total elapsed time and pipeline/stage time contribution.

## Acceptance Criteria

- `camera-labels visual_grounding=sim` still produces the current baseline
  candidate shape.
- Non-sim `visual_grounding` values call the HTTP service server-side and record
  pipeline stage provenance.
- Live Codex does not need service URLs, credentials, image paths, or direct
  model access.
- Failed HTTP calls produce visible pipeline-failure evidence and do not
  fabricate sim labels.
- Reports show enough pipeline metadata to compare Grounding DINO, YOLOE,
  fixed/custom YOLO where available, MiMo v2 Omni, and optional Qwen3-VL on the
  same run shape.
- The perception-isolated benchmark harness can rank proposer-only,
  proposer-plus-refiner, and direct-producer pipelines without a full cleanup
  run.
- End-to-end cleanup probes are reserved for the benchmark winners plus control
  lanes.
- The first end-to-end promotion set is capped to `sim`, the best proposer-only
  pipeline, the best proposer-plus-refiner pipeline, and at most one direct VLM
  pipeline until the benchmark corpus is stable enough for hard thresholds.
- Core cleanup dependencies remain unchanged until a sidecar producer is
  explicitly installed.

## Current Qwen3-VL Feasibility Note

As of the current Hugging Face docs, Qwen3-VL has documented Transformers usage
through `Qwen3VLForConditionalGeneration` plus `AutoProcessor`, and the model
card for `Qwen/Qwen3-VL-8B-Instruct` also shows `pipeline("image-text-to-text")`
and direct `AutoModelForImageTextToText` examples. That is enough to design a
Qwen3-VL refiner adapter and optional direct-producer adapter now.

It is not enough to make Qwen3-VL a first implementation dependency. We still
need local access, memory/performance evidence, structured JSON reliability,
and image-region quality before promoting it beyond an optional sidecar probe.
Its first useful role is a refiner for Grounding DINO or YOLOE proposals; direct
producer mode is a later comparison.

## Source References

- ADR-0133:
  `docs/adr/0133-use-http-visual-grounding-service-for-real-camera-labels.md`
- Current settings:
  `docs/human/molmospaces-settings.md`
- Current camera profile architecture:
  `docs/human/molmospaces-cleanup-mode-architecture.md`
- Hugging Face Qwen3-VL docs:
  <https://huggingface.co/docs/transformers/main/en/model_doc/qwen3_vl>
- Hugging Face Qwen3-VL 8B model card:
  <https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct>
- Hugging Face Grounding DINO docs:
  <https://huggingface.co/docs/transformers/main/en/model_doc/grounding-dino>
- Grounding DINO official implementation:
  <https://github.com/IDEA-Research/GroundingDINO>
- Ultralytics YOLOE docs:
  <https://docs.ultralytics.com/models/yoloe/>
- Ultralytics YOLO model docs:
  <https://docs.ultralytics.com/models/>
