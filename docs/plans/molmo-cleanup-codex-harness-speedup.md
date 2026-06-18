# Molmo Cleanup Codex Harness Speedup

**Status:** Proposed source plan
**Created:** 2026-05-19
**Source:** Local Codex Molmo cleanup timing review and harness speedup request
**Workflow:** Pre-GSD plan. Ingest or pass to `gsd-plan-phase` before
implementation.

## Problem

The current local Codex Molmo cleanup proof is correct and reviewable, but slow
enough that iteration on MCP and skill design is expensive.

The latest local Codex proof cited in `STATUS.md`,
`output/molmo/codex-local-env-nav2-report/0519_2041/seed-7/report.html`, took
about 18m30s end to end. Its MCP trace shows 58 requests, 19 observations, 14
waypoint sweeps, 5 object cleanups, full sweep coverage, and a successful final
report.

The wall-clock split is already visible from trace timestamps:

- tool/backend handling: about 370s;
- robot-view capture: about 405s;
- between-tool gaps, including model reasoning, Codex CLI orchestration,
  transport, and post-response overhead: about 297s.

The biggest measurable cost is not pure navigation logic. A speedup pass should
separate what the model is doing from what navigation/backend tools are doing,
then make nonessential proof work optional during performance iteration.

## Goal

Create a two-lane Molmo cleanup harness:

- keep the current `world-labels` lane as the full visual proof path with RBY1M
  robot-view artifacts;
- add an explicit fast performance lane that uses the same local Docker-backed
  Codex runtime and Molmo cleanup MCP contract, but skips or samples
  nonessential visual capture;
- produce a timing summary that explains model/agent time, navigation/backend
  time, robot-view capture time, and avoidable overhead.

The intended operator entry point is:

```bash
just agent::harness molmo-cleanup-codex-perf seed=7 generated_mess_count=10
```

This should route through the supported local Codex runtime, not bare host
`codex`.

## Decisions Locked

- Use the supported Docker-backed Codex path already used by
  `just task::run molmo-cleanup codex ...`.
- Do not replace the current `world-labels` report lane. Full visual proof
  remains available and remains the default human-review artifact.
- Add a separate performance lane, tentatively `world-labels-perf`, for speed
  diagnosis.
- Keep waypoint honesty, public/private separation, cleanup success, and final
  checker gates intact.
- Do not skip `metric_map`, `fixture_hints`, the waypoint sweep, final
  `done`, or private-scoring separation.
- Treat per-tool robot-view capture as optional performance overhead in the
  performance lane, not as required model input for structured world-label runs.

## Implementation Sketch

Add a `world-labels-perf` cleanup profile:

- backend: `molmospaces_subprocess`;
- perception mode: `visible_object_detections`;
- include robot metadata where useful, but do not record every per-tool robot
  view;
- require cleanup success, waypoint honesty, real-robot alignment, and full
  sweep coverage;
- label the report as semantic/performance evidence, not full robot-view proof.

Extend command routing:

- accept `world-labels-perf` in the Molmo cleanup facade;
- add `harness::molmo-cleanup-codex-perf`;
- allow that target through `just agent::harness`;
- route the harness to the existing `codex-live` runner.

Persist timing attribution:

- write a `runtime_timing` summary into `run_result.json`;
- write a live-run timing artifact such as `live_timing.json` with server
  startup, time to first MCP request, Codex exec elapsed, checker elapsed, and
  total elapsed;
- extend `scripts/molmo_cleanup/summarize_live_run.py` to print tool/backend
  handling, robot-view capture, between-tool/model gaps, and the slowest tools
  and gaps.

Fix local Codex skill materialization:

- ensure Docker-isolated Codex workspaces can actually read
  `skills/molmo-realworld-cleanup/SKILL.md`;
- prefer copying the task skill into the isolated workspace over a host symlink
  that can point outside the mounted container workspace;
- keep the kickoff prompt unchanged except where the new performance profile
  needs explicit "performance lane" wording.

## Expected Speedups

The first expected win is eliminating full per-tool robot-view capture in the
performance lane. The measured baseline spent about 405s there, so the
performance lane should save roughly 6-7 minutes if other behavior remains
similar.

Secondary wins should come from:

- fixing the missing skill lookup observed in the Codex event log, which caused
  extra shell exploration before MCP use;
- reducing tool-call count only where the skill can do so without weakening the
  sweep or cleanup contract;
- using the timing report to identify whether navigation tools, observation
  tools, or model gaps dominate after robot-view capture is removed.

## Non-Goals

- Do not remove or weaken the `world-labels` visual proof report.
- Do not make hosted CI launch live Codex.
- Do not expose private generated mess truth or acceptable-destination tables.
- Do not claim physical robot execution or planner-backed manipulation from
  this speedup pass.
- Do not optimize by skipping the waypoint-honest sweep required by the current
  checker.

## Acceptance Criteria

- `just agent::harness molmo-cleanup-codex-perf ...` launches the local
  Docker-backed Codex cleanup run through the existing network and provider
  guards.
- The performance lane produces `run_result.json`, `trace.jsonl`, timing
  summary artifacts, and `report.html`.
- The checker passes for cleanup success, waypoint honesty, real-robot
  alignment, and sweep coverage.
- `just molmo::status <run_dir>` reports the timing split clearly enough to
  answer:
  - what time the model/Codex side spent between tool calls;
  - what time MCP tools and backend navigation/manipulation spent;
  - what time robot-view capture spent;
  - which work is skipped or sampled in the performance lane.
- A baseline-vs-candidate comparison is recorded using the 18m30s local Codex
  run as the initial baseline.

## Verification Plan

- Routing dry runs:

  ```bash
  ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex world-labels-perf
  ROBOCLAWS_JUST_TRACE=1 just agent::harness molmo-cleanup-codex-perf
  ```

- Focused static checks:

  ```bash
  ruff check just/agent.just just/molmo.just roboclaws/molmo_cleanup/profiles.py \
    scripts/molmo_cleanup/run_live_codex_cleanup.py \
    scripts/molmo_cleanup/summarize_live_run.py
  ruff format --check roboclaws/molmo_cleanup/profiles.py \
    scripts/molmo_cleanup/run_live_codex_cleanup.py \
    scripts/molmo_cleanup/summarize_live_run.py
  ```

- Focused tests:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh -q \
    tests/contract/molmo_cleanup \
    tests/contract/reports/test_molmo_cleanup_report.py \
    tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
  ```

- Local proof run after sourcing `.env`:

  ```bash
  just agent::harness molmo-cleanup-codex-perf seed=7 generated_mess_count=10
  just molmo::status <run_dir>
  ```

## GSD Handoff

This should be a bounded instrumentation and routing phase before deeper MCP or
skill refactors. The first phase should add the performance lane and timing
attribution, run one local Codex proof, then use the resulting split to decide
whether the next bounded change belongs in MCP tools, backend navigation, report
capture, or the cleanup skill.

Preferred handoff:

```text
gsd-plan-phase <phase> --prd docs/plans/molmo-cleanup-codex-harness-speedup.md
```

The stop condition is a local Codex performance harness artifact that is faster
than the current 18m30s baseline while preserving cleanup correctness and
making the time split explicit.
