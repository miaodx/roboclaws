# Visual Grounding GPU Sidecar Benchmark

**Status:** Local GPU benchmark and direct cleanup validation complete
**Created:** 2026-05-26
**Source:** Visual grounding performance/debug discussion: current Grounding DINO
HTTP sidecar is fast at transport level, but the real adapter is running CPU
Torch even on a CUDA-capable workstation.
**Workflow:** `intuitive-flow` local implementation and evidence record.

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
| `omdet-turbo` | The public HF tiny checkpoint, swept across threshold/NMS variants until another valid public size is identified. | Fast non-YOLO open-vocabulary candidate for quality/latency balance. |

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
  pipeline=grounding-dino,yoloe,yolo-world,omdet-turbo \
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

If the local RAW_FPV corpus is stale or missing, rebuild it from stored cleanup
runs before ranking. The single-run builder is automated and useful for stable
fixtures, but the current tracked 28-observation corpus is weak model-ranking
evidence because it comes from one run family and uses room-level category
presence labels rather than bbox ground truth:

```bash
.venv/bin/python scripts/visual_grounding/build_visual_grounding_corpus_from_cleanup_run.py \
  output/molmo/<run>/seed-7 \
  --output harness/visual_grounding/local_raw_fpv_corpus.json
```

Prefer the representative local corpus builder for model-family comparisons:

```bash
.venv/bin/python scripts/visual_grounding/build_representative_visual_grounding_corpus.py \
  output \
  --output output/visual-grounding-corpora/representative-raw-fpv/representative_raw_fpv_corpus.json \
  --name representative-raw-fpv \
  --max-observations 96 \
  --min-raw-fpv 5
```

That builder scans multiple `run_result.json` artifacts, requires RAW_FPV and
private-evaluation data, removes exact duplicate image hashes by default,
stratifies the selection by room/category labels, and writes sampling metadata.
Its labels remain room-level category-presence labels; a bbox-annotated corpus
is still required before making fine-grained localization claims.

For the next model-selection gate, generate a fresh perception-only MolmoSpaces
corpus instead of reusing historical cleanup artifacts. The corpus generator
should actively sample:

- `scene_source=procthor-10k-val`;
- 10 distinct `scene_index` values, not only the default scene index 0;
- 10 generated cleanup targets per scene when available;
- RAW_FPV frames and public context from the same simulator state;
- private bbox labels from MuJoCo segmentation for visible target objects.

The generator should record scene index, seed, target object id, category,
source camera, camera pose/provenance, visible-pixel count, and bbox in private
label metadata. Private bbox labels are benchmark scoring data only and must not
be sent to the visual-grounding service, MCP responses, or Agent View.

Local command:

```bash
.venv/bin/python scripts/visual_grounding/build_molmospaces_visual_grounding_bbox_corpus.py \
  --output output/visual-grounding-corpora/molmospaces-bbox-10x10/corpus.json \
  --name molmospaces-bbox-10x10 \
  --scene-source procthor-10k-val \
  --scene-indices 0-9 \
  --targets-per-scene 10 \
  --frame-classes target_focused_fpv
```

Use `--scene-indices 0 --targets-per-scene 2` for a cheap local smoke. The
builder uses the MolmoSpaces subprocess backend with `include_robot=True`, saves
FPV frames under the ignored output directory, and stores private object id,
category, visible pixels, and normalized bbox only inside each observation's
`private_labels`.

Keep two frame classes separate:

- sweep FPV frames: realistic agent-view pressure tests, where target
  visibility may be weak or absent;
- target-focused FPV frames: localization scoring frames, where segmentation
  provides visible-object bbox truth.

Use bbox-aware metrics as the primary model-selection signal on the new corpus:

1. visible-object recall at IoU 0.30;
2. category-family accuracy for matched boxes;
3. duplicate and false-positive rates;
4. average sidecar latency;
5. failure, timeout, and parse rates.

Keep room-level category-presence recall as a diagnostic metric only. It can
explain broad cleanup relevance, but it should not select a default detector
because high-recall noisy proposers can look better there than they are at
localizing actionable objects.

Primary ranking:

1. Bbox-aware perception score on visible target objects.
2. Average sidecar stage latency.
3. Failure/timeout/parse rate.

2026-05-27 local result: the fresh bbox corpus promoted
`grounding-dino-base-recall` (`IDEA-Research/grounding-dino-base`,
`box_threshold=0.25`, `text_threshold=0.20`) as the default. It beat
`grounding-dino-tiny-recall` on visible-object bbox recall
(`0.877778` vs `0.866667`) and overall bbox-aware score (`0.730994` vs
`0.712989`) on 90 target-focused FPV observations across 10 MolmoSpaces scene
indices. `omdet-turbo-tiny-recall` was much faster (`53.578ms` average) but
lower recall (`0.766667`) and precision (`0.101025`).

End-to-end cleanup validation with DINO base-recall:

- scene 0: success, 8/10 exact private matches, 10 cleanup chains, 1.0 sweep
  coverage;
- scene 2: partial success, 4/10 exact private matches, 7 cleanup chains, 1.0
  sweep coverage, with three advisory-wrong placements.

Conclusion: base-recall is the default detector config, but cleanup quality is
now limited by candidate selection/destination policy under high-recall noisy
labels, not just detector localization.

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

## Local Validation Evidence

**Current selection:** the 2026-05-27 bbox-aware MolmoSpaces benchmark selects
`grounding-dino-base-recall` as the default real `camera-labels` detector
configuration. The 2026-05-26 `grounding-dino-tiny-recall` win below is kept as
historical evidence for the older RAW_FPV/category-presence benchmark; it should
not be used as the current default.

**Run date:** 2026-05-27

Fresh bbox-labeled MolmoSpaces benchmark:

- Corpus:
  `output/visual-grounding-corpora/molmospaces-bbox-representative-10scene/corpus.json`
- Scope: 90 target-focused FPV observations across 10 successful
  `procthor-10k-val` scene indices: 0, 2, 3, 4, 9, 10, 12, 13, 15, and 17.
- Benchmark artifact:
  `output/visual-grounding-benchmark/molmospaces-bbox-dino-omdet-0527-v2/`
- Checker:
  `.venv/bin/python scripts/visual_grounding/check_visual_grounding_benchmark_result.py output/visual-grounding-benchmark/molmospaces-bbox-dino-omdet-0527-v2 --require-success`
- Winner: `grounding-dino-base-recall`
- Winner metrics: score `0.730994`, bbox recall `0.877778`, bbox precision
  `0.148218`, bbox category-family accuracy `0.746835`, mean latency
  `348.422ms`.
- Runner-up: `grounding-dino-tiny-recall`, score `0.712989`, bbox recall
  `0.866667`, mean latency `243.456ms`.
- Fast comparison: `omdet-turbo-tiny-recall`, score `0.664263`, bbox recall
  `0.766667`, mean latency `53.578ms`.

Multi-scene cleanup validation with DINO base-recall:

- Scene 0:
  `output/molmo/direct-camera-labels-dino-base-recall-scene0-0527/seed-7/report.html`
  passed as success, with 8/10 exact private matches, 10 cleanup chains, and
  sweep coverage `1.0`.
- Scene 2:
  `output/molmo/direct-camera-labels-dino-base-recall-scene2-0527/seed-7/report.html`
  is partial-success evidence, with 4/10 exact private matches, 7 cleanup
  chains, sweep coverage `1.0`, and three advisory-wrong placements.

**Run date:** 2026-05-26

The local GPU sidecar ran the existing HTTP service boundary in
`real-router` / `real` mode from the dedicated `.venv-visual-grounding/`
environment. The sidecar diagnostics recorded CUDA runtime evidence for
Grounding DINO on `NVIDIA RTX 3500 Ada Generation Laptop GPU` with
`torch_version=2.12.0+cu130`.

Benchmark corpus:

- `harness/visual_grounding/local_raw_fpv_corpus.json`
- `harness/visual_grounding/raw_fpv/`
- 28 stored MolmoSpaces RAW_FPV observations from
  `output/visual-grounding-corpora/codex-camera-raw-mcp-check-final/`

Primary implemented-row benchmark:

- Artifact:
  `output/visual-grounding-benchmark/gpu-implemented-subset-expanded-matrix/0526_1947/`
- Scope: implemented first-wave rows for `grounding-dino`, `yoloe`, and
  `yolo-world`
- Checker:
  `.venv/bin/python scripts/visual_grounding/check_visual_grounding_benchmark_result.py output/visual-grounding-benchmark/gpu-implemented-subset-expanded-matrix/0526_1947 --require-success`
- Result: 12 rows, zero failures
- Historical winner for this category-presence benchmark:
  `grounding-dino-tiny-recall`
- Winner metrics: score `0.543014`, recall `0.707317`, precision `0.154255`,
  mean latency `235.179ms`
- Runtime: CUDA, `IDEA-Research/grounding-dino-tiny`,
  `box_threshold=0.25`, `text_threshold=0.20`
- Family sweep: `grounding-dino`, `yoloe`, and `yolo-world` each have at least
  three successful tested configurations; DINO includes tiny/base default,
  recall, and conservative rows.

Full matrix availability benchmark:

- Artifact:
  `output/visual-grounding-benchmark/gpu-full-matrix-expanded/0526_1948/`
- Checker:
  `.venv/bin/python scripts/visual_grounding/check_visual_grounding_benchmark_result.py output/visual-grounding-benchmark/gpu-full-matrix-expanded/0526_1948`
- Result: implemented `grounding-dino`, `yoloe`, and `yolo-world` rows
  completed; at the time `omdet-turbo` rows reported `missing_dependency`.
- Family sweep: `omdet-turbo` was marked under-sampled with zero successful
  configs and `missing_dependency`.

Apple-to-apple direct cleanup validation:

- `sim` control:
  `output/molmo/visual-grounding-e2e/sim/0526_1918/seed-7/report.html`
- Selected historical `grounding-dino-tiny-recall` row:
  `output/molmo/visual-grounding-e2e/grounding-dino-tiny-recall/0526_1921/seed-7/report.html`
- Checker for sim:
  `.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py --expect-task 帮我收拾这个房间 --expect-backend molmospaces_subprocess --expect-seeds 7 --expect-profile camera-labels --min-generated-mess-count 10 --require-advisory-scoring --require-robot-views --require-camera-model-policy --min-sweep-coverage 1.0 output/molmo/visual-grounding-e2e/sim/0526_1918`
- Checker for Grounding DINO:
  `.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py --expect-task 帮我收拾这个房间 --expect-backend molmospaces_subprocess --expect-seeds 7 --expect-profile camera-labels --min-generated-mess-count 10 --require-advisory-scoring --require-robot-views --require-camera-model-policy --expect-visual-grounding-pipeline grounding-dino --allow-partial-cleanup --min-sweep-coverage 1.0 output/molmo/visual-grounding-e2e/grounding-dino-tiny-recall/0526_1921`
- Result: both checker runs passed.
- Sim control: 8/10 exact private matches, 10/10 semantic accepted,
  sweep coverage `1.0`.
- Grounding DINO: 8/10 exact private matches, 9/10 semantic accepted,
  sweep coverage `1.0`, external visual-grounding provenance, CUDA runtime
  diagnostics, and `grounding-dino` stage evidence.
- Note: the Grounding DINO direct run had one advisory semantic disagreement
  from a pillow placed on a TV stand, while the deterministic cleanup checker
  still passed the accepted validation gate.

Codex-runtime cleanup validation was not run in this pass because the local
network was `work`, where OpenClaw workflows are guarded and coding-agent runs
must use an allowed repo-local `.env` key route.

## Open Follow-Ups

- Add a `just` setup recipe for syncing `sidecars/visual-grounding/` into
  `.venv-visual-grounding/`; current docs include the manual `uv sync` command.
- Expand the next bbox-aware matrix with more valid public model sizes as they
  are identified. Current OmDet support is tiny-only for the public HF adapter.
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

- `yolo-custom` is removed from active support because there is no planned
  cleanup-ontology training set or supplied weight package; YOLO-family
  comparisons should use `yoloe` and `yolo-world`.
- Real Agibot G2 head-camera seeds remain a physical-robot promotion input, not
  a prerequisite for the MolmoSpaces RAW_FPV simulator-side benchmark gate.

## Sidecar Setup

The visual-grounding sidecar uses its own uv environment so CUDA Torch and
model packages do not enter the core Roboclaws `.venv/`:

```bash
UV_PROJECT_ENVIRONMENT="$PWD/.venv-visual-grounding" \
  uv sync --project sidecars/visual-grounding --extra cuda --extra yoloe --extra omdet

.venv-visual-grounding/bin/python - <<'PY'
import torch, transformers, ultralytics
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
print("transformers", transformers.__version__)
print("ultralytics", ultralytics.__version__)
PY
```

Start the service in real-router mode after the environment is ready:

```bash
VISUAL_GROUNDING_DEVICE=auto \
VISUAL_GROUNDING_TORCH_DTYPE=auto \
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base \
VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 \
VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 \
  .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline real-router --adapter-mode real
```

Grounding DINO, YOLOE/YOLO-World, and OmDet-Turbo choose their model ids from
the benchmark row first, then `VISUAL_GROUNDING_*_MODEL_ID`, then the adapter
default. Current OmDet support uses
`omlab/omdet-turbo-swin-tiny-hf`; `omlab/omdet-turbo-swin-base-hf` is not a
valid public Hugging Face model id as of this update.
