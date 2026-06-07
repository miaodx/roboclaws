# MolmoSpaces Visual Grounding Results

Last updated: 2026-06-06

This page records the current relative results for MolmoSpaces
`camera-grounded-labels` camera labelers and their internal visual-grounding
pipelines. It is the human-facing overview for choosing a default camera
labeler and for appending future benchmark or cleanup runs.
Rows that name `mimo-v2-omni` are historical 2026-05 benchmark artifacts only;
active MiMo visual routes now use `mimo-v2.5`.

## Current Recommendation

Use `camera_labeler=grounding-dino` as the default real camera labeler for
`evidence_lane=camera-grounded-labels` runs. For real sidecar runs, the current
recommended Grounding DINO config is the bbox-aware benchmark winner:

```bash
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base
VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25
VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20
```

This supersedes the earlier tiny-recall recommendation. The old 96-image
representative RAW_FPV benchmark used room/category-presence labels and could
make tiny-recall look better than base. The 2026-05-27 bbox-labeled benchmark
uses fresh MolmoSpaces target-focused FPV frames from 10 scene indices and
private MuJoCo segmentation boxes; on that benchmark, base-recall has slightly
higher visible-object bbox recall than tiny-recall.

Keep `camera_labeler=sim-projected-labels` as the deterministic control
baseline. Keep
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
perception-benchmark precision; it over-rejected in the cleanup loop. The
historical `grounding-dino+mimo-v2-omni` run remains useful evidence for the
MiMo comparison lane, but new MiMo refiner or direct-VLM runs should use
`mimo-v2.5`: the old run needed a 240s timeout and its same-matrix cleanup
result was below both Gemini refiners.

The 2026-05-27 live Codex rerun with the current DINO base-recall sidecar
changed the live-agent readout: Codex + `grounding-dino` matched
`world-oracle-labels`
on final cleanup quality for the scene-0 seed-7 task, but took longer because
it produced many unresolved camera declarations. Treat that as a pass for the
current DINO base lane, not proof that camera labels are cheaper than the
privileged structured-label control. The same-day current mify `camera-raw-fpv`
rerun did not produce a cleanup score: it placed only one object, called `done`
with 6/14 waypoint coverage, and then hit the mify provider/tool namespace
failure again. Keep the 2026-05-26 raw-FPV success as provider-route reference
evidence only.

The 2026-06-06 strict-FPV rerun changes the `camera-raw-fpv` conclusion. The tool
route was healthy enough to run the full public waypoint sweep, and focused
prompt-loop tuning made Codex produce reviewable same-source bbox declarations.
However, pure `camera-raw-fpv` still completed only two grounded cleanup chains for
`seed=7 generated_mess_count=5`, below the five-object threshold, then entered
low-yield post-sweep retries. The failure classification is visual
grounding/image-understanding reliability, not Docker, MCP, placement policy,
or declaration schema. The run directory is
`output/household/household-cleanup/codex-camera-raw/0606_1537/seed-7`; it was
stopped manually after about 26 minutes, so it has trace/live logs but no
`run_result.json`, `checker.log`, or `report.html`.

The 2026-06-08 perception-only follow-up made the raw-FPV comparison scoreable
without changing live actionability. A public sweep corpus plus the saved live
trace produced a 36-frame raw-only probe set with private scorer labels covering
all five generated targets and no private-label or executable-handle leakage in
prompt inputs. CodexENV `gpt-5.5` still stayed below threshold: baseline JSON
confirmed 1 strict-bbox / 2 coarse unique targets, while skill JSON plus
semantic-map planning context confirmed 1 strict / 1 coarse unique target. The
probe route recommendation is `prefer_camera_grounded_labels`.

Success/latency conclusion: keep `grounding-dino` base-recall as the default
real `camera-grounded-labels` camera-labeler pipeline. For live-agent comparison,
`world-oracle-labels` remains the privileged sim/API control,
`camera-grounded-labels` + DINO base is the current real camera-label pass, and
pure `camera-raw-fpv` should be
treated as a baseline/ablation lane rather than the real-robot production path.
Real-robot cleanup should use assisted RAW-FPV or `camera-grounded-labels`: robot-camera
evidence first, a deployable visual-grounding sidecar to propose bbox/mask
candidates, and the LLM/coding agent for selection, tool use, recovery, and
verification.

## Selection Summary

| Pipeline | Current role | Why |
| --- | --- | --- |
| `sim` | Control baseline | Best controlled cleanup score, no real perception claim. |
| `grounding-dino` | Default real pipeline | Best bbox-aware proposer score on the current representative MolmoSpaces corpus; recommended config is base-recall. |
| `yoloe` | Ultra-fast speed lane | Prompt expansion improved recall materially, but it still trails Grounding DINO. |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | Quality refiner candidate | Best same-matrix Gemini/Qwen cleanup result, but high latency and token use. |
| `omdet-turbo` | Fast comparison lane | OmDet tiny-recall is much faster than DINO and beats default OmDet, but trails DINO base/tiny recall on bbox recall and precision. |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | Cheaper Gemini refiner comparison | Partial cleanup success; much better E2E behavior than Qwen 8B, but below Gemini 3-flash. |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | Conservative refiner comparison | Best perception-benchmark precision, but over-rejected in cleanup E2E and failed. |
| `grounding-dino+mimo-v2-omni` | Historical MiMo comparison baseline | Old model id retained only as benchmark evidence; new MiMo refiner runs should use `grounding-dino+mimo-v2.5`. |
| `mimo-v2-omni-direct` | Historical direct-VLM experiment | Old model id retained only as benchmark evidence; new direct MiMo runs should use `mimo-v2.5-direct`. |
| `xiaomi/mimo-v2-omni-direct` | Historical aggregation-route experiment | Old aggregation id retained only as benchmark evidence; new aggregation-route MiMo runs should use `xiaomi/mimo-v2.5-direct`. |
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

- `VISUAL_GROUNDING_YOLOE_MODEL_ID`
- `VISUAL_GROUNDING_YOLO_CONFIDENCE_THRESHOLD`
- `VISUAL_GROUNDING_YOLO_IMAGE_SIZE`
- `VISUAL_GROUNDING_YOLO_IOU_THRESHOLD`
- `VISUAL_GROUNDING_YOLO_MAX_DET`
- `VISUAL_GROUNDING_YOLO_AGNOSTIC_NMS`
- `VISUAL_GROUNDING_YOLO_AUGMENT`
- `VISUAL_GROUNDING_YOLO_RETINA_MASKS`
- `VISUAL_GROUNDING_YOLO_EXPAND_CLEANUP_HINTS`

`yolo-custom` / `VISUAL_GROUNDING_YOLO_CUSTOM_MODEL_ID` is not an active support
lane. Re-enable it only if a cleanup-ontology training set, weight package, and
licensing boundary exist.

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

### BBox-Aware MolmoSpaces Benchmark

Run date: 2026-05-27. Corpus:
`output/visual-grounding-corpora/molmospaces-bbox-representative-10scene/corpus.json`.
The corpus has 90 target-focused FPV observations from 10 successful
`procthor-10k-val` scene indices: 0, 2, 3, 4, 9, 10, 12, 13, 15, and 17.
Private labels are MuJoCo segmentation bboxes and are not sent to the sidecar
or written to prediction JSONL. Primary score basis is bbox IoU at 0.30.

| Row | Model | Bbox recall | Bbox precision | Bbox category acc | Candidates | Avg latency | Score | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `grounding-dino-base-recall` | `IDEA-Research/grounding-dino-base` | 0.877778 | 0.148218 | 0.746835 | 533 | 348.422ms | 0.730994 | Current winner and recommended config. |
| `grounding-dino-tiny-recall` | `IDEA-Research/grounding-dino-tiny` | 0.866667 | 0.125201 | 0.679487 | 623 | 243.456ms | 0.712989 | Close, faster fallback if base latency matters. |
| `omdet-turbo-tiny-recall` | `omlab/omdet-turbo-swin-tiny-hf` | 0.766667 | 0.101025 | 0.840580 | 683 | 53.578ms | 0.664263 | Fast comparison lane, but lower bbox recall and many false positives. |
| `grounding-dino-base-default` | `IDEA-Research/grounding-dino-base` | 0.633333 | 0.271429 | 0.842105 | 210 | 401.178ms | 0.618496 | Higher precision, lower recall. |
| `grounding-dino-tiny-default` | `IDEA-Research/grounding-dino-tiny` | 0.633333 | 0.266355 | 0.842105 | 214 | 333.589ms | 0.617481 | Similar to base-default. |
| `omdet-turbo-tiny-default` | `omlab/omdet-turbo-swin-tiny-hf` | 0.655556 | 0.154047 | 0.813559 | 383 | 100.133ms | 0.605499 | Middle ground for OmDet. |
| `grounding-dino-tiny-conservative` | `IDEA-Research/grounding-dino-tiny` | 0.511111 | 0.338235 | 0.847826 | 136 | 243.656ms | 0.559096 | Precision lane. |
| `grounding-dino-base-conservative` | `IDEA-Research/grounding-dino-base` | 0.511111 | 0.326241 | 0.869565 | 141 | 349.589ms | 0.558871 | Precision lane. |
| `omdet-turbo-tiny-precision` | `omlab/omdet-turbo-swin-tiny-hf` | 0.433333 | 0.226744 | 0.743590 | 172 | 54.011ms | 0.479708 | Too much recall loss. |

Interpretation: the earlier tiny-recall win was an artifact of category-only
matching on a narrow historical corpus. With segmentation bbox truth, DINO base
recall is the best default. OmDet is viable and very fast, but today only the
public `omlab/omdet-turbo-swin-tiny-hf` checkpoint is supported in the matrix;
the previously discussed OmDet base id is not a valid public checkpoint for the
current Transformers adapter.

Artifacts:

- `output/visual-grounding-benchmark/molmospaces-bbox-dino-omdet-0527-v2/`
- `output/visual-grounding-corpora/molmospaces-bbox-representative-10scene/`

### Historical RAW_FPV Benchmark

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

## Apple-To-Apple Cleanup Rerun

Run date: 2026-05-26. All rows used seed 7, `generated_mess_count=10`,
`assets/maps/molmospaces-procthor-val-0-7`, robot-view reports, and the same
Chinese cleanup task prompt. Direct rows use the deterministic cleanup routine;
Codex rows use the Docker-backed supported coding-agent route.

| Route | Input / pipeline | Candidates | Raw FPV observations | Robot view steps | Exact private matches | Semantic accepted | Wall time | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Direct control | `sim` | 13 | 24 | 70 | 8/10 | 10/10 | 135.3s | Success |
| Direct proposer-only | `grounding-dino` | 20 | 18 | 38 | 3/10 | 7/10 | 145.2s | Partial success |
| Direct proposer+refiner | `grounding-dino+vertex_ai/gemini-3-flash-preview` | 33 | 24 | 70 | 8/10 | 10/10 | 456.6s | Success |
| Live Codex visual reasoning | `raw_fpv_only` | 15 | 22 | 90 | 8/10 | 10/10 | 897.7s | Success |
| Live Codex camera labels | `grounding-dino` | 23 | 16 | 52 | 3/10 | 7/10 | 498.4s | Partial success |
| Live Codex camera labels + refiner | `grounding-dino+vertex_ai/gemini-3-flash-preview` | 36 | 17 | 84 | 5/10 | 9/10 | 1247.9s | Partial success |

Latency details:

| Route | Visual/model timing note |
| --- | --- |
| Direct `grounding-dino` | 14 proposer calls, 67.2s total sidecar time, 4.80s average proposer latency. |
| Direct `grounding-dino+vertex_ai/gemini-3-flash-preview` | 14 proposer calls at 4.37s average plus 14 refiner calls at 22.06s average; refiner total was 308.8s. |
| Live Codex `raw_fpv_only` | 14m57s runner wall time; MCP trace spent 11m00s in between-tool/model gap and 3m02s in robot-view capture. |
| Live Codex `grounding-dino` | 8m18s runner wall time; 16 DINO declares averaged 3.87s, and MCP trace spent 4m57s in between-tool/model gap. |
| Live Codex `grounding-dino+vertex_ai/gemini-3-flash-preview` | 20m47s runner wall time; 16 declares used 68.6s proposer time and 383.2s Gemini refiner time, while MCP trace spent 10m51s in between-tool/model gap and 2m42s in robot-view capture. |

Rerun artifacts:

- `output/molmo/apple2apple-0526-direct-sim/0526_1322/seed-7/report.html`
- `output/molmo/apple2apple-0526-direct-dino/0526_1325/seed-7/report.html`
- `output/molmo/apple2apple-0526-direct-dino-gemini3flash/0526_1328/seed-7/report.html`
- `output/molmo/apple2apple-0526-codex-raw/0526_1337/seed-7/report.html`
- `output/molmo/apple2apple-0526-codex-dino/0526_1354/seed-7/report.html`
- `output/molmo/apple2apple-0526-codex-dino-gemini3flash-autocontinue-timeout240/0526_1513/seed-7/report.html`

Interpretation: `sim` and direct `grounding-dino+Gemini 3 Flash` tie on exact
cleanup quality for this seed, but `sim` is privileged control data while the
Gemini route is real camera-derived perception. Proposer-only `grounding-dino`
is much faster than the Gemini refiner but still only restores 3/10 exactly.
Live Codex `raw_fpv_only` achieved the same 8/10 exact score as the control,
but took about 15 minutes and used full image-reasoning loops. Live Codex with
DINO labels was faster than RAW_FPV but did not improve over direct
proposer-only DINO on final cleanup quality. Live Codex with DINO + Gemini
improved over proposer-only DINO from 3/10 to 5/10 exact and from 7/10 to 9/10
semantic accepted, but it took 20m47s and still missed the direct
DINO + Gemini and Codex RAW_FPV exact-match result. The refiner also encouraged
more post-placement observations and declarations, so it is not the live-agent
default despite being the direct-control quality route.

## Current-DINO Live Codex Rerun

Run date: 2026-05-27. Rows below use seed 7, `generated_mess_count=10`,
`assets/maps/molmospaces-procthor-val-0-7`, robot-view reports, the same
Chinese cleanup task prompt, and the Docker-backed Codex route through the
repo-local `.env` mify configuration allowed on the work network. The DINO row
used the current recommended sidecar config:
`IDEA-Research/grounding-dino-base`, `box_threshold=0.25`,
`text_threshold=0.20`.

| Route | Input / pipeline | Candidates / declarations | Raw FPV observations | Robot view steps | Exact private matches | Semantic accepted | Sweep coverage | Wall time | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Live Codex control | `world-oracle-labels` / sim API | n/a | 0 | 114 | 8/10 | 10/10 | 1.0 | 1025.2s | Cleanup success; runner checker failed on a fridge-sequence review gate. |
| Live Codex camera labels | `grounding-dino` base-recall | 216 | 41 | 129 | 8/10 | 10/10 | 1.0 | 1520.0s | Success. |
| Live Codex visual reasoning | `camera-raw-fpv` on current mify route | 2 model-declared objects | 11 | 29 | n/a | n/a | 0.428571 at rejected `done` | 1122.5s | Failed before score: only 1 object placed, `done` rejected for insufficient sweep coverage, then provider/tool namespace error. |

Latency and behavior notes:

| Route | Timing / behavior note |
| --- | --- |
| `world-oracle-labels` / sim API | 17m05s runner wall time, 16 Codex turns, 189 MCP tool calls, 12m41s MCP between-tool/model gap, and 3m43s robot-view capture. The report has `run_result.json` and a successful private cleanup score, but the runner exit status was 1 because the stricter checker flagged a fridge sequence. |
| `camera-grounded-labels` + DINO base | 25m20s runner wall time, 7 Codex turns, 168 MCP tool calls, 39 `declare_visual_candidates` calls, 20 resolved declarations, 196 unresolved declarations, and 173 `needs_clarification` declarations. The sidecar provenance confirms `IDEA-Research/grounding-dino-base` on CUDA with the recommended thresholds. |
| `camera-raw-fpv` current mify route | The final 2026-05-27 rerun used 9 Codex turns, 47 MCP tool calls, 11 `observe` responses, 3 `navigate_to_visual_candidate` calls, 1 `pick`, and 1 `place_inside`. It declared 2 objects from raw FPV: one unresolved linen candidate and one Potato that was placed in the fridge. The agent skipped most middle-room waypoint observations, called `done` anyway, and the server returned `insufficient_sweep_coverage` with 6/14 waypoints observed. After that, mify again emitted `function_call namespace 'mcp__roboclaws__' does not contain function 'metric_map'`, so the runner exited without `run_result.json` or `report.html`. This is not an apple-to-apple score row. |

Artifacts:

- `output/molmo/apple2apple-0527-codex-world-basecompare-rerun/0527_1733/seed-7/report.html`
- `output/molmo/apple2apple-0527-codex-dino-base/0527_1752/seed-7/report.html`
- `output/molmo/apple2apple-0527-codex-raw/0527_1818/seed-7/`
- `output/molmo/apple2apple-0527-codex-raw-rerun/0527_1825/seed-7/`
- `output/molmo/apple2apple-0527-codex-raw-promptfix/0527_1845/seed-7/`
- `output/molmo/apple2apple-0527-codex-raw-namespacefix/0527_1911/seed-7/`

Interpretation: the current DINO base row is good enough to keep as the
recommended `camera-grounded-labels` default: it reached the same final cleanup quality
as the structured-label control on this task. The cost is runtime and noisy
actionability: many DINO proposals were unresolved or needed clarification, so
the live agent spent more time declaring and filtering candidates. The 2026-05-26
RAW_FPV success remains useful, but it used a different provider/model route;
do not compare it as the current mify raw-FPV result until the tool namespace
failure is fixed and the raw agent can satisfy the same sweep and cleanup gates.

## Multi-Scene Cleanup Check

Run date: 2026-05-27. Both rows used direct deterministic
`camera-grounded-labels`,
`generated_mess_count=10`, real MolmoSpaces/RBY1M robot views, and the
recommended DINO base-recall sidecar config. Scene 0 used the prebuilt
`assets/maps/molmospaces-procthor-val-0-7` bundle; scene 2 intentionally did
not claim Nav2 bundle coverage because this repo currently only has the scene 0
MolmoSpaces map bundle.

| Scene | Pipeline config | Model-declared candidates | Cleanup chains | Exact private matches | Advisory summary | Sweep coverage | Status |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| `procthor-10k-val:0` | DINO base recall | 86 | 10 | 8/10 | 8 exact + 2 benign semantic disagreements | 1.0 | Success |
| `procthor-10k-val:2` | DINO base recall | 104 | 7 | 4/10 | 4 exact + 3 benign + 3 wrong placements | 1.0 | Partial success |

Interpretation: the selected detector improves isolated localization enough to
recommend it as the default, but cleanup quality is still scene-sensitive.
Scene 2 shows the next bottleneck: the cleanup selection/destination heuristic
can act on high-recall noisy labels and choose semantically wrong placements
for pillows/remotes. The scene 2 strict robot-view checker also flagged one
held-object FPV focus frame during fridge opening as weak visibility; the run
itself is valid partial cleanup evidence, but that report has a review-view
gap for one open-receptacle step.

Artifacts:

- `output/molmo/direct-camera-labels-dino-base-recall-scene0-0527/seed-7/report.html`
- `output/molmo/direct-camera-labels-dino-base-recall-scene2-0527/seed-7/report.html`

## End-To-End Cleanup Results

All rows below use seed 7 and the MolmoSpaces camera-grounded-labels cleanup path unless
noted.

| Run | Pipeline | Candidates | Declares | Cleaned handles | Exact private matches | Sweep coverage | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Direct control | `sim` | 13 | n/a | 10 | 8/10 | 1.0 | Passed |
| Direct fake transport | `fake-http` | 14 | 14 | 2 | 2/10 | 1.0 | Partial success |
| MCP smoke fake transport | `fake-http` | 14 | 14 | 2 | 2/10 | 1.0 | Partial success |
| Direct proposer-only | `grounding-dino` | 20 | n/a | 4 | 3/10 | 1.0 | Passed |
| MCP smoke proposer-only | `grounding-dino` | 20 | 14 | 4 | 3/10 | 1.0 | Passed |
| Live Codex proposer-only | `grounding-dino` | 24 | 16 | 4 | 3/10 | 1.0 | Partial success |
| Live Codex proposer+refiner | `grounding-dino+vertex_ai/gemini-3-flash-preview` | 36 | 16 | 12 | 5/10 | 1.0 | Partial success |
| Direct proposer+refiner, default timeout | `grounding-dino+mimo-v2-omni` | 0 | 14 | 0 | 0/10 | 1.0 | Failed usefully |
| Direct proposer+refiner, 240s timeout | `grounding-dino+mimo-v2-omni` | 17 | 14 | 7 | 5/10 | 1.0 | Partial success |
| Direct proposer+refiner | `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | 3 | 14 | 1 | 0/10 | 1.0 | Failed |
| Direct proposer+refiner | `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | 19 | 14 | 8 | 6/10 | 1.0 | Partial success |
| Direct proposer+refiner | `grounding-dino+vertex_ai/gemini-3-flash-preview` | 30 | 14 | 10 | 8/10 | 1.0 | Passed |

Refiner cleanup telemetry:

| Pipeline | Refiner calls | Avg refiner latency | Total refiner tokens | Avg proposer latency |
| --- | ---: | ---: | ---: | ---: |
| `grounding-dino+mimo-v2-omni`, default timeout | 0 | n/a | n/a | n/a |
| `grounding-dino+mimo-v2-omni`, 240s timeout | 14 | 30934ms | 68080 | 4334ms |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | 14 | 8311ms | 32601 | 4518ms |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | 14 | 9104ms | 46713 | 4277ms |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | 14 | 19815ms | 78282 | 4284ms |
| Live Codex `grounding-dino+vertex_ai/gemini-3-flash-preview` | 16 | 23950ms | 103282 | 4290ms |

Refiner decision summary:

| Default candidate | Use when | Avoid when |
| --- | --- | --- |
| `grounding-dino` | Need the current stable default with known direct/MCP/Codex cleanup evidence. | Need maximum cleanup quality and can pay VLM-refiner latency. |
| `grounding-dino+vertex_ai/gemini-3-flash-preview` | Need best tested cleanup quality: 10 cleaned handles and 8/10 exact matches. | Need predictable runtime or low token use. |
| `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview` | Need a cheaper Gemini refiner with partial-success E2E behavior. | Need the best exact-match rate. |
| `grounding-dino+mimo-v2-omni` | Need a MiMo baseline or provider diversity comparison. | Running with default timeout, or choosing the strongest current refiner. |
| `grounding-dino+siliconflow/Qwen/Qwen3-VL-8B-Instruct` | Need a conservative Qwen comparison route. | Running cleanup E2E; it over-rejected and failed this seed. |

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
- `output/molmo/apple2apple-0526-codex-dino-gemini3flash-autocontinue-timeout240/0526_1513/seed-7/report.html`

## Interpretation

`grounding-dino` is the current default real pipeline because it is the best
proposer-only option on recall and overall score, and it already has direct,
MCP smoke, and live Codex cleanup evidence.

Benchmark-design conclusion: use two separate gates. The bbox benchmark is the
right model-selection gate because it is automated, samples fresh MolmoSpaces
scene indices and target-focused FPV frames, and scores IoU against private
MuJoCo segmentation boxes. The live cleanup apple-to-apple table is the
right agent-behavior gate because it controls the task, seed, map, and prompt
while changing the evidence lane. A single scene-0 live cleanup run should not
be treated as a product-level model ranking. For the next representative pass,
generate a fresh bbox corpus with about 10 scene indices x 10 targets and then
run a smaller same-matrix cleanup subset across multiple scene categories.

`yoloe` is now a credible ultra-fast lane, not just a placeholder. Expanding
cleanup-family hints improved recall from 0.04878 to 0.121951, and the best
tested speed config reached 0.146341 recall at 368.821ms average latency. That
is still below Grounding DINO's recall and score, so YOLOE should not be the
default. It is useful for low-latency sweeps, for future navigation-time
perception, and as a proposer to revisit after we add better object hints or
visual-prompt reference boxes.

For hosted VLM refine, the end-to-end check overrides the perception-only
ranking. `grounding-dino+vertex_ai/gemini-3-flash-preview` is the best direct
quality refiner in the Gemini/Qwen set: it cleaned 10 observed handles and
reached 8/10 exact private matches. The tradeoff is cost and latency: 14 direct
refiner calls averaged 19.8s and reported 78k total refiner tokens. Use it only
when quality matters more than runtime. `grounding-dino+vertex_ai/gemini-3.1-flash-lite-preview`
is the cheaper Gemini lane: 8 cleaned handles, 6/10 exact private matches, and
9.1s average refiner latency. Qwen 8B should not be the default refiner for this
cleanup loop; it looked precise in the isolated benchmark but over-rejected in
E2E, producing only 3 candidates, 1 cleaned handle, and 0/10 exact private
matches.

The live Codex + DINO + Gemini run did not inherit the direct refiner win. It
cleaned 12 public handles, but only 5/10 exact private matches, with 9/10
semantic accepted. It also took 20m47s because Codex kept declaring after
post-placement observations. That makes it useful evidence for real-robot-like
Codex/MCP behavior, but not the default live-agent perception setting.

The historical `grounding-dino+mimo-v2-omni` run remains useful MiMo comparison
evidence. It improved the end-to-end cleanup run from 4 cleaned handles / 3
exact private matches to 7 cleaned handles / 5 exact private matches, but only
after increasing `VISUAL_GROUNDING_TIMEOUT_S` to 240 seconds. With the default
20 second timeout, it produced visible timeout failures and zero fabricated
simulator labels, which is the correct failure mode but not a usable default.
After the Gemini/Qwen refiner checks, MiMo was not the strongest hosted refiner
candidate on this seed: Gemini 3.1 flash-lite and Gemini 3-flash both cleaned
more handles and hit more exact private matches. New MiMo comparison runs should
use the active `mimo-v2.5` pipeline ids.

The historical `mimo-v2-omni-direct` run has promising benchmark evidence but
still needs an end-to-end cleanup run on the active `mimo-v2.5-direct` route
before a direct MiMo lane can be promoted. The old internal aggregation route
model id `xiaomi/mimo-v2-omni` did not improve on the token-plan MiMo route in
this benchmark: it had lower recall, similar precision, higher latency, and 4
read timeouts. New aggregation-route MiMo checks should use `xiaomi/mimo-v2.5`.

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

- run a same-matrix end-to-end cleanup report for `mimo-v2.5-direct`;
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
