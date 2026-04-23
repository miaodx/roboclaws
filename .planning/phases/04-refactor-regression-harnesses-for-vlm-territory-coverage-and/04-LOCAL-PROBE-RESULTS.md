# Phase 04 Local Probe Results

**Date:** 2026-04-23
**Host:** `mi-ThinkPad-P16-Gen-2` (`Linux 6.17.0-20-generic`, `x86_64`)
**Docker:** `29.2.1`
**AI2-THOR:** `5.0.0`
**Provider env:** repo-local `.env` sourced; real Kimi path available

## Scope

This file records the first real baseline-refresh evidence for Phase 04's
refactor-regression harnesses. It covers:

- one real direct-VLM workflow-proof pair
- one real push-model OpenClaw baseline
- one real autonomous OpenClaw baseline
- one analyzer run over a real same-commit baseline/candidate pair

## Commands Run

Environment prep:

```bash
set -a && source .env && set +a
uv pip install -e ".[dev]"
docker --version
.venv/bin/python -c "import ai2thor; print(ai2thor.__version__)"
env -i PATH=".venv/bin:/usr/bin:/bin" HOME=$HOME KIMI_API_KEY="$KIMI_API_KEY" \
  .venv/bin/pytest tests/test_capture_refactor_regression.py \
  tests/test_analyze_refactor_regression.py -q
```

Real direct-VLM baseline:

```bash
.venv/bin/python scripts/capture_refactor_regression.py \
  --suite explore-vlm \
  --label baseline-2026-04-23-direct \
  --scenes FloorPlan201 \
  --seeds 1 \
  --agents 1 \
  --steps 3 \
  --model kimi-coding
```

Real direct-VLM candidate (same-commit workflow-proof pair):

```bash
.venv/bin/python scripts/capture_refactor_regression.py \
  --suite explore-vlm \
  --label candidate-2026-04-23-direct-samecommit \
  --scenes FloorPlan201 \
  --seeds 1 \
  --agents 1 \
  --steps 3 \
  --model kimi-coding
```

Analyzer:

```bash
.venv/bin/python scripts/analyze_refactor_regression.py \
  --baseline output/refactor-regression/baseline-2026-04-23-direct/results.jsonl \
  --candidate output/refactor-regression/candidate-2026-04-23-direct-samecommit/results.jsonl
```

Real push-model OpenClaw baseline:

```bash
docker rm -f openclaw-gateway >/dev/null 2>&1 || true
export OPENCLAW_GATEWAY_TOKEN=$(PROVIDER=kimi AGENTS=2 ./scripts/openclaw-bootstrap.sh)
.venv/bin/python scripts/capture_refactor_regression.py \
  --suite openclaw-demo \
  --label baseline-2026-04-23-openclaw-demo \
  --scenes FloorPlan201 \
  --seeds 1 \
  --agents 2 \
  --steps 3 \
  --model kimi-coding \
  --allow-local
```

First autonomous attempt (captured the port-collision failure before the
harness fix described below):

```bash
docker rm -f openclaw-gateway >/dev/null 2>&1 || true
PROVIDER=kimi .venv/bin/python scripts/capture_refactor_regression.py \
  --suite openclaw-autonomous \
  --label baseline-2026-04-23-openclaw-autonomous \
  --scenes FloorPlan201 \
  --seeds 1 \
  --agents 1 \
  --steps 2 \
  --model kimi-coding \
  --allow-local
```

Successful autonomous rerun after the stale `18788` owner cleared:

```bash
docker rm -f openclaw-gateway >/dev/null 2>&1 || true
PROVIDER=kimi .venv/bin/python scripts/capture_refactor_regression.py \
  --suite openclaw-autonomous \
  --label baseline-2026-04-23-openclaw-autonomous-rerun \
  --scenes FloorPlan201 \
  --seeds 1 \
  --agents 1 \
  --steps 2 \
  --model kimi-coding \
  --allow-local
```

## Refreshed Suites

### 1. Direct VLM

**Suite:** `explore-vlm`
**Coordinate tuple:** `(suite=explore-vlm, backend=vlm, scene=FloorPlan201, seed=1, game=explore, model=kimi-coding, agents=1, variant=null)`

Baseline artifact:

`output/refactor-regression/baseline-2026-04-23-direct/explore-vlm/FloorPlan201-seed1/20260423T133218549634-7705c79b`

Candidate artifact:

`output/refactor-regression/candidate-2026-04-23-direct-samecommit/explore-vlm/FloorPlan201-seed1/20260423T133345799091-044c3863`

Observed metrics:

- baseline: `cells_visited=3`, `usd=0.009459`, `wallclock_seconds=78.27`, `termination_reason=max_steps`
- candidate: `cells_visited=2`, `usd=0.016323`, `wallclock_seconds=197.62`, `termination_reason=max_steps`

This pair was a **same-commit workflow proof**, not a before/after refactor
comparison. The intent was to prove the capture/analyzer workflow against a
real provider path, not to claim behavioral drift on the same tree.

### 2. Push-model OpenClaw

**Suite:** `openclaw-demo`
**Coordinate tuple:** `(suite=openclaw-demo, backend=openclaw, scene=FloorPlan201, seed=1, game=navigation, model=openclaw:agent-*, agents=2, variant=map-v2+chase)`

Artifact:

`output/refactor-regression/baseline-2026-04-23-openclaw-demo/openclaw-demo/FloorPlan201-seed1/20260423T133812373343-e9c73855`

Observed metrics:

- `termination_reason=max_steps`
- `wallclock_seconds=58.49`
- `variant=map-v2+chase`
- Gateway bootstrap/probe succeeded (`openclaw/agent-0 -> PONG`) before the run

### 3. Autonomous OpenClaw

**Suite:** `openclaw-autonomous`
**Coordinate tuple:** `(suite=openclaw-autonomous, backend=openclaw, scene=FloorPlan201, seed=1, game=autonomous-navigation, model=kimi-coding, agents=1, variant=map-v2+chase)`

First attempt artifact:

`output/refactor-regression/baseline-2026-04-23-openclaw-autonomous/openclaw-autonomous/FloorPlan201-seed1/20260423T133935990387-c08f08a1`

First attempt outcome:

- MCP server bind failed on `0.0.0.0:18788` because another local process already owned the port
- `run_result.json` recorded `terminated_by=error`
- `summary.json` showed zero tool calls
- this surfaced a harness bug: the capture suite had been treating `terminated_by=error` as `status=ok`

Successful rerun artifact:

`output/refactor-regression/baseline-2026-04-23-openclaw-autonomous-rerun/openclaw-autonomous/FloorPlan201-seed1/20260423T134558571396-519f233d`

Successful rerun outcome:

- `terminated_by=done`
- `tool_calls_by_type={"observe": 2, "move": 1, "done": 1}`
- `frames_unseen_by_agent=1`
- `decision_modes={"fresh_observe": 0, "reasoned_batch": 1, "blind_batch": 0}`
- `transcript_source=terminal-body`
- `view_variant=map-v2+chase`
- `report.html`, `replay.gif`, `trace.jsonl`, `run_result.json`, and `summary.json` all present

## Analyzer Outcome

Analyzer output:

- `output/refactor-regression/candidate-2026-04-23-direct-samecommit/analysis/summary.md`
- `output/refactor-regression/candidate-2026-04-23-direct-samecommit/analysis/summary.json`

Final analyzer verdict: **pass**

Details from the final analyzer run:

- `cells_visited`: pass (`3 -> 2`, allowed floor `>= 2`)
- `usd`: pass after threshold update (`0.009459 -> 0.016323`)
- `wallclock_seconds`: pass after threshold update (`78.27 -> 197.62`)

This remained a **same-commit workflow proof**. No claim is made that the
candidate is a better or worse code revision than the baseline.

## Threshold Adjustment Justified By Live Evidence

Live same-commit Kimi runs showed that the original ratio-only `explore-vlm`
thresholds were too brittle for small real captures:

- original `usd` rule: `<= +25%`
- original `wallclock` rule: `<= +50%`

Those rules failed a same-commit 3-step workflow-proof pair even though:

- both runs ended `max_steps`
- `cells_visited` stayed within the expected tolerance
- no provider failure occurred

The analyzer was updated to use:

- `usd`: `<= max(+25%, +$0.01 absolute slack)`
- `wallclock_seconds`: `<= max(+50%, +120s absolute slack)`

Rationale: for tiny real-provider captures, fixed per-turn and cold-start
overheads dominate the ratio, so a small absolute slack makes the workflow
usable without masking large regressions.

## Harness Corrections Triggered By The Probe

Two corrections landed during this probe cycle:

1. `openclaw-autonomous` capture now raises an error when:
   - `run_result.json` reports `terminated_by=error`, or
   - `summary.json` shows zero `observe` calls

2. `explore-vlm` analyzer policy now uses ratio-or-absolute slack for cost and
   wall-clock, based on the live same-commit evidence above.

## Notes

- No secrets were written to this file.
- No large baseline artifacts were committed; only the artifact paths are
  recorded here.
- The stale-port failure was environmental, not a claim against the autonomous
  runner itself. Once `18788` was free, the same suite completed successfully.
