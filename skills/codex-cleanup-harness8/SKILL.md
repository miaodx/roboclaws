---
name: codex-cleanup-harness8
description: Run and review the eight-case live Codex household-cleanup regression harness.
---

# Codex Cleanup Harness 8

Use this skill when a source change or cleanup-skill change may affect live
Codex household cleanup behavior. This is a harness skill, not a cleanup
strategy skill: do not add task heuristics here. Keep behavior guidance in
`skills/molmo-realworld-cleanup/`.

## Cases

The grid is one Codex route over four evidence lanes, run both directly and
with a DINO semantic-map prior:

```text
direct-world-oracle-labels
direct-world-public-labels
direct-camera-grounded-labels-grounding-dino
direct-camera-raw-fpv
dino-prior-world-oracle-labels
dino-prior-world-public-labels
dino-prior-camera-grounded-labels-grounding-dino
dino-prior-camera-raw-fpv
```

The prior rows first build:

```bash
just task::run semantic-map-build direct evidence_lane=camera-grounded-labels \
  seed=7 generated_mess_count=10 camera_labeler=grounding-dino
```

## Preflight

Read `docs/human/codex-cleanup-harness8.md` before a live sweep. On the work
network, Codex must use a repo-local mify or Codex env route. DINO rows require
the real visual-grounding sidecar; do not use fake grounding as regression
evidence.

## Commands

Dry-run the manifest:

```bash
just agent::harness codex-cleanup-harness8 dry-run \
  output_dir=output/molmo/codex-harness8/$(date +%m%d_%H%M)
```

Run one row:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  row=direct-world-oracle-labels
```

Run a focused subset:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  row=dino-prior-world-oracle-labels,dino-prior-camera-grounded-labels-grounding-dino
```

Explicit retryable provider-transient failures from the live runner are retried
once by default. During a noisy provider window, use:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  provider_retry_attempts=2 provider_retry_sleep_s=90
```

Run the full grid:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/$(date +%m%d_%H%M)
```

Use an existing prior:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  runtime_map_prior=output/.../runtime_metric_map.json
```

## Review

Use `codex_cleanup_harness8.html` and `codex_cleanup_harness8.json` as the
summary. Review behavior metrics separately from strict checker exit status:

- `behavior_status`
- exact/private restored count
- semantic accepted count
- sweep coverage
- disturbance count
- unrecovered semantic-order errors
- wall time and tool-call count
- retry count / provider-transient evidence
- per-row `report.html`

For source and skill changes, a practical pass means no obvious regression in
semantic accepted count, sweep coverage, disturbance count, or DINO service
health. A `strict_checker_failed` row with `behavior_status=success` is still
useful evidence; inspect the checker reason before treating it as cleanup
behavior regression.

A row with `behavior_status=infra_failure` is not cleanup behavior evidence.
`provider_transient_failed` means the live runner reported
`reason=provider_transient_failure` with a `provider_reason` such as
`rate_limit`, `upstream_unavailable`, or `upstream_timeout`, and the harness
exhausted the configured retry budget. `infra_failed` means an external
dependency such as the Grounding DINO sidecar failed or timed out. Rerun it
before comparing direct vs DINO-prior behavior.
