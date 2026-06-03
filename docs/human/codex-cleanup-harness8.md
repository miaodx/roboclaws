# Codex Cleanup Harness 8

This harness is the standard live Codex regression set for household cleanup
source changes and cleanup-skill changes.

Use it when a change can affect agent behavior, cleanup prompts, MCP recovery,
public/private cleanup boundaries, perception lanes, semantic-map priors, or
report scoring. It intentionally stays smaller than the older apple-to-apple
grid: one Codex route, four evidence lanes, with and without a Runtime Metric
Map prior.

## Cases

The eight cleanup rows are:

| Row | Cleanup input | Runtime map prior |
| --- | --- | --- |
| `direct-world-labels` | `world-labels` | none |
| `direct-world-labels-sanitized` | `world-labels-sanitized` | none |
| `direct-camera-labels-grounding-dino` | `camera-labels`, `visual_grounding=grounding-dino` | none |
| `direct-camera-raw` | `camera-raw` | none |
| `dino-prior-world-labels` | `world-labels` | DINO semantic-map-build prior |
| `dino-prior-world-labels-sanitized` | `world-labels-sanitized` | DINO semantic-map-build prior |
| `dino-prior-camera-labels-grounding-dino` | `camera-labels`, `visual_grounding=grounding-dino` | DINO semantic-map-build prior |
| `dino-prior-camera-raw` | `camera-raw` | DINO semantic-map-build prior |

The setup row builds the prior once with:

```bash
just task::run semantic-map-build direct camera-labels \
  seed=7 generated_mess_count=10 visual_grounding=grounding-dino
```

## Preflight

On the work network, Codex is allowed only through a repo-local mify or
codex-env route. Check this first:

```bash
just dev::network-status
set -a && source .env && set +a
python - <<'PY'
import os
assert os.environ.get("XM_LLM_API_KEY") or (
    os.environ.get("CODEX_API_KEY") and os.environ.get("CODEX_BASE_URL")
), "No Codex provider route configured"
PY
```

For the DINO rows, start the visual-grounding sidecar in another terminal:

```bash
VISUAL_GROUNDING_DEVICE=auto \
VISUAL_GROUNDING_TORCH_DTYPE=auto \
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base \
VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 \
VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 \
  .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline real-router --adapter-mode real
```

If the sidecar is intentionally not available, use dry-run only. Do not replace
real DINO with `contract-fake` for performance-regression evidence.

## Trigger

Dry-run the manifest and report:

```bash
just agent::harness codex-cleanup-harness8 dry-run \
  output_dir=output/molmo/codex-harness8/$(date +%m%d_%H%M)
```

Execute all eight rows, continuing after row failures:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/$(date +%m%d_%H%M)
```

Provider `429 Too Many Requests` / rate-limit failures are treated as
infrastructure failures and are retried once by default. For a noisier provider
window, raise the retry budget without changing cleanup behavior:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  rate_limit_retries=2 rate_limit_retry_sleep_s=90
```

Execute one row:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  row=direct-world-labels-sanitized
```

Execute a focused subset:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  row=dino-prior-world-labels,dino-prior-camera-labels-grounding-dino
```

Use an already-built prior:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  runtime_map_prior=output/.../runtime_metric_map.json
```

The harness writes:

- `codex_cleanup_harness8.json`
- `codex_cleanup_harness8.html`
- per-row `report.html`
- per-row `run_result.json`

## Review

The minimum review fields are:

- `behavior_status`
- strict checker status / `strict_exit_status`
- `completion_status`
- exact/private restored count
- semantic accepted count
- sweep coverage
- disturbance count
- unrecovered semantic-order error count
- wall time and tool-call count
- retry count / rate-limit evidence
- report link

For source and skill changes, compare against the most recent accepted harness
run. Treat these as regression triggers:

- sweep coverage below `1.0`;
- disturbance count above `0`;
- semantic accepted count dropping by more than one object in a structured lane;
- `world-labels-sanitized` falling back to repeated `done`/held loops;
- DINO rows failing due to service, timeout, or declaration contract errors;
- large wall-time increases not explained by provider rate limits or sidecar
  latency.

Rows with `status=rate_limited` and `behavior_status=infra_failure` did not
produce behavioral evidence after the configured retry budget. Rerun those rows
before drawing cleanup-regression conclusions.

Exact/private restore is useful evidence, but it is not the primary objective
for sanitized public-policy cleanup. Use semantic accepted, sweep coverage, and
disturbance as the main stability indicators.

Rows can report `strict_checker_failed` while still carrying
`behavior_status=success`. That means `run_result.json` says the agent completed
the cleanup, but the stricter checker rejected an auxiliary invariant such as
semantic order. Inspect the checker reason before treating that row as behavior
regression.

## Relationship To Other Grids

`just molmo::apple2apple-grid` is broader: it compares online/offline map modes
across Codex and Claude routes for Grounding DINO and RAW_FPV lanes.

This harness is narrower and should be the default repeated optimization loop
for Codex cleanup source and skill implementation changes.
