# MolmoSpaces Visual Grounding Results

Last updated: 2026-05-26

This page records the current relative results for MolmoSpaces
`camera-labels` visual-grounding pipelines. It is the human-facing overview for
choosing a default pipeline and for appending future benchmark or cleanup runs.

## Current Recommendation

Use `visual_grounding=grounding-dino` as the default real visual-grounding
pipeline for `camera-labels` runs.

Keep `visual_grounding=sim` as the deterministic control baseline. Keep
`yoloe` as the ultra-fast speed lane, now with cleanup-family prompt expansion
enabled by default, but do not make it the default until recall improves. The
best tested YOLOE speed config is:

```bash
VISUAL_GROUNDING_YOLOE_MODEL_ID=yoloe-11s-seg.pt
VISUAL_GROUNDING_YOLO_CONFIDENCE_THRESHOLD=0.20
VISUAL_GROUNDING_YOLO_IMAGE_SIZE=960
VISUAL_GROUNDING_YOLO_MAX_DET=8
```

For proposer-plus-refiner experiments, the current quality candidate is
`grounding-dino+vertex_ai/gemini-3-flash-preview`: it produced the best
same-matrix end-to-end cleanup check among the Gemini/Qwen refiners, with 10
cleaned handles and 8/10 exact private matches. It is still not the default
because latency and token usage are much higher than proposer-only Grounding
DINO. `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` is the cheaper
Gemini comparison lane. Do not promote the Qwen 8B refiner despite its
perception-benchmark precision; it over-rejected in the cleanup loop.

## Selection Summary

| Pipeline | Current role | Why |
| --- | --- | --- |
| `sim` | Control baseline | Best controlled cleanup score, no real perception claim. |
| `grounding-dino` | Default real pipeline | Best proposer-only recall and best DINO-vs-YOLOE score on the current corpus. |
| `yoloe` | Ultra-fast speed lane | Prompt expansion improved recall materially, but it still trails Grounding DINO. |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | Quality refiner candidate | Best same-matrix Gemini/Qwen cleanup result, but high latency and token use. |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | Cheaper Gemini refiner comparison | Partial cleanup success; much better E2E behavior than Qwen 8B, but below Gemini 3-flash. |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | Conservative refiner comparison | Best perception-benchmark precision, but over-rejected in cleanup E2E and failed. |
| `grounding-dino+mimo-v2-omni` | Slow quality opt-in | Only refiner route with same-matrix cleanup E2E evidence, but default 20s timeout fails. |
| `mimo-v2-omni-direct` | Experimental direct VLM | Token-plan route has the best direct-VLM benchmark score, but no same-matrix end-to-end cleanup report yet. |
| `xiaomi/mimo-v2-omni-direct` | Aggregation-route experiment | Works through the internal aggregation route, but was slower and less stable than the token-plan MiMo route. |
| `vertex_ai/gemini-3.1-flash-lite-preview-direct` | Fast hosted-VLM experiment | Fastest healthy provider-prefixed route, but current recall/precision are too low for default. |
| `vertex_ai/gemini-3-flash-preview-direct` | Hosted-VLM quality experiment | Slightly higher score than Gemini lite in one direct run, but much slower and noisy. |
| `siliconflow/Qwen/Qwen3-VL-8B-Instruct-direct` | Qwen fallback experiment | Healthy JSON/vision route, but current false-positive rate is too high. |
| `tongyi/qwen3-vl-*` variants | Blocked route experiment | Smoke calls returned incomplete JSON content, so they were not promoted to full corpus. |

## YOLOE Research And Tuning Notes

Sources checked:

- [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/): YOLOE
  supports text, visual, and prompt-free modes. The current Roboclaws adapter
  uses text prompts via `model.set_classes(...)`.
- [Ultralytics predict settings](https://docs.ultralytics.com/modes/predict/):
  the relevant runtime knobs are `conf`, `iou`, `imgsz`, `max_det`,
  `agnostic_nms`, `augment`, and `retina_masks`.
- [YOLOE paper](https://arxiv.org/abs/2503.07465): visual prompts can help when
  text prompts are weak for a rare or scene-specific object, but that requires a
  reference box/image workflow that we do not yet expose in the cleanup agent.

The main local issue was ontology mismatch. The benchmark public hints are broad
families such as `food`, `dish`, `electronics`, and `linen`, while private
labels include concrete object names such as apple, potato, cup, bowl, mug,
plate, and remote control. YOLOE text prompts worked better after expanding
those families into concrete cleanup-scene labels before calling
`set_classes(...)`.

Current YOLOE adapter knobs:

- `VISUAL_GROUNDING_YOLOE_MODEL_ID` / `VISUAL_GROUNDING_YOLO_CUSTOM_MODEL_ID`
- `VISUAL_GROUNDING_YOLO_CONFIDENCE_THRESHOLD`
- `VISUAL_GROUNDING_YOLO_IMAGE_SIZE`
- `VISUAL_GROUNDING_YOLO_IOU_THRESHOLD`
- `VISUAL_GROUNDING_YOLO_MAX_DET`
- `VISUAL_GROUNDING_YOLO_AGNOSTIC_NMS`
- `VISUAL_GROUNDING_YOLO_AUGMENT`
- `VISUAL_GROUNDING_YOLO_RETINA_MASKS`
- `VISUAL_GROUNDING_YOLO_EXPAND_CLEANUP_HINTS`

Best tested YOLOE balance on the 28-observation RAW_FPV corpus:

| YOLOE config | Candidates | Recall | Precision | Score | Avg latency | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Old coarse hints, 11s default | 16 | 0.04878 | 0.125 | 0.170579 | 95.679ms | Historical baseline before hint expansion. |
| Expanded hints, 11s default | 48 | 0.121951 | 0.104167 | 0.203532 | 229.0ms | New default adapter behavior. |
| Expanded hints, 11s, `conf=0.20`, `imgsz=960`, `max_det=8` | 51 | 0.146341 | 0.117647 | 0.221664 | 368.821ms | Best tested YOLOE config. |
| Expanded hints, 11s, `conf=0.15`, `imgsz=960`, `max_det=12` | 75 | 0.146341 | 0.08 | 0.208488 | 392.179ms | More recall-oriented, too many false positives. |
| Expanded hints, 11s, `conf=0.20`, `max_det=8` | 55 | 0.121951 | 0.090909 | 0.198891 | 221.857ms | Faster, but lost the 960-image recall gain. |
| Expanded hints, 11s, `conf=0.25`, `imgsz=960`, `max_det=8` | 44 | 0.097561 | 0.090909 | 0.185477 | 356.821ms | Higher threshold over-pruned. |
| Expanded hints, 26s default | 44 | 0.073171 | 0.068182 | 0.164108 | 289.893ms | Larger 26s weight did not help this corpus. |

## Perception Benchmark Results

All rows below use the same path-backed RAW_FPV benchmark corpus unless noted.
The current corpus has 28 observations. Recall and precision are against private
benchmark labels; those labels are scoring evidence and are not returned to the
cleanup agent.

| Pipeline | Candidates | Recall | Precision | Avg latency | Failure rate | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `grounding-dino` | 58 | 0.219512 | 0.155172 | 4685.857ms | 0.0 | Best proposer-only quality. |
| `yoloe` expanded hints | 48 | 0.121951 | 0.104167 | 229.0ms | 0.0 | New default YOLOE adapter behavior. |
| `yoloe` expanded hints, tuned | 51 | 0.146341 | 0.117647 | 368.821ms | 0.0 | Best tested YOLOE speed config: 11s, `conf=0.20`, `imgsz=960`, `max_det=8`. |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | 20 | 0.121951 | 0.25 | 7917.821ms | 0.0 | Best Gemini/Qwen refiner score; aggressive but clean. |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | 39 | 0.121951 | 0.128205 | 7482.25ms | 0.0 | Fast Gemini refiner, but low actionability and lower precision than Qwen 8B. |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | 67 | 0.170732 | 0.104478 | 23914.571ms | 0.0 | Higher recall, too slow and verbose for default refine. |
| `grounding-dino+mimo-v2-omni` | 37 | 0.195122 | 0.216216 | 31253.429ms | 0.0 | Precision improves, latency is high. |
| `mimo-v2-omni-direct` | 71 | 0.268293 | 0.15493 | 29189.321ms | 0.0 | Token-plan route; best direct-VLM score so far, still no E2E cleanup comparison. |
| `xiaomi/mimo-v2-omni-direct` | 61 | 0.219512 | 0.147541 | 41412.679ms | 0.142857 | Internal aggregation route; 4 read timeouts on 28 observations. |
| `vertex_ai/gemini-3.1-flash-lite-preview-direct` | 52 | 0.121951 | 0.096154 | 3290.643ms | 0.0 | Fastest healthy provider-prefixed direct VLM route. |
| `vertex_ai/gemini-3-flash-preview-direct` | 86 | 0.146341 | 0.069767 | 20655.286ms | 0.0 | Dedicated run passed; combined run saw 1 read timeout, so latency is noisy. |
| `siliconflow/Qwen/Qwen3-VL-8B-Instruct-direct` | 45 | 0.04878 | 0.044444 | 5217.25ms | 0.0 | Healthy route but very high false-positive rate. |

Combined proposer comparison:

| Pipeline | Score | Interpretation |
| --- | ---: | --- |
| `grounding-dino` | 0.275042 | Current proposer winner. |
| `yoloe` expanded hints, tuned | 0.221664 | Best tested YOLOE speed config. |
| `yoloe` expanded hints | 0.203532 | New default YOLOE adapter behavior. |
| `yoloe` old coarse hints | 0.170579 | Historical pre-tuning baseline. |

Benchmark artifacts:

- `output/visual-grounding-benchmark/path-backed-grounding-dino-real-0525/`
- `output/visual-grounding-benchmark/path-backed-yoloe-real-0525/`
- `output/visual-grounding-benchmark/path-backed-proposer-real-comparison-0525/`
- `output/visual-grounding-benchmark/path-backed-yoloe-11s-expanded-real-0526/`
- `output/visual-grounding-benchmark/path-backed-yoloe-26s-expanded-real-0526/`
- `output/visual-grounding-benchmark/path-backed-yoloe-11s-expanded-img960-conf015-0526/`
- `output/visual-grounding-benchmark/path-backed-yoloe-11s-expanded-img960-conf020-maxdet8-0526/`
- `output/visual-grounding-benchmark/path-backed-yoloe-11s-expanded-conf020-maxdet8-0526/`
- `output/visual-grounding-benchmark/path-backed-yoloe-11s-expanded-img960-conf025-maxdet8-0526/`
- `output/visual-grounding-benchmark/path-backed-grounding-dino-mimo-refiner-real-0525/`
- `output/visual-grounding-benchmark/refiner-vlm-smoke-0526/`
- `output/visual-grounding-benchmark/path-backed-grounding-dino-gemini-qwen-refiner-0526/`
- `output/visual-grounding-benchmark/path-backed-mimo-v2-omni-direct-0525_202437/`
- `output/visual-grounding-benchmark/provider-prefixed-vlm-smoke-0526/`
- `output/visual-grounding-benchmark/siliconflow-qwen3-vl-smoke-0526/`
- `output/visual-grounding-benchmark/path-backed-provider-prefixed-vlm-direct-0526/`
- `output/visual-grounding-benchmark/path-backed-gemini-direct-0526/`
- `output/visual-grounding-benchmark/path-backed-siliconflow-qwen3-vl-direct-0526/`

## Hosted VLM Smoke Results

The smoke corpus has 3 synthetic observations and is used as a route-health
gate before spending time on the 28-observation RAW_FPV corpus.

| Pipeline | Smoke result | Avg latency | Notes |
| --- | --- | ---: | --- |
| `xiaomi/mimo-v2-omni-direct` | Pass | 18573.333ms | JSON and vision input work through the aggregation route. |
| `vertex_ai/gemini-3.1-flash-lite-preview-direct` | Pass | 4607.0ms | Fastest passing smoke route in the first hosted-VLM batch. |
| `vertex_ai/gemini-3-flash-preview-direct` | Pass | 6105.333ms | Passed smoke with clean JSON output. |
| `tongyi/qwen3-vl-flash-direct` | Fail | 1455.333ms | Returned incomplete JSON content with no parseable object. |
| `tongyi/qwen3-vl-plus-direct` | Fail | 3080.333ms | Same incomplete JSON failure mode as the flash route. |
| `siliconflow/Qwen/Qwen3-VL-8B-Instruct-direct` | Pass | 1988.333ms | Healthy Qwen fallback route; advanced to full corpus. |

## Refiner Benchmark Results

The refiner route keeps Grounding DINO as the proposer and asks the hosted VLM
only to review/filter candidate boxes. This is a different task from direct VLM
grounding, and the results are materially different.

Smoke corpus, 3 observations:

| Pipeline | Smoke result | Recall | Precision | Avg latency | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | Pass | 1.0 | 1.0 | 8809.667ms | Healthy route. |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | Pass | 1.0 | 1.0 | 11261.0ms | Healthy route, slower. |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | Pass | 0.5 | 1.0 | 5971.333ms | Conservative route. |
| `grounding-dino+tongyi/qwen3-vl-flash` | Fail | n/a | n/a | n/a | Incomplete JSON content. |
| `grounding-dino+tongyi/qwen3-vl-plus` | Fail | n/a | n/a | n/a | Incomplete JSON content. |

Full RAW_FPV corpus, 28 observations:

| Pipeline | Candidates | Recall | Precision | Avg latency | Total tokens | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | 20 | 0.121951 | 0.25 | 7917.821ms | 36072 | Best precision and best score in this refiner batch. |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | 39 | 0.121951 | 0.128205 | 7482.25ms | 64089 | Similar latency to Qwen 8B, worse precision/actionability. |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | 67 | 0.170732 | 0.104478 | 23914.571ms | 156378 | Higher recall, but too slow and verbose for default refine. |

Interpretation: the perception-only refiner benchmark favored Qwen 8B because
it emitted the cleanest candidate list. The end-to-end cleanup checks below
changed the operational recommendation: Qwen 8B over-rejected useful candidates
in the cleanup loop, while Gemini kept enough candidates to drive actual
cleanup. Tongyi Qwen flash/plus should remain blocked until the incomplete JSON
route is fixed.

## End-To-End Cleanup Results

All rows below use seed 7 and the MolmoSpaces camera-labels cleanup path unless
noted.

| Run | Pipeline | Candidates | Declares | Cleaned handles | Exact private matches | Sweep coverage | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Direct control | `sim` | 13 | n/a | 10 | 8/10 | 1.0 | Passed |
| Direct fake transport | `fake-http` | 14 | 14 | 2 | 2/10 | 1.0 | Partial success |
| MCP smoke fake transport | `fake-http` | 14 | 14 | 2 | 2/10 | 1.0 | Partial success |
| Direct proposer-only | `grounding-dino` | 20 | n/a | 4 | 3/10 | 1.0 | Passed |
| MCP smoke proposer-only | `grounding-dino` | 20 | 14 | 4 | 3/10 | 1.0 | Passed |
| Live Codex proposer-only | `grounding-dino` | 24 | 16 | 4 | 3/10 | 1.0 | Partial success |
| Direct proposer+refiner, default timeout | `grounding-dino+mimo-v2-omni` | 0 | 14 | 0 | n/a | n/a | Failed usefully |
| Direct proposer+refiner, 240s timeout | `grounding-dino+mimo-v2-omni` | 17 | 14 | 7 | 5/10 | 1.0 | Passed |
| Direct proposer+refiner | `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | 3 | 14 | 1 | 0/10 | 1.0 | Failed |
| Direct proposer+refiner | `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | 19 | 14 | 8 | 6/10 | 1.0 | Partial success |
| Direct proposer+refiner | `grounding-dino+vertex_ai/gemini-3-flash-preview` | 30 | 14 | 10 | 8/10 | 1.0 | Passed |

Gemini/Qwen refiner check telemetry:

| Pipeline | Refiner calls | Avg refiner latency | Total refiner tokens | Avg proposer latency |
| --- | ---: | ---: | ---: | ---: |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | 14 | 8311ms | 32601 | 4518ms |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | 14 | 9104ms | 46713 | 4277ms |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | 14 | 19815ms | 78282 | 4284ms |

Cleanup artifacts:

- `output/molmo/direct-camera-labels-sim-baseline/0525_2206/seed-7/report.html`
- `output/molmo/direct-camera-labels-fake-http/0525_2252/seed-7/report.html`
- `output/molmo/mcp-camera-labels-fake-http/0525_2253/seed-7/report.html`
- `output/molmo/direct-camera-labels/0525_2132/seed-7/report.html`
- `output/molmo/mcp-camera-labels-grounding-dino/0525_2141/seed-7/report.html`
- `output/molmo/codex-camera-labels-grounding-dino/0525_2216/seed-7/report.html`
- `output/molmo/direct-camera-labels-grounding-dino-mimo-refiner/0525_2145/seed-7/report.html`
- `output/molmo/direct-camera-labels-grounding-dino-mimo-refiner-240s/0525_2153/seed-7/report.html`
- `output/molmo/direct-camera-labels-grounding-dino-qwen8b-refiner-check/0526_1243/seed-7/report.html`
- `output/molmo/direct-camera-labels-grounding-dino-gemini-lite-refiner-check/0526_1246/seed-7/report.html`
- `output/molmo/direct-camera-labels-grounding-dino-gemini-flash-refiner-check/0526_1251/seed-7/report.html`

## Interpretation

`grounding-dino` is the current default real pipeline because it is the best
proposer-only option on recall and overall score, and it already has direct,
MCP smoke, and live Codex cleanup evidence.

`yoloe` is now a credible ultra-fast lane, not just a placeholder. Expanding
cleanup-family hints improved recall from 0.04878 to 0.121951, and the best
tested speed config reached 0.146341 recall at 368.821ms average latency. That
is still below Grounding DINO's recall and score, so YOLOE should not be the
default. It is useful for low-latency sweeps, for future navigation-time
perception, and as a proposer to revisit after we add better object hints or
visual-prompt reference boxes.

For hosted VLM refine, the end-to-end check overrides the perception-only
ranking. `grounding-dino+vertex_ai/gemini-3-flash-preview` is the best quality
refiner in the Gemini/Qwen set: it cleaned 10 observed handles and reached 8/10
exact private matches. The tradeoff is cost and latency: 14 refiner calls
averaged 19.8s and reported 78k total refiner tokens. Use it only when quality
matters more than runtime. `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview`
is the cheaper Gemini lane: 8 cleaned handles, 6/10 exact private matches, and
9.1s average refiner latency. Qwen 8B should not be the default refiner for this
cleanup loop; it looked precise in the isolated benchmark but over-rejected in
E2E, producing only 3 candidates, 1 cleaned handle, and 0/10 exact private
matches.

`grounding-dino+mimo-v2-omni` remains the useful quality reference because it
has same-matrix cleanup proof. It improved the end-to-end cleanup run from 4
cleaned handles / 3 exact private matches to 7 cleaned handles / 5 exact private
matches, but only after increasing `VISUAL_GROUNDING_TIMEOUT_S` to 240 seconds.
With the default 20 second timeout, it produced visible timeout failures and
zero fabricated simulator labels, which is the correct failure mode but not a
usable default.

`mimo-v2-omni-direct` has promising benchmark evidence but needs an end-to-end
cleanup run before it can be promoted. The internal aggregation route model id
`xiaomi/mimo-v2-omni` did not improve on the token-plan MiMo route in this
benchmark: it had lower recall, similar precision, higher latency, and 4 read
timeouts.

Gemini routes are useful comparison lanes. Gemini 3-flash is now the quality
refiner candidate; Gemini 3.1 flash-lite is the cheaper partial-success lane.
Tongyi Qwen flash/plus failed the smoke route with incomplete JSON output, so
they should stay blocked until the request or provider route is repaired.

## How To Add Future Results

For a new benchmark, append one row to "Perception Benchmark Results" with:

- pipeline id;
- observation count if it differs from 28;
- candidate count;
- recall and precision;
- average latency;
- failure or timeout rate;
- artifact path.

For a new cleanup run, append one row to "End-To-End Cleanup Results" with:

- driver shape, such as direct, MCP smoke, live Codex, or live Claude;
- pipeline id;
- candidate count and `declare_visual_candidates` count;
- cleaned handle count;
- exact private matches;
- sweep coverage;
- pass/fail/partial status;
- artifact path.

When a result changes the recommendation, update "Current Recommendation" and
"Selection Summary" in the same commit.

## Parked Comparison Work

These are intentionally not blockers for the current recommendation:

- run a same-matrix end-to-end cleanup report for `mimo-v2-omni-direct`;
- repeat the Gemini/Qwen refiner cleanup checks across more seeds before making
  a default policy change;
- investigate the `tongyi/qwen3-vl-*` incomplete-JSON route failure;
- evaluate YOLOE visual-prompt/reference-box mode for scene-specific objects
  once we have a safe way to provide public reference crops;
- add fixed/custom YOLO only after weights, ontology, and licensing boundaries
  are reviewed;
- add a real Agibot G2 head-camera seed set before choosing a real deployed
  robot proposer;
- evaluate continuous route perception during navigation after waypoint
  observation grounding is stable.
