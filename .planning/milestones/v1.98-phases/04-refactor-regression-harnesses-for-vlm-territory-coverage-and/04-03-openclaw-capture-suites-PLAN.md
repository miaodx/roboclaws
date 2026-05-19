<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0423-autoplan-restore-20260423-205957.md -->
---
phase: 4
plan: 03
slug: openclaw-capture-suites
type: execute
wave: 3
depends_on: ["04-02"]
files_modified:
  - roboclaws/regression.py
  - scripts/capture_refactor_regression.py
  - tests/test_capture_refactor_regression.py
autonomous: false
requirements_addressed: [A-08]

must_haves:
  truths:
    - "Push-model OpenClaw suites reuse `openclaw_demo.py` and the existing territory/coverage example runners with `backend=\"openclaw\"`."
    - "The autonomous OpenClaw suite extracts structured metrics from `run_result.json` and `summary.json`; it does not diff raw transcript prose."
    - "Every OpenClaw suite is explicitly marked local-dev only and refuses to run without the operator override."
    - "Captured rows never log secrets and only persist artifact paths plus structured metrics."
  artifacts:
    - path: "roboclaws/regression.py"
      provides: "OpenClaw push-model and autonomous suite definitions with structured metric extraction"
      contains: "openclaw-autonomous"
    - path: "scripts/capture_refactor_regression.py"
      provides: "Capture CLI capable of local-only OpenClaw suite execution"
      contains: "--allow-local"
    - path: "tests/test_capture_refactor_regression.py"
      provides: "Synthetic suite tests for OpenClaw row extraction and guardrails"
      contains: "openclaw-demo"
  key_links:
    - from: "roboclaws/regression.py"
      to: "scripts/render_autonomous_replay.py"
      via: "summary metrics consumed from `summary.json`"
      pattern: "transcript_source"
---

<objective>
Extend the Phase-4 capture harness to the shipped OpenClaw paths. After this
plan, the same baseline/candidate workflow can capture push-model Gateway runs
and the autonomous MCP path while preserving the repo's cloud/local boundary.
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
@examples/openclaw_demo.py
@examples/territory_game.py
@examples/coverage_game.py
@examples/openclaw_nav_autonomous.py
@scripts/render_autonomous_replay.py
@tests/test_openclaw_demo.py
@tests/test_openclaw_nav_autonomous.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add the push-model OpenClaw capture suites</name>
  <read_first>
    - examples/openclaw_demo.py
    - examples/territory_game.py
    - examples/coverage_game.py
    - roboclaws/regression.py
  </read_first>
  <behavior>
    - Reuse the current runners exactly as the user would run them.
    - Mark these suites as local-dev only.
    - Extract only structured result data plus replay summary / replay step-state fields when the runner omits a metric directly.
  </behavior>
  <action>
    Extend `roboclaws/regression.py` with push-model OpenClaw suites:

    1. `openclaw-demo`
       - runner: `run_openclaw_demo(...)`
       - metrics: `visited_cells` (from the final replay step's
         `game_state.visited_cells` or an additive summary field if that lands
         cheaply), `steps_executed`, `termination_reason`, `provider_status`

    2. `territory-openclaw`
       - runner: `run_territory_game(..., backend="openclaw")`
       - metrics: `cells_claimed_total`, `blocking_events`,
         `termination_reason`, `provider_status`

    3. `coverage-openclaw`
       - runner: `run_coverage_game(..., backend="openclaw")`
       - metrics: `coverage_fraction`, `cells_covered`, `work_balance`,
         `termination_reason`, `provider_status`

    All three suites must:
    - set `backend="openclaw"` explicitly
    - carry the same stable coordinates as the direct-VLM suites
    - be flagged `local_dev_only=True`
    - prove via synthetic tests that `openclaw-demo` can recover
      `visited_cells` from canned replay artifacts without changing the real loop
  </action>
  <verify>
    <automated>cd /home/mi/ws/gogo/roboclaws && pytest tests/test_capture_refactor_regression.py tests/test_openclaw_demo.py -q</automated>
  </verify>
  <done>Push-model OpenClaw suites exist and are guarded as local-only.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add the autonomous OpenClaw suite and local-only CLI guardrails</name>
  <read_first>
    - examples/openclaw_nav_autonomous.py
    - scripts/render_autonomous_replay.py
    - tests/test_openclaw_nav_autonomous.py
    - tests/test_render_autonomous_replay.py
    - scripts/capture_refactor_regression.py
  </read_first>
  <behavior>
    - The autonomous suite captures structured data only: `run_result.json`,
      `summary.json`, and artifact paths.
    - The CLI refuses local-only suites unless the operator explicitly opts in.
    - Tests stay synthetic: no real Gateway, Docker, or AI2-THOR.
  </behavior>
  <action>
    Finish the OpenClaw capture surface:

    1. Add `openclaw-autonomous` to `roboclaws/regression.py`:
       - runner: `run_autonomous_navigation(...)`
       - row extraction sources:
         - `run_result.json`
         - `summary.json`
       - required metrics:
         - `terminated_by`
         - `transcript_source`
         - `tool_calls_by_type`
         - `frames_unseen_by_agent`
         - `decision_modes`
         - `wallclock_seconds`
         - `view_variant`

    2. Update `scripts/capture_refactor_regression.py` so any suite marked
       `local_dev_only=True` hard-fails without `--allow-local`, with a message
       that points back to the repo's cloud/local split.

    3. Add synthetic tests proving:
       - autonomous row extraction works from canned `run_result.json` and
         `summary.json`
       - `--allow-local` is required for OpenClaw suites
       - failed local-only runs still emit error rows with stable coordinates

    Do NOT add threshold logic here. That belongs to Plan 04.
  </action>
  <verify>
    <automated>cd /home/mi/ws/gogo/roboclaws && pytest tests/test_capture_refactor_regression.py tests/test_openclaw_nav_autonomous.py tests/test_render_autonomous_replay.py -q</automated>
  </verify>
  <done>The harness can capture structured OpenClaw push-model and autonomous metrics without weakening the local-only boundary.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Local-only OpenClaw suites ↔ cloud sessions | The capture harness must not imply that cloud can validate real Gateway behavior. |
| OpenClaw artifact extraction ↔ later analyzer | The analyzer depends on truthful structured metrics, not hidden secrets or prose parsing. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-05 | Information Disclosure | OpenClaw capture rows | mitigate | Persist only structured metrics and artifact paths; never write bearer tokens or raw Authorization headers. |
| T-04-06 | Spoofing | Local-only suite execution | mitigate | Require an explicit `--allow-local` override for every local-only OpenClaw suite. |
| T-04-07 | Tampering | Autonomous metric extraction | mitigate | Derive metrics from `run_result.json` and `summary.json`, not from fragile transcript text parsing. |

No `high`-severity threats; plan proceeds.
</threat_model>

<verification>
- `pytest tests/test_capture_refactor_regression.py tests/test_openclaw_demo.py tests/test_openclaw_nav_autonomous.py tests/test_render_autonomous_replay.py -q` exits 0.
- OpenClaw suites are explicit, local-only, and structured.
- The capture harness still does not own any runner logic itself.
</verification>

<success_criteria>
- The Phase-4 capture workflow now spans the shipped OpenClaw surfaces.
- The cloud/local boundary is enforced by code, not just by documentation.
- The analyzer will receive stable OpenClaw metrics instead of raw prose blobs.
</success_criteria>
