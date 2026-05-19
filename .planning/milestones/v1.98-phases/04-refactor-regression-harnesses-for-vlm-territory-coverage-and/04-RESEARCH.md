---
phase: "04"
kind: "research"
date: "2026-04-23"
status: "Complete"
---

# Phase 4 — Research

## Question

What do we need to know to plan refactor-regression harnesses for this repo
without building a parallel execution stack, over-freezing unstable outputs, or
blurring the cloud/local split?

## Current Runtime Facts

### 1. The repo already has the right capture/analyze pattern in miniature

- `examples/view_experiment.py` appends one JSONL row per run, keeps per-run
  replay dirs, and uses a simple `GAME_RUNNERS` registry that tests
  monkeypatch directly.
- `scripts/analyze_view_experiment.py` is intentionally separate from capture.
  It loads rows, pairs variants by stable coords, and emits markdown instead of
  folding analysis into the runner.

Planning implication: Phase 4 should generalize this pattern, not replace it
with one monolithic harness.

### 2. The public runners already expose structured results worth diffing

- `examples/single_agent_explore.py` returns `cells_visited`,
  `termination_reason`, `vlm_cost_usd`, and `provider_status`.
- `examples/territory_game.py` returns `cells_claimed`, `blocking_events`,
  `termination_reason`, `vlm_cost_usd`, and `provider_status`.
- `examples/coverage_game.py` returns `cells_covered`, `coverage_pct`,
  `work_balance`, `termination_reason`, `vlm_cost_usd`, and `provider_status`.
- `examples/openclaw_demo.py` returns `steps_executed`,
  `termination_reason`, and `provider_status`; `visited_cells` is available in
  the per-step `game_state` written into `replay.json`, not in the direct
  return dict.
- `examples/openclaw_nav_autonomous.py` writes `run_result.json`, and then
  `scripts/render_autonomous_replay.py` derives `summary.json` with tool
  counts, transcript source, unseen-frame counts, and termination mode.

Planning implication: compare structured outputs and replay summaries; do not
diff raw reasoning text.

### 3. Exact-contract seams already exist and should be frozen, not reinvented

- `roboclaws/core/views.py` currently exposes one supported prompt bundle and a
  stable image-label order: `("fpv", "map_v2", "chase")`.
- `roboclaws/core/replay.py` writes a stable `replay.json` shape with
  `metadata`, `summary`, and per-step records.
- `tests/fixtures/trace_schema_reference.json` already freezes the
  additive-vs-exact contract for OpenClaw trace payloads and
  `snapshot_metrics`.
- Existing tests already pin key invariants such as OpenClaw demo default
  step/stale behavior, autonomous `run_result.json` fields, and
  territory/coverage termination semantics.

Planning implication: Phase 4 should add a small contract-fixture layer where
gaps remain, while explicitly reusing the existing tests as part of the safety
wall.

### 4. Cloud-safe mocked runs already have a pattern

- `scripts/generate_demo_report.py` patches the engine, reuses existing example
  runners, and writes replay/report artifacts without Unity or a live provider.
- `roboclaws.core.reporter.compare()` already provides side-by-side HTML for
  two replay dirs, which is useful as an operator-facing drill-down but not
  enough as a machine gate.

Planning implication: the new harness can rely on mocked/canned seams in tests
and CI for plumbing proof, while keeping real-VLM and real-Gateway behavioral
claims local only.

### 5. OpenClaw has two distinct regression surfaces

- Push-model OpenClaw: `openclaw_demo.py` and
  `territory_game.py` / `coverage_game.py --backend openclaw`
- Autonomous MCP OpenClaw: `openclaw_nav_autonomous.py` +
  `run_result.json` + `summary.json` + `trace.jsonl`

The schemas and failure modes are different. The autonomous path cares about
`terminated_by`, `transcript_source`, `tool_calls_by_type`,
`frames_unseen_by_agent`, and `decision_modes`; the push-model path looks more
like the direct-VLM examples plus Gateway transport health.

Planning implication: Phase 4 should use one comparison vocabulary but
recognize separate suite extractors.

### 6. The cloud/local split is load-bearing

- `AGENTS.md` and `CLAUDE.md` explicitly forbid cloud sessions from claiming
  real Kimi / real Gateway / real AI2-THOR validation.
- Phase 4 can build the harnesses and synthetic tests in cloud, but any "did
  behavior stay within tolerance on the real stack?" claim remains local-dev
  only.

Planning implication: local-only suites need a hard guardrail and a doc path
for baseline refreshes; the harness must not silently fake them in CI.

## Candidate Implementation Paths

### Option A — One giant end-to-end regression script

Rejected.

Why:

- violates the phase context's "do not build one fat harness" decision
- mixes execution, row extraction, threshold policy, and reporting into one
  hard-to-test surface
- makes local-only OpenClaw concerns infect cloud-safe VLM flows

### Option B — Shared suite/row helpers plus one capture CLI and one compare CLI

Preferred.

Shape:

- small shared module for suite registry, stable coordinate keys, JSONL
  helpers, and row normalization
- `scripts/capture_refactor_regression.py` drives existing runners and writes
  append-only rows plus replay dirs
- `scripts/analyze_refactor_regression.py` compares baseline vs candidate rows
  using suite-specific thresholds

Why it fits the repo:

- matches `view_experiment.py` + `analyze_view_experiment.py`
- keeps tests monkeypatchable
- keeps OpenClaw local-only suites behind explicit gates
- avoids duplicate execution loops

### Option C — Exact equality on real-model behavior

Rejected.

Why:

- real VLM and live Gateway runs are not step-deterministic enough for exact
  replay equality
- the repo already learned this lesson in Phase 2.4 by using paired stats
  instead of frame-by-frame equality

Exact equality belongs only to committed fixtures and cloud-safe deterministic
surfaces. Real behavior needs threshold gates.

## Recommended Phase-4 Shape

### Shared capture row model

Every row should include stable pairing coordinates:

- `suite`
- `backend`
- `scene`
- `seed`
- `game`
- `model`
- `agents`
- `variant` when applicable

Plus common run outcome fields:

- `label` as an immutable capture-set name such as `baseline-2026-04-23` or
  `candidate-dongxu-dev-0423`
- `run_id`
- `captured_at`
- `commit_sha`
- `schema_version`
- `status`
- `termination_reason` or `terminated_by`
- `usd`
- `wallclock_seconds`
- `artifact_dir`
- `provider_status` or equivalent transport summary

Suite-specific metrics ride on top:

- `cells_visited`
- `cells_claimed_total`
- `blocking_events`
- `coverage_fraction`
- `work_balance`
- `tool_calls_by_type`
- `transcript_source`
- `frames_unseen_by_agent`
- `decision_modes`

### Recommended suite set

The minimum useful split is:

- `explore-vlm`
- `territory-vlm`
- `coverage-vlm`
- `openclaw-demo`
- `territory-openclaw`
- `coverage-openclaw`
- `openclaw-autonomous`

This mirrors the real user-facing paths instead of inventing harness-only
pseudo-runners.

### Recommended output layout

Use immutable capture-set labels, keep rows append-only, and give every capture
a unique per-run artifact directory even when the stable coordinates are
identical. The operator still thinks in terms of baseline vs candidate, but the
actual `--label` value should be a snapshot name, not a mutable bucket:

```text
output/refactor-regression/
  baseline-2026-04-23/
    results.jsonl
    <suite>/<scene>-seed<N>/<run-id>/
  candidate-dongxu-dev-0423/
    results.jsonl
    <suite>/<scene>-seed<N>/<run-id>/
```

For autonomous OpenClaw, the per-run dir should continue to own `trace.jsonl`,
`run_result.json`, `summary.json`, `replay.gif`, and `report.html`; the
harness records both the stable pairing coordinates and the unique artifact path.

## Recommended Threshold Model

One global threshold is the wrong shape. Use a suite policy table.

### Exact-contract surfaces

Use exact equality or required-key checks for:

- prompt image label order/count
- `replay.json` required summary keys
- OpenClaw trace required top-level keys
- `snapshot_metrics` exact key set
- transport/runtime defaults already frozen in existing tests

### Behavioral suites

Recommended first-pass thresholds:

- `explore-vlm`
  - visited cells: no worse than `-1` absolute vs baseline
  - cost: no more than `+25%`
  - wallclock: no more than `+50%`
- `openclaw-demo`
  - visited cells from the final replay step state: no worse than `-1`
  - replay-summary cost (when present): no more than `+25%`
  - wallclock: no more than `+50%`
- `territory-*`
  - total claimed cells: no worse than `-2` absolute
  - blocking events: no worse than `+2`
  - no new `provider_error` / `provider_unstable` termination mode
- `coverage-*`
  - coverage fraction: no worse than `-0.05`
  - work balance: no worse than `-0.10`
  - steps-to-termination: no worse than `+20%`
- `openclaw-autonomous`
  - `transcript_source`: exact
  - `tool_calls_by_type` counts: within `±2` per tool family
  - `frames_unseen_by_agent`: no worse than `+2`
  - no regression from a successful `done`/`wall_clock` baseline into
    `error`/startup failure

The exact numeric table should live in code so it is reviewable and testable.

## Validation Implications

### Automated

Phase 4 should add focused tests for:

- contract fixtures and schema/key-set enforcement
- capture-suite registry and JSONL row writing
- row extraction from synthetic replay/autonomous artifacts
- compare/analyze threshold logic on synthetic baseline/candidate JSONL files

### Local-only

Phase 4 still needs one real baseline-refresh proof:

- at least one real direct-VLM capture using a stable model
- at least one real OpenClaw push-model capture
- at least one real OpenClaw autonomous capture
- operator notes recording commands, artifact dirs, and any threshold
  adjustments justified by live data

## Concrete Planning Implications

1. Plan 01 should freeze the exact contracts and add the shared suite/row
   scaffolding.
2. Plan 02 should wire direct-VLM and territory/coverage suites into the
   capture harness.
3. Plan 03 should extend the same harness to OpenClaw push-model and
   autonomous suites without weakening the local-only guardrail.
4. Plan 04 should add the baseline-vs-candidate analyzer, operator docs, and
   the initial local baseline refresh/write-up.

---
*Phase: 04-refactor-regression-harnesses-for-vlm-territory-coverage-and*
*Research completed: 2026-04-23*
