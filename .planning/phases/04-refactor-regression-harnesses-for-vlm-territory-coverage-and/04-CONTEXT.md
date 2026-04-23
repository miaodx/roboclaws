---
phase: "4"
phase_name: "Refactor regression harnesses for VLM, territory/coverage, and OpenClaw"
status: "Ready for planning"
gathered: "2026-04-23"
mode: "Pre-seeded from refactor-safety discussion; current root PLAN.md is the source-draft context file"
depends_on: "2.4, 2.6"
---

# Phase 4: Refactor regression harnesses for VLM, territory/coverage, and OpenClaw — Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Mode:** Pre-seeded from the 2026-04-23 refactor-safety discussion. The repo already has the right patterns in place (`results.jsonl` runners, separate analyzers, fixture-backed schema contracts); this phase should extend those patterns, not replace them with a monolithic new harness.

<authoritative_source>
## Authoritative Sources

1. `PLAN.md` — current active source draft. Treat this as the primary source-draft context file for how the repo currently frames validation work.
2. `.planning/STATE.md` — current active phase state, blockers, and recent refactor context.
3. `examples/view_experiment.py` — existing thin capture harness pattern: append-only `results.jsonl`, per-run replay dirs, named suite coordinates.
4. `scripts/analyze_view_experiment.py` — existing analyzer pattern: separate CLI, paired comparisons, threshold/stat summary output.
5. `scripts/generate_demo_report.py` — cloud-safe mock/demo harness pattern that reuses existing runners rather than reimplementing loops.
6. `tests/fixtures/trace_schema_reference.json` plus `tests/test_openclaw_mcp_server.py` — current reference-fixture pattern for frozen contracts.

</authoritative_source>

<domain>
## Phase Boundary

Add refactor-safety harnesses for the three paths the user explicitly wants preserved:
- direct VLM behavior
- territory + coverage game behavior
- OpenClaw behavior

**In scope (MUST deliver):**
- Deterministic regression fixtures for exact contracts
- Thin run-capture harness(es) that emit append-only machine-readable rows plus replay artifacts
- Separate compare/analyze harness(es) that diff baseline vs candidate runs by stable coordinates
- Threshold-based regression gates for real-model / live-Gateway behavior where exact step equality is too brittle

**Out of scope (explicit):**
- Rewriting the game loops or provider flows just to fit a new harness
- One giant all-in-one script that mixes execution, diffing, reporting, and fixture generation
- Exact reasoning-text comparisons for real VLM/OpenClaw runs
- Reopening the deferred Isaac Lab work

</domain>

<decisions>
## Implementation Decisions

### D-01: Do not build one fat harness
Prefer 2-3 small pieces that match current repo practice:
- capture runner CLI
- compare/analyze CLI
- optional shared suite/row helper module

### D-02: Reuse existing entrypoints
Drive `examples/territory_game.py`, `examples/coverage_game.py`, `examples/openclaw_demo.py`, and the shipped autonomous/OpenClaw surfaces through their existing runners. Do not fork a parallel execution stack.
When a suite needs a metric the runner does not return directly, extract it from
the existing replay artifacts instead of rewriting the loop just for the harness.

### D-03: Split exact-contract vs behavioral-regression coverage
- Exact contracts belong in tests + tiny committed fixtures
- Behavioral regressions belong in run harness outputs + thresholds/statistical comparisons

### D-04: Compare structured metrics, not raw prose
Use replay summaries, trace metrics, termination reasons, counts, costs, and other structured outputs. Do not gate on exact reasoning text.

### D-05: Stable pairing keys are mandatory
Baseline vs candidate comparisons should pair on stable coordinates such as `suite`, `scene`, `seed`, `game`, `backend`, and `variant` when applicable.
Those stable coordinates are not the artifact identity. Repeated captures of the
same coordinate tuple still need unique per-run artifact directories so the
evidence is retained instead of overwritten.

### D-06: Current root `PLAN.md` stays in the context set
The user explicitly asked to use the current plan as one context file. Planning should keep `PLAN.md` in the authoritative source set rather than treating this phase as disconnected tooling work.

</decisions>

<specifics>
## Specific Touchpoints

**Likely files to modify or add:**
- new capture/analyze scripts under `scripts/`
- tests for harness registries / row extraction / threshold comparison
- possibly a small shared helper module under `roboclaws/` or `scripts/`
- reference fixtures under `tests/fixtures/` for any newly frozen schema/row shapes

**Likely suite split:**
- synthetic contract / registry smoke: cloud-safe proof that the harness wiring
  works without claiming real-model behavior
- `real-vlm`: direct VLM exploration / territory / coverage behavior snapshots
  on a provisioned local-dev or otherwise fully provisioned environment
- `openclaw-live`: OpenClaw demo/game behavior snapshots

**Likely metrics by path:**
- direct VLM: fallback rate, retry/transient counts, cost, termination reason
- territory: claimed cells, blocking events, connectivity, stale/max-step behavior
- coverage: coverage fraction, steps-to-target, work balance
- OpenClaw push-model: visited cells (from replay step state when the runner
  does not return it directly), steps executed, termination reason, provider
  status
- OpenClaw autonomous: terminated_by, transcript source, observe/move/done
  counts, blind-move warnings, collisions

</specifics>

<success_shape>
## Phase Outcome

After this phase, a maintainer doing a large refactor should be able to answer:

1. Did I preserve the hard contracts?
2. Did I preserve the important behaviors within tolerance?
3. If something regressed, which stack did it break: direct VLM, game logic, or OpenClaw?

</success_shape>

---

*Phase: 04-refactor-regression-harnesses-for-vlm-territory-coverage-and*
*Context gathered: 2026-04-23*
