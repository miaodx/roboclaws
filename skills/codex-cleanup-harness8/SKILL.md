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
direct-world-labels
direct-world-labels-sanitized
direct-camera-labels-grounding-dino
direct-camera-raw
dino-prior-world-labels
dino-prior-world-labels-sanitized
dino-prior-camera-labels-grounding-dino
dino-prior-camera-raw
```

The prior rows first build:

```bash
just task::run semantic-map-build direct camera-labels \
  seed=7 generated_mess_count=10 visual_grounding=grounding-dino
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
  row=direct-world-labels
```

Run a focused subset:

```bash
just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/0603_refactor_check \
  row=dino-prior-world-labels,dino-prior-camera-labels-grounding-dino
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
- per-row `report.html`

For source and skill changes, a practical pass means no obvious regression in
semantic accepted count, sweep coverage, disturbance count, or DINO service
health. A `strict_checker_failed` row with `behavior_status=success` is still
useful evidence; inspect the checker reason before treating it as cleanup
behavior regression.
