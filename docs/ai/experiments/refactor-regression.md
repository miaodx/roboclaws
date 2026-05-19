# Refactor Regression Harness

## What this harness protects

This workflow exists to make large refactors safer across the repo paths that
matter in practice:

- direct VLM exploration
- territory / coverage game behavior
- OpenClaw push-model runs
- OpenClaw autonomous MCP runs

It does that in two layers:

- exact contracts stay frozen in committed fixtures and focused tests
- behavioral comparisons happen through append-only capture sets plus a
  baseline-vs-candidate analyzer

## Capture a baseline

Use an immutable capture-set label. Do not reuse a permanent bucket like
`baseline`; use a dated name such as `baseline-2026-04-23`.

```bash
python scripts/regression/capture_refactor_regression.py \
  --suite explore-vlm,territory-vlm,coverage-vlm \
  --label baseline-2026-04-23 \
  --scenes FloorPlan201 \
  --seeds 1,2 \
  --agents 2 \
  --steps 20 \
  --model mock
```

Artifacts land under:

```text
output/refactor-regression/<label>/
  results.jsonl
  <suite>/<scene>-seed<N>/<run-id>/
```

Each run gets a unique `artifact_dir` even when the stable coordinate tuple is
the same.

## Capture a candidate

Run the same coordinates with a different immutable label.

```bash
python scripts/regression/capture_refactor_regression.py \
  --suite explore-vlm,territory-vlm,coverage-vlm \
  --label candidate-dongxu-dev-0423 \
  --scenes FloorPlan201 \
  --seeds 1,2 \
  --agents 2 \
  --steps 20 \
  --model mock
```

For local-only suites, add `--allow-local` only in a real workstation session
that satisfies the repo preflight.

## Compare them

```bash
python scripts/regression/analyze_refactor_regression.py \
  --baseline output/refactor-regression/baseline-2026-04-23/results.jsonl \
  --candidate output/refactor-regression/candidate-dongxu-dev-0423/results.jsonl
```

By default the analyzer writes:

- `output/refactor-regression/<candidate-label>/analysis/summary.md`
- `output/refactor-regression/<candidate-label>/analysis/summary.json`

It exits non-zero on missing pairs or threshold breaches.

## Local-only suites

These suites are intentionally guarded and require `--allow-local`:

- `openclaw-demo`
- `territory-openclaw`
- `coverage-openclaw`
- `openclaw-autonomous`

That guard is load-bearing. The repo’s cloud/local split in `AGENTS.md` and
`CLAUDE.md` is explicit: cloud-safe sessions can build and test the harness,
but real Gateway / AI2-THOR / provider behavior must be refreshed on a local
workstation. Follow [`docs/human/openclaw/local.md`](../../human/openclaw/local.md) and the preflight
steps in `AGENTS.md §1` before capturing those suites.

## Evidence

The first real baseline-refresh evidence for this phase belongs in
[04-LOCAL-PROBE-RESULTS](../../../.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md).
