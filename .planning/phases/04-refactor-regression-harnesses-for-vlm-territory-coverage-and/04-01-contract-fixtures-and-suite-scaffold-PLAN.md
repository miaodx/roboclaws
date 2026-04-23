<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0423-autoplan-restore-20260423-205957.md -->
---
phase: 4
plan: 01
slug: contract-fixtures-and-suite-scaffold
type: execute
wave: 1
depends_on: []
files_modified:
  - roboclaws/regression.py
  - scripts/capture_refactor_regression.py
  - tests/fixtures/replay_summary_reference.json
  - tests/fixtures/refactor_regression_row_reference.json
  - tests/test_refactor_regression_contracts.py
  - tests/test_capture_refactor_regression.py
autonomous: false
requirements_addressed: [A-08]

must_haves:
  truths:
    - "Phase 4 has one shared suite/row vocabulary instead of ad-hoc per-script result shapes."
    - "Critical exact contracts are frozen with tiny fixtures/tests: replay summary required keys, prompt image order/labels, and the already-frozen OpenClaw trace/snapshot rules stay explicit."
    - "Stable pairing keys and common row fields are frozen explicitly, including a unique artifact path per capture so repeated runs never overwrite the evidence."
    - "The capture harness writes append-only rows and is monkeypatchable in tests via a suite registry."
    - "Plan 01 scaffolds how later plans call existing runners; it does not reimplement the example loops."
  artifacts:
    - path: "roboclaws/regression.py"
      provides: "Shared suite registry, stable pairing-key builder, and row helpers for refactor regression harnesses"
      contains: "class RegressionSuite"
    - path: "scripts/capture_refactor_regression.py"
      provides: "Thin capture CLI shell with registry-backed suite selection and append-only JSONL writing"
      contains: "--suite"
    - path: "tests/fixtures/replay_summary_reference.json"
      provides: "Frozen replay-summary required-key reference"
      contains: "\"summary\""
    - path: "tests/fixtures/refactor_regression_row_reference.json"
      provides: "Frozen required pairing-key/common-row contract for the regression harness"
      contains: "\"artifact_dir\""
  key_links:
    - from: "scripts/capture_refactor_regression.py"
      to: "roboclaws/regression.py"
      via: "registry-backed suite lookup and row normalization"
      pattern: "RegressionSuite"
    - from: "tests/test_refactor_regression_contracts.py"
      to: "tests/fixtures/replay_summary_reference.json"
      via: "required-key contract"
      pattern: "replay_summary_reference"
    - from: "tests/test_refactor_regression_contracts.py"
      to: "tests/fixtures/refactor_regression_row_reference.json"
      via: "required row contract"
      pattern: "refactor_regression_row_reference"
---

<objective>
Create the exact-contract and suite-scaffolding layer that the rest of Phase 4
builds on. After this plan, the phase has a frozen list of hard contracts, a
frozen common row contract, and a small, testable capture-harness shell ready
for real suites.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-CONTEXT.md
@.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-RESEARCH.md
@PLAN.md
@roboclaws/core/views.py
@roboclaws/core/replay.py
@tests/fixtures/trace_schema_reference.json
@tests/test_openclaw_mcp_server.py
@tests/test_openclaw_demo.py
@tests/test_openclaw_nav_autonomous.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add tiny contract fixtures and dedicated refactor-safety tests</name>
  <read_first>
    - roboclaws/core/views.py
    - roboclaws/core/replay.py
    - tests/fixtures/trace_schema_reference.json
    - tests/test_openclaw_mcp_server.py
    - tests/test_openclaw_demo.py
    - tests/test_openclaw_nav_autonomous.py
  </read_first>
  <behavior>
    - Freeze only stable contracts; do not snapshot volatile fields such as timestamps, wallclock totals, or real-model reasoning text.
    - Reuse existing targeted tests where they already pin a contract. Add dedicated Phase-4 tests only where an explicit fixture-backed contract is missing.
    - Keep the fixture tiny and human-reviewable.
  </behavior>
  <action>
    Add a small contract layer for the surfaces this phase exists to protect.

    Required work:

    1. Create `tests/fixtures/replay_summary_reference.json` capturing the
       required `replay.json` top-level `metadata` and `summary` keys that
       refactors must preserve.

    2. Create `tests/fixtures/refactor_regression_row_reference.json`
       capturing the required stable pairing/common row fields for every
       captured run:
       - `suite`
       - `backend`
       - `scene`
       - `seed`
       - `game`
       - `model`
       - `agents`
       - `variant` (present and nullable when not applicable)
       - `label`
       - `status`
       - `artifact_dir`
       - `run_id`
       - `captured_at`
       - `commit_sha`
       - `schema_version`

    3. Add `tests/test_refactor_regression_contracts.py` covering:
       - `image_labels_for_variant("map-v2+chase")` remains
         `("fpv", "map_v2", "chase")`
       - `build_prompt_images()` preserves FPV / map / chase ordering
       - `ReplayRecorder.save()` emits a `replay.json` whose required
         `metadata` and `summary` keys are a superset of the new fixture
       - row normalization emits a superset of
         `refactor_regression_row_reference.json`, including a nullable
         `variant` key, a unique `artifact_dir`, and the required run
         metadata fields
       - the existing `tests/fixtures/trace_schema_reference.json` is still
         treated as the source of truth for OpenClaw additive-vs-exact schema
         contracts

    4. Do NOT clone existing OpenClaw demo/autonomous tests into the new file.
       Instead, keep the new test focused on the cross-cutting contracts that
       Phase 4 needs to name explicitly.
  </action>
  <verify>
    <automated>cd /home/mi/ws/gogo/roboclaws && pytest tests/test_refactor_regression_contracts.py tests/test_openclaw_mcp_server.py -q</automated>
  </verify>
  <done>Phase 4 has an explicit, fixture-backed contract wall for replay summaries and prompt-image ordering.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create the shared regression module and thin capture CLI scaffold</name>
  <read_first>
    - examples/view_experiment.py
    - scripts/analyze_view_experiment.py
    - .planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-RESEARCH.md
  </read_first>
  <behavior>
    - The shared module is small: registry, stable coordinate helpers, JSONL append helper, and row-normalization helpers only.
    - The CLI is a shell around the registry, not a giant new execution framework.
    - Later plans must be able to monkeypatch the registry in tests without invoking real AI2-THOR or live providers.
    - Repeated captures of the same stable coordinates must append rows without overwriting prior artifacts.
  </behavior>
  <action>
    Create the base Phase-4 harness surfaces:

    1. Add `roboclaws/regression.py` with:
       - a small `RegressionSuite` dataclass
       - a registry keyed by suite name
       - helpers to build stable pairing coordinates
       - a helper to build unique per-run artifact directories beneath a
         stable coordinate root
       - append-only JSONL writing helpers
       - a small row-normalization helper that all later suites reuse

    2. Add `scripts/capture_refactor_regression.py` with the CLI shell for:
       - `--suite`
       - `--output-dir`
       - `--label <capture-set-name>`
       - `--scenes`
       - `--seeds`
       - `--agents`
       - `--steps`
       - `--model`
       - `--allow-local`

       At plan-01 scope the CLI only needs registry-backed orchestration,
       append-only row writing, and clean error messages for unknown or
       local-only suites. Real suites land in later plans. Require
       `<capture-set-name>` to be an immutable snapshot label such as
       `baseline-2026-04-23` or `candidate-dongxu-dev-0423`, not a permanent
       bucket reused across refreshes.

    3. Add `tests/test_capture_refactor_regression.py` using a fake suite
       registered entirely inside the test so the scaffold proves:
       - registry lookup works
       - rows append to `results.jsonl`
       - output dirs are created per suite / coordinate / run-id
       - rerunning the same coordinate yields distinct `artifact_dir` values
         instead of clobbering the previous capture
       - local-only suites refuse to run without the explicit override
  </action>
  <verify>
    <automated>cd /home/mi/ws/gogo/roboclaws && pytest tests/test_capture_refactor_regression.py -q</automated>
  </verify>
  <done>The Phase-4 scaffold exists and is testable without real runners.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Frozen contract fixtures ↔ future refactors | If the wrong fields are frozen, the harness either misses regressions or blocks harmless changes. |
| Suite scaffold ↔ later capture plans | The base registry and row helpers define the shape every later plan will extend. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-01 | Tampering | Contract fixtures | mitigate | Freeze only required keys and stable label ordering; keep volatile fields out of fixtures. |
| T-04-02 | Reliability | Suite scaffold | mitigate | Keep the base registry tiny and prove it with fake-suite tests before adding any real suites. |

No `high`-severity threats; plan proceeds.
</threat_model>

<verification>
- `pytest tests/test_refactor_regression_contracts.py tests/test_capture_refactor_regression.py -q` exits 0.
- The capture scaffold is thin, registry-backed, and append-only.
- Phase 4's exact contracts are explicit and reviewable.
</verification>

<success_criteria>
- The phase has a named contract wall instead of relying on scattered implicit knowledge.
- Later plans can add suites without inventing a new row schema each time.
- No runner logic has been duplicated yet.
</success_criteria>
