<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0423-autoplan-restore-20260423-205957.md -->
---
phase: 4
plan: 02
slug: direct-vlm-and-game-capture-suites
type: execute
wave: 2
depends_on: ["04-01"]
files_modified:
  - roboclaws/regression.py
  - scripts/capture_refactor_regression.py
  - tests/test_capture_refactor_regression.py
autonomous: false
requirements_addressed: [A-08]

must_haves:
  truths:
    - "Direct-VLM suites reuse the existing `run_exploration`, `run_territory_game`, and `run_coverage_game` entrypoints instead of forking their control loops."
    - "Each captured row exposes stable pairing coordinates plus structured metrics from the existing result dicts and `replay.json` summaries."
    - "The capture harness preserves append-only `results.jsonl` semantics and per-run replay directories."
    - "Cloud-safe tests cover the suite registration and row extraction paths without live VLM calls or Unity; real direct-VLM behavioral captures stay honest about their environment requirements."
  artifacts:
    - path: "roboclaws/regression.py"
      provides: "Registered direct-VLM / territory / coverage suites with normalized row extraction"
      contains: "explore-vlm"
    - path: "scripts/capture_refactor_regression.py"
      provides: "Capture CLI capable of running the direct-VLM suite matrix"
      contains: "territory-vlm"
    - path: "tests/test_capture_refactor_regression.py"
      provides: "Smoke coverage for direct suite registration and row output"
      contains: "coverage-vlm"
  key_links:
    - from: "roboclaws/regression.py"
      to: "scripts/capture_refactor_regression.py"
      via: "suite registry consumed by the CLI matrix loop"
      pattern: "explore-vlm"
---

<objective>
Wire the direct-VLM and game-path suites into the Phase-4 capture harness.
After this plan, a provisioned local-dev or otherwise fully provisioned session
can capture baseline/candidate rows for the repo's direct exploration,
territory, and coverage paths without inventing new runner logic. Cloud-safe
sessions still get truthful synthetic coverage of the registry/row plumbing,
not fake claims about real-model behavior.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-CONTEXT.md
@.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-RESEARCH.md
@roboclaws/regression.py
@scripts/capture_refactor_regression.py
@examples/single_agent_explore.py
@examples/territory_game.py
@examples/coverage_game.py
@examples/view_experiment.py
@tests/test_view_experiment.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Register the direct-VLM suites and normalize their row shapes</name>
  <read_first>
    - examples/single_agent_explore.py
    - examples/territory_game.py
    - examples/coverage_game.py
    - examples/view_experiment.py
    - roboclaws/regression.py
  </read_first>
  <behavior>
    - The harness calls the existing public runners directly.
    - Row extraction uses the structured return dict plus `replay.json` summary when helpful; it does not parse stdout.
    - Each suite emits stable coordinates suitable for baseline-vs-candidate pairing.
    - Missing-provider / missing-Unity / other environment failures become actionable error rows or loud failures, not a misleading "cloud-safe" story.
  </behavior>
  <action>
    Extend `roboclaws/regression.py` with these capture suites:

    1. `explore-vlm`
       - runner: `run_exploration(...)`
       - metrics: `cells_visited`, `termination_reason`, `vlm_cost_usd`,
         `provider_status`, replay `total_steps`

    2. `territory-vlm`
       - runner: `run_territory_game(..., backend="vlm")`
       - metrics: `cells_claimed_total`, `blocking_events`,
         `termination_reason`, `vlm_cost_usd`, `provider_status`

    3. `coverage-vlm`
       - runner: `run_coverage_game(..., backend="vlm")`
       - metrics: `coverage_fraction`, `cells_covered`, `work_balance`,
         `termination_reason`, `vlm_cost_usd`, `provider_status`

    Required common coordinates:
    - `suite`
    - `backend`
    - `scene`
    - `seed`
    - `game`
    - `model`
    - `agents`
    - `variant` when present

    Seed the suites the same way `view_experiment.py` does: set both
    `random.seed(seed)` and `np.random.seed(seed)` before calling the runner.
  </action>
  <verify>
    <automated>cd /home/mi/ws/gogo/roboclaws && pytest tests/test_capture_refactor_regression.py -q</automated>
  </verify>
  <done>The direct-VLM suites exist and emit structured rows with stable pairing coordinates.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend the capture CLI for direct-VLM matrix runs</name>
  <read_first>
    - scripts/capture_refactor_regression.py
    - roboclaws/regression.py
    - examples/view_experiment.py
  </read_first>
  <behavior>
    - The CLI remains thin: suite selection, coordinate iteration, append-only row writing, and output-dir layout only.
    - Per-run artifacts stay under the suite-specific replay dir produced by the existing runner.
    - The CLI supports partial suite lists so operators can refresh one baseline slice without rerunning everything.
  </behavior>
  <action>
    Update `scripts/capture_refactor_regression.py` to run the direct-VLM suite
    matrix.

    Required behavior:

    1. Accept `--suite explore-vlm,territory-vlm,coverage-vlm` and iterate
       `suite × scene × seed`.

    2. Write output under:

       ```text
       output/refactor-regression/<label>/<suite>/<scene>-seed<N>/<run-id>/
       ```

       with `results.jsonl` at the `<label>/` root. `<label>` must be an
       immutable capture-set name such as `baseline-2026-04-23` or
       `candidate-dongxu-dev-0423`, not a mutable bucket reused over time.

    3. Keep JSONL append-only semantics. If a run fails, write a row with:
       - `status=error`
       - `error_kind`
       - `error`
       - the same stable coordinates

    4. Add smoke tests proving:
       - multiple direct suites can run in one command
       - rows append in a deterministic order
       - rerunning the same coordinate keeps both artifact dirs intact
       - failed runs log error rows and the loop continues

    Do NOT add a separate analyzer here. That belongs to Plan 04.
  </action>
  <verify>
    <automated>cd /home/mi/ws/gogo/roboclaws && pytest tests/test_capture_refactor_regression.py tests/test_refactor_regression_contracts.py -q</automated>
  </verify>
  <done>The capture CLI can run the direct-VLM suite matrix and produce replay dirs plus append-only rows.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Capture CLI ↔ existing example runners | The harness must call the shipped entrypoints exactly as they are, not a harness-only fork. |
| Structured result rows ↔ later analyzer | The row schema chosen here becomes the pairing surface for Plan 04. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-03 | Tampering | Direct-VLM capture suites | mitigate | Reuse the existing public runners and extract only structured outputs plus replay summaries. |
| T-04-04 | Repudiation | Append-only capture history | mitigate | Failed runs still emit error rows with full stable coordinates so baseline/candidate comparisons do not silently skip regressions. |

No `high`-severity threats; plan proceeds.
</threat_model>

<verification>
- `pytest tests/test_capture_refactor_regression.py tests/test_refactor_regression_contracts.py -q` exits 0.
- Direct-VLM capture runs reuse the current examples and produce append-only rows.
- Row shapes are stable enough for baseline-vs-candidate pairing.
</verification>

<success_criteria>
- A provisioned local-dev or otherwise fully provisioned session can capture
  baseline or candidate runs for the direct-VLM stacks.
- The harness exposes the metrics Phase 4 actually cares about instead of raw text logs.
- No duplicate runner implementation exists.
</success_criteria>
