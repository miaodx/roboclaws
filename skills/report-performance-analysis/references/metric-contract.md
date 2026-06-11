# Report Performance Metric Contract

The source of truth is `roboclaws_report_performance_metrics_v1`, produced by
`roboclaws.reports.live_performance`.

## Packet Sections

- `run_identity`: surface, intent, task name, agent engine, provider profile,
  model, evidence lane, seed, and profile id.
- `quality`: checker state, terminal state, cleanup/completion status, restored
  counts, restoration and sweep rates, disturbances, semantic accepted count,
  and failed/no-op tool count.
- `call_counts`: model calls, agent attempts, continuations, MCP tool calls,
  per-tool counts, and non-tool turns when available.
- `model_work`: input, cached input, uncached input, output, reasoning, image
  counts/pixels, percentiles, and explicit unavailable metrics.
- `timing`: observed wall time, runner agent time, MCP time, between-tool gap,
  tool handler time, robot-view capture time, observed model API time,
  estimated model work, residual latency, and non-model time.

## Per-Call Rows

`model_call_metrics.jsonl` uses `roboclaws_model_call_metric_v1`.

Allowed row fields are sanitized counts, timing, source, status, failure class,
and limitations. Do not add raw prompts, model text, function inputs/outputs,
full tool payload bodies, credentials, private evaluator truth, or compact
continuation packets.

## Speed Claim Boundary

A single run is diagnostic only. A speedup claim needs:

- explicit baseline or comparison manifest;
- same-or-better quality, or a recorded waiver;
- comparable run identity, or a diagnostic apples-to-oranges label;
- repeated rows or an explicit repeatability waiver for publishable claims;
- calibration metadata before treating normalized model time as authoritative.

When calibration coefficients are unavailable, report
`estimated_model_work_s.available=false` and keep residual latency diagnostic.
