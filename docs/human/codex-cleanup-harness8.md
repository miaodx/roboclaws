# Codex Cleanup Harness 8

This harness is the standard live Codex regression set for household cleanup
source changes and cleanup-skill changes.

Use it when a change can affect agent behavior, cleanup prompts, MCP recovery,
public/private cleanup boundaries, evidence lanes, semantic-map priors, or
report scoring. It intentionally stays smaller than the older apple-to-apple
grid: one Codex route, four evidence lanes, with and without a Runtime Metric
Map prior.

## Cases

The eight cleanup rows are:

| Row | Cleanup input | Runtime map prior |
| --- | --- | --- |
| `direct-world-oracle-labels` | `world-oracle-labels` | none |
| `direct-world-public-labels` | `world-public-labels` | none |
| `direct-camera-grounded-labels-grounding-dino` | `camera-grounded-labels`, `camera_labeler=grounding-dino` | none |
| `direct-camera-raw-fpv` | `camera-raw-fpv` | none |
| `dino-prior-world-oracle-labels` | `world-oracle-labels` | DINO semantic-map-build prior |
| `dino-prior-world-public-labels` | `world-public-labels` | DINO semantic-map-build prior |
| `dino-prior-camera-grounded-labels-grounding-dino` | `camera-grounded-labels`, `camera_labeler=grounding-dino` | DINO semantic-map-build prior |
| `dino-prior-camera-raw-fpv` | `camera-raw-fpv` | DINO semantic-map-build prior |

The setup row builds the prior once with:

```bash
just task::run semantic-map-build direct evidence_lane=camera-grounded-labels \
  seed=7 generated_mess_count=10 camera_labeler=grounding-dino
```

## Preflight

On the work network, Codex defaults to the repo-local `codex-env` route. The
mify route is allowed only when `ROBOCLAWS_CODEX_PROVIDER=mify` is set
explicitly. Check this first:

```bash
just dev::network-status
set -a && source .env && set +a
python - <<'PY'
import os
provider = os.environ.get("ROBOCLAWS_CODEX_PROVIDER") or "codex-env"
if provider == "mify":
    assert os.environ.get("XM_LLM_API_KEY"), "mify requires XM_LLM_API_KEY"
else:
    assert os.environ.get("CODEX_API_KEY") and os.environ.get("CODEX_BASE_URL"), (
        "codex-env requires CODEX_BASE_URL and CODEX_API_KEY"
    )
PY
```

For the DINO rows, the harness manages the real Grounding DINO sidecar by
default:

- if a healthy real sidecar already answers at `VISUAL_GROUNDING_BASE_URL` or
  `http://127.0.0.1:18880`, it is reused and left running;
- if no sidecar is reachable, the harness starts one from
  `.venv-visual-grounding/bin/python` or `ROBOCLAWS_VISUAL_GROUNDING_PYTHON` and
  stops only that process when the harness exits;
- if the port is already bound by an unhealthy or non-DINO service, DINO rows are
  marked as infrastructure failure instead of killing the unknown process.

The harness-owned process uses the recommended DINO base configuration:

```bash
VISUAL_GROUNDING_DEVICE=auto \
VISUAL_GROUNDING_TORCH_DTYPE=auto \
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base \
VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 \
VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 \
  .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline real-router --adapter-mode real
```

Use `dino_sidecar_lifecycle=reuse-only` when you want the run to require an
already-running sidecar. Use `dino_sidecar_lifecycle=off` only for debugging the
old unmanaged behavior. Do not replace real DINO with `contract-fake` for
performance-regression evidence.

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

Opt into two local visual backend slots for batch development:

```bash
ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2 \
  just agent::harness codex-cleanup-harness8 execute \
    output_dir=output/molmo/codex-harness8/$(date +%m%d_%H%M) \
    parallelism=2
```

`parallelism=2` keeps the setup prior row serialized, assigns distinct MCP
ports to cleanup rows, and records row start/end timing, assigned port, and
harness parallelism in `codex_cleanup_harness8.json`.

Explicit retryable provider-transient failures from the live runner are treated
as infrastructure failures and retried once by default. For a noisier provider
window, raise the provider retry budget without changing cleanup behavior:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  provider_retry_attempts=2 provider_retry_sleep_s=90
```

Execute one row:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  row=direct-world-public-labels
```

Execute a focused subset:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  row=dino-prior-world-oracle-labels,dino-prior-camera-grounded-labels-grounding-dino
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
- retry count / provider-transient evidence
- report link

For source and skill changes, compare against the most recent accepted harness
run. Treat these as regression triggers:

- sweep coverage below `1.0`;
- disturbance count above `0`;
- semantic accepted count dropping by more than one object in a structured lane;
- `world-public-labels` falling back to repeated `done`/held loops;
- DINO rows failing due to service, timeout, or declaration contract errors;
- large wall-time increases not explained by provider transient failures or sidecar
  latency.

Rows with `behavior_status=infra_failure` did not produce clean behavioral
evidence. `status=provider_transient_failed` means the live runner reported
`reason=provider_transient_failure` with a `provider_reason` such as
`rate_limit`, `upstream_unavailable`, or `upstream_timeout`, and the harness
exhausted the configured retry budget. `status=infra_failed` means an external
dependency such as the Grounding DINO sidecar failed or timed out. Rerun those
rows after the provider or sidecar is healthy before drawing cleanup-regression
conclusions.

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
