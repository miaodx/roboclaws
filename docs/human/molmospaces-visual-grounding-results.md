# MolmoSpaces Visual Grounding Results

Last updated: 2026-05-26

This page records the current relative results for MolmoSpaces
`camera-labels` visual-grounding pipelines. It is the human-facing overview for
choosing a default pipeline and for appending future benchmark or cleanup runs.

## Current Recommendation

Use `visual_grounding=grounding-dino` as the default real visual-grounding
pipeline for `camera-labels` runs.

Keep `visual_grounding=sim` as the deterministic control baseline. Use
`grounding-dino+mimo-v2-omni` only as an opt-in quality comparison because it is
much slower and needs an explicit longer timeout. Keep `yoloe` as a latency
challenger, not the default, because current recall is too low. Keep
direct hosted VLM producers experimental until one has same-matrix end-to-end
cleanup evidence and materially better precision/recall than Grounding DINO.

## Selection Summary

| Pipeline | Current role | Why |
| --- | --- | --- |
| `sim` | Control baseline | Best controlled cleanup score, no real perception claim. |
| `grounding-dino` | Default real pipeline | Best proposer-only recall and best DINO-vs-YOLOE score on the current corpus. |
| `yoloe` | Speed experiment | Very low latency, but current recall is too low for cleanup default. |
| `grounding-dino+mimo-v2-omni` | Slow quality opt-in | Better precision and better cleanup actionability than DINO alone, but default 20s timeout fails. |
| `mimo-v2-omni-direct` | Experimental direct VLM | Token-plan route has the best direct-VLM benchmark score, but no same-matrix end-to-end cleanup report yet. |
| `xiaomi/mimo-v2-omni-direct` | Aggregation-route experiment | Works through the internal aggregation route, but was slower and less stable than the token-plan MiMo route. |
| `vertex_ai/gemini-3.1-flash-lite-preview-direct` | Fast hosted-VLM experiment | Fastest healthy provider-prefixed route, but current recall/precision are too low for default. |
| `vertex_ai/gemini-3-flash-preview-direct` | Hosted-VLM quality experiment | Slightly higher score than Gemini lite in one direct run, but much slower and noisy. |
| `siliconflow/Qwen/Qwen3-VL-8B-Instruct-direct` | Qwen fallback experiment | Healthy JSON/vision route, but current false-positive rate is too high. |
| `tongyi/qwen3-vl-*` variants | Blocked route experiment | Smoke calls returned incomplete JSON content, so they were not promoted to full corpus. |

## Perception Benchmark Results

All rows below use the same path-backed RAW_FPV benchmark corpus unless noted.
The current corpus has 28 observations. Recall and precision are against private
benchmark labels; those labels are scoring evidence and are not returned to the
cleanup agent.

| Pipeline | Candidates | Recall | Precision | Avg latency | Failure rate | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `grounding-dino` | 58 | 0.219512 | 0.155172 | 4685.857ms | 0.0 | Best proposer-only quality. |
| `yoloe` | 16 | 0.04878 | 0.125 | 95.679ms | 0.0 | Fast, but misses too many candidates. |
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
| `yoloe` | 0.170579 | Current proposer runner-up. |

Benchmark artifacts:

- `output/visual-grounding-benchmark/path-backed-grounding-dino-real-0525/`
- `output/visual-grounding-benchmark/path-backed-yoloe-real-0525/`
- `output/visual-grounding-benchmark/path-backed-proposer-real-comparison-0525/`
- `output/visual-grounding-benchmark/path-backed-grounding-dino-mimo-refiner-real-0525/`
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

Cleanup artifacts:

- `output/molmo/direct-camera-labels-sim-baseline/0525_2206/seed-7/report.html`
- `output/molmo/direct-camera-labels-fake-http/0525_2252/seed-7/report.html`
- `output/molmo/mcp-camera-labels-fake-http/0525_2253/seed-7/report.html`
- `output/molmo/direct-camera-labels/0525_2132/seed-7/report.html`
- `output/molmo/mcp-camera-labels-grounding-dino/0525_2141/seed-7/report.html`
- `output/molmo/codex-camera-labels-grounding-dino/0525_2216/seed-7/report.html`
- `output/molmo/direct-camera-labels-grounding-dino-mimo-refiner/0525_2145/seed-7/report.html`
- `output/molmo/direct-camera-labels-grounding-dino-mimo-refiner-240s/0525_2153/seed-7/report.html`

## Interpretation

`grounding-dino` is the current default real pipeline because it is the best
proposer-only option on recall and overall score, and it already has direct,
MCP smoke, and live Codex cleanup evidence.

`grounding-dino+mimo-v2-omni` is a useful quality reference. It improved the
end-to-end cleanup run from 4 cleaned handles / 3 exact private matches to 7
cleaned handles / 5 exact private matches, but only after increasing
`VISUAL_GROUNDING_TIMEOUT_S` to 240 seconds. With the default 20 second timeout,
it produced visible timeout failures and zero fabricated simulator labels, which
is the correct failure mode but not a usable default.

`yoloe` should stay in the matrix because it is much faster. It should not be
the default until recall improves on the same corpus or a new corpus shows a
different result.

`mimo-v2-omni-direct` has promising benchmark evidence but needs an end-to-end
cleanup run before it can be promoted. The internal aggregation route model id
`xiaomi/mimo-v2-omni` did not improve on the token-plan MiMo route in this
benchmark: it had lower recall, similar precision, higher latency, and 4 read
timeouts.

Gemini and SiliconFlow Qwen routes are useful as hosted-VLM comparison lanes,
not defaults. Gemini lite is the best latency challenger among the healthy
provider-prefixed routes, but its full-corpus precision/recall are too low.
SiliconFlow Qwen is route-healthy and fast enough to keep in the matrix, but it
produced too many false positives on the current corpus. Tongyi Qwen flash/plus
failed the smoke route with incomplete JSON output, so they should stay blocked
until the request or provider route is repaired.

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
- investigate the `tongyi/qwen3-vl-*` incomplete-JSON route failure;
- add fixed/custom YOLO only after weights, ontology, and licensing boundaries
  are reviewed;
- add a real Agibot G2 head-camera seed set before choosing a real deployed
  robot proposer;
- evaluate continuous route perception during navigation after waypoint
  observation grounding is stable.
