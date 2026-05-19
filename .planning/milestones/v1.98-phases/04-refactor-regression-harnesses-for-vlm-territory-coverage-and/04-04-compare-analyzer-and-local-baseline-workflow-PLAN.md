<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0423-autoplan-restore-20260423-205957.md -->
---
phase: 4
plan: 04
slug: compare-analyzer-and-local-baseline-workflow
type: execute
wave: 4
depends_on: ["04-03"]
files_modified:
  - scripts/analyze_refactor_regression.py
  - tests/test_analyze_refactor_regression.py
  - docs/refactor-regression.md
  - .planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md
autonomous: false
requirements_addressed: [A-08]

must_haves:
  truths:
    - "Baseline-vs-candidate comparison pairs runs on stable coordinates and exits non-zero on threshold breaches."
    - "Threshold policy is suite-specific, reviewable in code, and separate from capture."
    - "`docs/refactor-regression.md` tells operators how to capture baselines, run comparisons, and which suites are local-only."
    - "`04-LOCAL-PROBE-RESULTS.md` records the first real baseline refresh commands, artifact paths, and any threshold adjustments justified by live evidence."
    - "No large baseline artifacts or secrets are committed to the repo."
  artifacts:
    - path: "scripts/analyze_refactor_regression.py"
      provides: "Machine-readable and markdown baseline-vs-candidate analyzer"
      contains: "ThresholdPolicy"
    - path: "docs/refactor-regression.md"
      provides: "Operator workflow for baseline capture, candidate capture, and comparison"
      contains: "local-only suites"
    - path: ".planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md"
      provides: "Dated local evidence for the first real baseline refresh"
      contains: "Artifact paths"
  key_links:
    - from: "docs/refactor-regression.md"
      to: ".planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md"
      via: "operator evidence link"
      pattern: "04-LOCAL-PROBE-RESULTS"
---

<objective>
Finish the Phase-4 workflow by adding the baseline-vs-candidate analyzer,
operator documentation, and the first real local baseline refresh. After this
plan, maintainers can use the harnesses to answer "did the refactor preserve
behavior within tolerance?" on the real stacks that matter.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-CONTEXT.md
@.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-RESEARCH.md
@.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-VALIDATION.md
@roboclaws/regression.py
@scripts/capture_refactor_regression.py
@examples/view_experiment.py
@scripts/analyze_view_experiment.py
@scripts/render_autonomous_replay.py
@docs/openclaw-local.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement the baseline-vs-candidate analyzer with suite-specific threshold policies</name>
  <read_first>
    - scripts/analyze_view_experiment.py
    - roboclaws/regression.py
    - .planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-RESEARCH.md
  </read_first>
  <behavior>
    - The analyzer is separate from capture.
    - Pairing is driven only by stable coordinates.
    - Threshold policy is explicit per suite; no single global threshold.
    - The analyzer emits both human-readable markdown and machine-readable JSON.
  </behavior>
  <action>
    Create `scripts/analyze_refactor_regression.py` and
    `tests/test_analyze_refactor_regression.py`.

    Required analyzer behavior:

    1. Inputs:
       - `--baseline <results.jsonl>`
       - `--candidate <results.jsonl>`
       - optional `--output-dir`

    2. Pair rows on:
       - `suite`
       - `backend`
       - `scene`
       - `seed`
       - `game`
       - `model`
       - `agents`
       - `variant`

    3. Enforce suite policies in code, with at least these first-pass rules:
       - `explore-vlm`: visited cells no worse than `-1`,
         cost `<= +25%`, wallclock `<= +50%`
       - `openclaw-demo`: visited cells from replay step state no worse than
         `-1`, replay-summary cost (when present) `<= +25%`, wallclock
         `<= +50%`
       - `territory-*`: total claimed no worse than `-2`, blocking no worse
         than `+2`, no new provider-failure termination
       - `coverage-*`: coverage fraction no worse than `-0.05`, work balance
         no worse than `-0.10`, steps no worse than `+20%`
       - `openclaw-autonomous`: `transcript_source` exact,
         `tool_calls_by_type` within `±2`, `frames_unseen_by_agent` no worse
         than `+2`

    4. Outputs:
       - `summary.md`
       - `summary.json`
       - non-zero exit code if any threshold is breached

    5. Tests must cover:
       - successful pairing
       - missing baseline or candidate rows
       - threshold breaches
       - suite-specific exact checks such as `transcript_source`
  </action>
  <verify>
    <automated>cd /home/mi/ws/gogo/roboclaws && pytest tests/test_analyze_refactor_regression.py -q</automated>
  </verify>
  <done>The repo can compare baseline vs candidate capture sets and fail fast on real regressions.</done>
</task>

<task type="auto">
  <name>Task 2: Write the operator workflow in `docs/refactor-regression.md`</name>
  <read_first>
    - scripts/capture_refactor_regression.py
    - scripts/analyze_refactor_regression.py
    - AGENTS.md § 1 and § 7
    - docs/openclaw-local.md
  </read_first>
  <behavior>
    - The doc is concise and operational.
    - It distinguishes cloud-safe suites from local-only suites.
    - It explains baseline refresh, candidate capture, analyzer use, and how to investigate a failure.
  </behavior>
  <action>
    Add `docs/refactor-regression.md` with these sections:

    1. `## What this harness protects`
       - direct VLM
       - territory / coverage
       - OpenClaw push-model
       - OpenClaw autonomous

    2. `## Capture a baseline`
       - example `scripts/capture_refactor_regression.py` commands
       - explain that `--label` should be an immutable capture-set name such
         as `baseline-2026-04-23`

    3. `## Capture a candidate`
       - matching commands with a different immutable capture-set label/output
         root such as `candidate-dongxu-dev-0423`

    4. `## Compare them`
       - `scripts/analyze_refactor_regression.py` command
       - where `summary.md` / `summary.json` land

    5. `## Local-only suites`
       - explain `--allow-local`
       - point back to `AGENTS.md` cloud/local split and `docs/openclaw-local.md`

    6. `## Evidence`
       - link to `04-LOCAL-PROBE-RESULTS.md`

    Keep the doc operator-facing. Do not turn it into a changelog.
  </action>
  <verify>
    <automated>bash -c 'f=/home/mi/ws/gogo/roboclaws/docs/refactor-regression.md; rg -n "What this harness protects|Capture a baseline|Capture a candidate|Compare them|Local-only suites|04-LOCAL-PROBE-RESULTS" "$f"'</automated>
  </verify>
  <done>The repo has one operator doc for baseline capture, candidate capture, and comparison.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Pre-flight — confirm a real local baseline refresh is possible</name>
  <read_first>
    - AGENTS.md § 1 and § 7
    - docs/openclaw-local.md
    - docs/refactor-regression.md
  </read_first>
  <behavior>
    - This task does not proceed in a cloud-only session.
    - The operator confirms Docker, AI2-THOR, and at least one real provider key are available.
    - No stale `openclaw-gateway` container is blocking the expected ports unless the operator intends to reuse it.
  </behavior>
  <action>
    Run and paste the outputs of:

    1. `set -a && source .env && set +a`
    2. `docker --version`
    3. `python -c "import ai2thor; print(ai2thor.__version__)"`
    4. `[[ -n "$KIMI_API_KEY" || -n "$OPENAI_API_KEY" || -n "$ANTHROPIC_API_KEY" ]] && echo provider-set || echo provider-missing`
    5. `docker ps -a --format '{{.Names}}' | grep -x openclaw-gateway || echo absent`
    6. `env -i PATH=".venv/bin:/usr/bin:/bin" HOME=$HOME .venv/bin/pytest tests/test_capture_refactor_regression.py tests/test_analyze_refactor_regression.py -q`

    If this is a cloud session, stop here and defer the local refresh.
  </action>
  <verify>
    <automated>MISSING — checkpoint task; operator confirms local readiness</automated>
  </verify>
  <done>Operator confirms a real local baseline-refresh session is available.</done>
</task>

<task type="auto">
  <name>Task 4: Refresh the first real baselines and write `04-LOCAL-PROBE-RESULTS.md`</name>
  <read_first>
    - docs/refactor-regression.md
    - scripts/capture_refactor_regression.py
    - scripts/analyze_refactor_regression.py
    - examples/openclaw_demo.py
    - examples/openclaw_nav_autonomous.py
  </read_first>
  <behavior>
    - Capture at least one real direct-VLM run, one push-model OpenClaw run, and one autonomous OpenClaw run.
    - Use the analyzer on at least one baseline/candidate pair and record the result honestly.
    - Any threshold change made after live evidence must be explained in the local results file.
    - No raw secrets are pasted into the repo.
    - For the first workflow proof, baseline and candidate may be two captures
      from the same commit / same coordinates under different labels; record
      explicitly that this was a workflow-proof pair and that the expected
      analyzer result was pass.
  </behavior>
  <action>
    Run the first local baseline refresh and record it under
    `.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md`.

    Minimum evidence set:

    1. One real direct-VLM suite capture, for example `territory-vlm`
    2. One real push-model OpenClaw suite capture, for example `openclaw-demo`
    3. One real `openclaw-autonomous` capture
    4. One analyzer run comparing a baseline vs candidate pair

    The write-up must include:
    - date and host context
    - exact commands run (with env var placeholders, not secrets)
    - baseline/candidate capture-set labels used in those commands
    - the exact coordinate tuple used for each refreshed suite
    - artifact paths
    - the suites refreshed
    - whether the analyzer pair was same-commit workflow proof or a true
      before/after refactor comparison
    - analyzer outcome (`pass` / `fail`) and the specific threshold result
    - any threshold adjustment justified by live evidence

    If live evidence forces a threshold adjustment, update
    `scripts/analyze_refactor_regression.py` before marking the task done and
    rerun the focused pytest slice:

    ```bash
    env -i PATH=".venv/bin:/usr/bin:/bin" HOME=$HOME .venv/bin/pytest \
      tests/test_capture_refactor_regression.py \
      tests/test_analyze_refactor_regression.py -q
    ```
  </action>
  <verify>
    <automated>test -f /home/mi/ws/gogo/roboclaws/.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md && rg -n "Artifact paths|Analyzer outcome|openclaw-autonomous|openclaw-demo|territory-vlm" /home/mi/ws/gogo/roboclaws/.planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md</automated>
  </verify>
  <done>The first real baseline refresh is documented with commands, artifact paths, and analyzer outcomes.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Baseline/candidate analyzer ↔ operator decisions | The analyzer will decide whether a refactor is acceptable; bad pairing or bad thresholds make it untrustworthy. |
| Local probe evidence ↔ repo docs | The docs and local results file must describe only what was actually validated. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-08 | Reliability | Threshold policy | mitigate | Keep the threshold table explicit, per suite, synthetic-test covered, and adjustable only with recorded live evidence. |
| T-04-09 | Tampering | Row pairing | mitigate | Pair only on stable coordinates and fail loudly on missing baseline/candidate rows. |
| T-04-10 | Information Disclosure | Local evidence / docs | mitigate | Use env-var placeholders in docs and local-results notes; never paste secrets or large baseline artifacts into the repo. |

No `high`-severity threats; plan proceeds.
</threat_model>

<verification>
- `pytest tests/test_analyze_refactor_regression.py -q` exits 0.
- `docs/refactor-regression.md` exists and documents the operator workflow.
- `04-LOCAL-PROBE-RESULTS.md` records the first real baseline refresh and any threshold adjustments.
</verification>

<success_criteria>
- Maintainers can capture baselines, capture candidates, and compare them with one documented workflow.
- Phase 4 ends with at least one real local proof that the harness is usable on the actual stacks.
- Threshold policy is evidence-backed rather than hand-wavy.
</success_criteria>
