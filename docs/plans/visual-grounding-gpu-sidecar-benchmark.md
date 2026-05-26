# Visual Grounding GPU Sidecar Benchmark

**Status:** Proposed source plan
**Created:** 2026-05-26
**Source:** Visual grounding performance/debug discussion: current Grounding DINO
HTTP sidecar is fast at transport level, but the real adapter is running CPU
Torch even on a CUDA-capable workstation.
**Workflow:** Pre-GSD plan. Use this as the source for a later bounded
implementation phase.

## Problem

Roboclaws now has a provider-neutral HTTP visual-grounding sidecar, which is the
right boundary for running heavier perception models outside the core cleanup
runtime. The current real `grounding-dino` path is still too slow: benchmark
artifacts show about five seconds per request.

The measured breakdown rules out HTTP/base64 transport as the main bottleneck.
On the 28-observation RAW_FPV benchmark, `grounding-dino` averaged about
`5016.8ms` request latency and `5008.0ms` adapter-stage latency, leaving only
about `8.8ms` transport/service overhead. The current repo environment also
pins `visual-grounding-dino` to `torch==2.7.1+cpu`, while the local workstation
has an NVIDIA RTX 3500 Ada Laptop GPU. This is an implementation/runtime bug,
not a reason to abandon the HTTP boundary.

The next step is to make the visual-grounding service a dedicated GPU sidecar,
probe a practical shortlist of faster grounding candidates, and choose the
default from perception-isolated benchmark evidence before running end-to-end
cleanup checks.

## Goals

- Keep the existing HTTP visual-grounding service boundary and cleanup MCP
  contract unchanged.
- Run real visual-grounding models in a dedicated uv-managed GPU sidecar
  environment, separate from the core cleanup `.venv/`.
- Fix the current Grounding DINO GPU placement issue and re-benchmark it as the
  current baseline.
- Compare a practical model shortlist through the existing probe benchmark,
  testing multiple model sizes/configurations per relevant model family.
- Select the recommended pipeline primarily from perception F1/quality and
  latency.
- Validate the winning pipelines through Codex/runtime end-to-end cleanup
  reports against `sim` and `RAW_FPV` apple-to-apple baselines.

## Non-Goals

- Do not change the public MCP cleanup tools or add a new agent-facing visual
  grounding tool.
- Do not make CUDA model dependencies part of the core Roboclaws runtime.
- Do not promote hosted VLM-direct routes as the first real-time producer path.
- Do not make end-to-end cleanup score the primary model-ranking metric for
  this phase; E2E cleanup is a validation gate after perception ranking.
- Do not include broad research candidates in the first implementation wave.
  Florence-2, OWLv2, GLIP/GLIPv2, and hosted VLM-direct routes remain second-wave
  candidates if the practical shortlist is insufficient.
- Do not reject a model family after testing only one small/default
  configuration. The first phase must look for a model that is large enough to
  be useful, quick enough to run as a sidecar producer, and good enough on the
  cleanup RAW_FPV corpus.

## Sidecar Environment

Create a dedicated uv-managed environment for visual grounding, for example:

```text
.venv-visual-grounding/
```

This is a deliberate exception to the normal single `.venv/` project runtime.
The exception is justified because ADR-0133 already moved real grounding models
behind an HTTP service boundary so GPU/CUDA/model dependencies can be isolated
from the core cleanup runtime.

The sidecar environment should:

- install CUDA-capable Torch matching the workstation or target edge box;
- install model-specific dependencies for the selected adapter probes;
- run the existing HTTP sidecar entry point;
- preserve the JSON-over-HTTP contract used by
  `HttpVisualGroundingClient`;
- avoid leaking model paths, credentials, or GPU details to the Codex agent.

The core cleanup `.venv/` continues to run the MCP server, cleanup loop, reports,
and Codex runtime integration. It should not need CUDA Torch or real model
weights.

## Implementation Shape

Keep the endpoint shape unchanged:

```text
POST /v1/visual-grounding/candidates
```

Use the existing service process in real-router mode so one GPU sidecar can
satisfy multiple requested pipelines:

```bash
.venv-visual-grounding/bin/python \
  scripts/visual_grounding/serve_visual_grounding_service.py \
  --pipeline real-router \
  --adapter-mode real
```

Fix the current DINO runtime bug:

- add explicit device selection, defaulting to CUDA when available;
- support an override such as `VISUAL_GROUNDING_DEVICE=cpu|cuda|cuda:0|auto`;
- move the Grounding DINO model and request tensors to the selected device;
- optionally support dtype selection, such as `VISUAL_GROUNDING_TORCH_DTYPE`;
- record device, dtype, torch version, CUDA availability, and model id in
  sidecar stage diagnostics.

Preserve current failure behavior:

- missing GPU dependencies produce visible `adapter_unavailable` or
  `missing_dependency` evidence;
- sidecar HTTP failures produce zero fabricated candidates;
- `visual_grounding=sim` remains the deterministic control baseline and is not
  silently used as fallback for failed real pipelines.

## Candidate Families And Size Sweep

First-wave candidates should stay practical and implementation-bounded, but each
family must be tested across enough sizes/configurations to avoid dismissing it
based on a weak default.

| Family / Pipeline | Required first-wave sweep | Why Include |
| --- | --- | --- |
| `grounding-dino` | HF tiny and base checkpoints at minimum; include any locally available larger/edge/optimized DINO-family checkpoint if it can run in the GPU sidecar. | Repairs the current baseline and tests whether a larger DINO is good enough without being too slow. |
| `yoloe` | At least the current 11s config plus one larger available YOLOE weight; run default and tuned cleanup-prompt settings. | Existing fast open-vocabulary lane; size sweep checks whether recall improves enough before latency becomes unacceptable. |
| `yolo-world` | Small and medium/large available weights, with the same cleanup prompt expansion as YOLOE. | Fast YOLO-family open-vocabulary candidate with a better real-time profile than DINO. |
| `omdet-turbo` | Tiny/base or equivalent available variants. | Fast non-YOLO open-vocabulary candidate for quality/latency balance. |
| `yolo-custom` | One fast fixed-ontology model and one larger fixed-ontology model if weights/data are available. | Deployment upper bound when cleanup categories are stable. |

Do not include broad second-wave research candidates in the first phase unless
all practical candidates fail to beat current CPU DINO.

For every family, record unavailable sizes explicitly instead of silently
shrinking the sweep. If only one size can be tested, the report must mark that
family as under-sampled and must not use that single result to make a broad
"not suitable" claim.

## Benchmark Plan

Use the existing perception-isolated benchmark as the model-selection gate.
Run every candidate on the same RAW_FPV corpus, category hints, fixture hints,
and private scoring labels.

The benchmark should be a family-level sweep, not a one-row-per-family smoke
test. Each row must include:

- pipeline id;
- model family;
- model id / weight name;
- size tier, such as tiny, small, base, medium, large, or edge-optimized;
- device, dtype, and CUDA availability;
- key runtime knobs, including image size, threshold, max detections, prompt
  expansion, and adapter-specific NMS settings when applicable.

Example command shape:

```bash
VISUAL_GROUNDING_BASE_URL=http://127.0.0.1:18880 \
VISUAL_GROUNDING_TIMEOUT_S=60 \
just agent::harness molmo-visual-grounding-benchmark \
  pipeline=grounding-dino,yoloe,yolo-world,omdet-turbo,yolo-custom \
  corpus=harness/visual_grounding/local_raw_fpv_corpus.json \
  require_success=true
```

For DINO-family candidates, run at least a small threshold sweep per model size
instead of testing only the current defaults. The first matrix should include:

- current defaults: `box_threshold=0.35`, `text_threshold=0.25`;
- recall-oriented: `box_threshold=0.25`, `text_threshold=0.20`;
- conservative: `box_threshold=0.40`, `text_threshold=0.30`.

For YOLO-family candidates, keep the current tuned YOLOE point as one row and
add at least one lower-recall/higher-precision and one higher-recall setting.
Use cleanup-family prompt expansion consistently unless a row explicitly tests
the no-expansion ablation.

If the local RAW_FPV corpus is stale or missing, rebuild it from a stored cleanup
run before ranking:

```bash
.venv/bin/python scripts/visual_grounding/build_visual_grounding_corpus_from_cleanup_run.py \
  output/molmo/<run>/seed-7 \
  --output harness/visual_grounding/local_raw_fpv_corpus.json
```

Primary ranking:

1. Perception score from recall/precision on the benchmark corpus.
2. Average sidecar stage latency.
3. Failure/timeout/parse rate.

Selection should happen in two passes:

1. Pick the best Pareto rows within each family, balancing score and latency.
2. Compare only those family winners to choose the promotion set.

This prevents a large but slow model from hiding a useful medium model, and
prevents a tiny but weak model from making a whole family look unsuitable.

Hard rejection:

- any pipeline failure rate above zero in the benchmark run;
- structured-output parse failures;
- missing real/hosted stage provenance;
- missing device/runtime diagnostics for local GPU candidates;
- average latency worse than current CPU DINO unless perception score improves
  materially.

Promotion set:

- best overall perception candidate;
- fastest candidate that clears current DINO quality;
- best DINO-family row, unless it is already one of the winners;
- CUDA `grounding-dino` tiny/default rerun as the repaired historical baseline,
  even if a larger DINO row becomes the DINO-family winner.

## End-To-End Validation

After perception benchmark ranking, run apple-to-apple cleanup checks with:

- `visual_grounding=sim`;
- `camera-raw` / RAW_FPV input;
- best overall perception candidate;
- fastest acceptable perception candidate;
- repaired CUDA `grounding-dino` baseline if not already selected.

Run both direct-control and Codex-runtime checks when feasible. Codex runs must
continue to access visual grounding only through the existing MCP cleanup tools;
the agent must not receive service URLs, model paths, or credentials.

E2E reports should compare:

- exact private matches;
- semantic accepted count;
- candidate count;
- raw FPV observation count;
- robot view steps;
- wall time;
- sidecar stage latency;
- Codex/MCP trace time where available.

Do not promote a new default until it beats current CPU DINO in perception
benchmark quality/latency and completes at least one E2E cleanup validation run
without contract regressions.

## Acceptance Criteria

- A dedicated GPU sidecar environment can start the visual-grounding service in
  `real-router` / `real` mode.
- `grounding-dino` benchmark results show real CUDA-capable runtime diagnostics.
- Benchmark reports rank all first-wave candidates and model-size rows on
  identical RAW_FPV inputs.
- Each practical family has at least two tested sizes/configurations, or the
  report explicitly marks the family as under-sampled with the reason.
- Reports preserve stage provenance, latency, overlays, and private-label
  separation.
- The selected pipeline is validated in apple-to-apple cleanup reports against
  `sim` and `RAW_FPV`.
- Core cleanup `.venv/` remains free of CUDA model dependency requirements.

## Test Plan

- Unit or contract tests for adapter catalog entries and missing-dependency
  behavior for new candidate pipelines.
- Contract tests confirming failed real sidecar calls return visible failures
  with zero fabricated candidates.
- Benchmark checker:

```bash
.venv/bin/python scripts/visual_grounding/check_visual_grounding_benchmark_result.py \
  <benchmark-run-dir> \
  --require-success
```

- Report review for overlays, stage diagnostics, latency, and private-label
  separation.
- E2E cleanup checker on the selected apple-to-apple run directories.

## Open Follow-Ups

- Decide whether the sidecar environment should be represented by a checked-in
  dependency manifest, a `uv sync --project` helper, or a `just` setup recipe.
- Decide whether `yolo-custom` needs a small generated cleanup ontology dataset
  before it can be fairly compared.
- Decide whether to add a compact benchmark matrix manifest so model id, size
  tier, thresholds, image size, and prompt expansion are versioned instead of
  embedded only in shell commands.
- Add a real Agibot G2 head-camera seed set before choosing a physical-robot
  default; the MolmoSpaces RAW_FPV corpus is sufficient for this simulator-side
  promotion gate.

## Review Decision Reconciliation

**Review date:** 2026-05-26
**Review route:** `intuitive-flow` inline review. External `autoplan` was not
run because this local work-network session must not launch system-provider
Codex or Claude Code workflows.

Accepted decisions:

- Keep the public cleanup MCP tools and `POST /v1/visual-grounding/candidates`
  HTTP contract unchanged.
- Use a checked-in sidecar dependency project plus docs/recipes for
  `.venv-visual-grounding/`, rather than moving CUDA Torch into the core
  Roboclaws `.venv/`.
- Add a compact benchmark matrix manifest so first-wave model ids, size tiers,
  thresholds, image size, max detections, prompt expansion, and NMS knobs are
  versioned as benchmark inputs.
- Treat real CUDA benchmark and Codex/runtime cleanup reports as local hardware
  gates. CI-safe tests should prove contract behavior, matrix expansion,
  provenance, failure visibility, and private-label separation without claiming
  real GPU model results.
- Mark unavailable or one-size-only model families as under-sampled in the
  benchmark output instead of using them for broad family rejection claims.

Deferred decisions:

- `yolo-custom` can be cataloged and benchmarked when weights are supplied, but
  a generated cleanup ontology dataset remains a separate follow-up.
- Real Agibot G2 head-camera seeds remain a physical-robot promotion input, not
  a prerequisite for the MolmoSpaces RAW_FPV simulator-side benchmark gate.
