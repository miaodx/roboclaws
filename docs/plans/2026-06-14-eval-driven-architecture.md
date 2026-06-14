---
plan_scope: eval-driven-architecture
status: DRAFT
created: 2026-06-14
last_reviewed: 2026-06-15
implementation_allowed: false
source:
  - user request to make Roboclaws eval-driven and AI-native
  - intuitive-reduce-entropy selection packet
  - follow-up intuitive-reduce-entropy saturation audit
  - docs/research/08-agent-evaluation-harness-research.md
  - grill-with-docs-batch decision review accepted 2026-06-15
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - TODOS.md
  - docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md
  - docs/adr/0139-use-household-open-task-surface-with-presets.md
  - docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md
  - docs/research/README.md
  - docs/human/technical-design.md
  - docs/human/agent-task-command-taxonomy.md
  - docs/human/local-runtime.md
  - docs/human/molmospaces-settings.md
  - docs/human/ut_ci_design.md
  - docs/research/08-agent-evaluation-harness-research.md
  - docs/plans/2026-06-11-agent-validation-matrix-skill.md
  - docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md
---

# Eval-Driven Architecture

## Goal

Make evaluation a first-class Roboclaws architecture layer, not a collection of
harness recipes and report artifacts. The target repo should make future
agentic development flow through versioned eval suites:

```text
eval suite
  -> eval sample
  -> environment reset
  -> agent trial
  -> trace and artifacts
  -> graders
  -> aggregate metrics
  -> failure replay and regression samples
```

This should let Roboclaws answer product-quality questions such as:

- Did cleanup capability improve or regress across a versioned sample set?
- Does an agent succeed reliably across repeated trials, not just once?
- Did a prompt, skill, MCP tool, backend, or provider change improve behavior
  without leaking private scorer truth?
- Which failure class blocks the next improvement: perception, map
  actionability, tool arguments, policy, provider/runtime, or final world
  state?

## Why Now

Recent cleanup work left the repo in a cleaner architectural state:

- public launch axes are centered on `surface`, `world`, `backend`, `intent`,
  `agent_engine`, `provider_profile`, `evidence_lane`, and `camera_labeler`;
- retired AI2-THOR/direct-VLM public surfaces and hosted VLM-direct sidecars are
  no longer active architecture drivers;
- household-world and planner-proof are the current product surfaces;
- private scorer truth and public agent evidence are already separated;
- `agent-validation-matrix` can already select validation gates from a plan or
  diff.

The remaining entropy is that `harness`, `verify`, `agent-validation-matrix`,
CI gates, report artifacts, and private scorers each solve part of the problem,
but no source of truth says evaluation is the product architecture loop.

## Current State

Implemented foundations:

- `just run::surface ...` is the user-facing product run grammar.
- `just agent::harness agent-validation recommend|execute ...` chooses
  relevant validation gates from plan, diff, or explicit axes.
- Launch plans already carry intent-level evaluation metadata through
  `roboclaws.launch.evaluation`.
- Serious runs already emit `trace.jsonl`, `agent_view.json`,
  `run_result.json`, `goal_contract.json`, `runtime_metric_map.json` when
  relevant, model metrics, and `report.html`.
- ADR-0003 and current reports preserve the public/private scorer boundary.

Current gaps:

- no versioned eval-suite concept;
- no durable eval sample schema;
- no `eval_trial` / `eval_result` packet with full identity and failure class;
- no standard state, trajectory, privacy, and efficiency grader taxonomy;
- no standard `pass@k` or `pass^k` aggregation;
- no failure-to-regression-sample loop;
- architecture docs still present evaluation mostly as artifacts and gates.
- some current human docs still mix active launch axes with older private
  driver/profile or validation-required route terminology;
- parked TODOs still include retired AI2-THOR/game-era benchmark work that
  should either be deleted or re-expressed as household eval-suite work;
- research index entries for older AI2-THOR-era reports need clearer historical
  status so they are not mistaken for current strategy.
- `goal_contract.tool_plan` and a few live-agent hints still mention
  `fixture_hints` as if it were a current cleanup MCP tool, while the cleanup
  MCP server contract rejects that tool;
- Agibot map-build still exposes `fixture_hints` as an active MCP tool, so the
  accepted direction is to converge it away from fixture-hints-first active MCP
  semantics instead of preserving a permanent exception;
- local runtime docs still point at some legacy-shaped output roots, which will
  become more confusing once eval outputs exist.

## Architecture Decision

Roboclaws should use four distinct layers:

```text
Product run
  just run::surface ...

Validation matrix
  just agent::harness agent-validation ...
  Selects which gates this plan/diff must run.

Eval suite
  Versioned product capability benchmark owned by the repo.
  Runs samples, trials, graders, and aggregate metrics.

Harness recipes
  Lower-level runners and specialist probes used by validation/eval/product
  flows, not the conceptual source of truth.
```

The key distinction:

- `agent-validation-matrix` answers "what should this change validate?"
- `evals/` answers "is this agent capability improving over time?"
- `harness::*` answers "how do we execute this specific low-level proof?"

ADR-0140 records this as the durable architecture decision. This plan owns the
execution sequence, schemas, commands, tests, and cleanup work.

## Target Vocabulary

Use these terms consistently:

- `eval_suite`: versioned group of samples, thresholds, and required graders.
- `eval_sample`: one task setup with public inputs, private goal reference,
  allowed agents, seeds/trials, and grader list.
- `eval_trial`: one execution of one sample by one agent identity.
- `eval_result`: machine-readable packet with identity, scorer outputs,
  aggregate status, artifacts, and limitations.
- `grader`: deterministic, model, or human scoring unit.
- `outcome`: final world/map/task state, not the agent's completion claim.
- `trajectory`: ordered MCP/tool and state-transition evidence.
- `failure_class`: normalized reason a trial failed.

## Target Layout

Start repo-native. Do not add Inspect AI or another eval framework until the
first internal suite proves what framework help is actually needed.

```text
evals/
  household_world/
    suites/
      smoke_regression.yaml
      cleanup_capability.yaml
      map_build_consumer.yaml
      open_ended_goals.yaml
    samples/
      cleanup/
      map_build/
      open_ended/
    README.md

roboclaws/
  evals/
    models.py
    runner.py
    graders/
      artifacts.py
      state.py
      trajectory.py
      privacy.py
      efficiency.py
    reports.py
```

The exact module layout may change during implementation, but the concepts
should remain explicit and visible.

## Eval Result Identity

Every `eval_result` must record enough identity to make two results
comparable:

- suite id and version;
- sample id and version;
- trial id and repetition index;
- surface, intent, preset, world, backend, evidence lane, camera labeler;
- scenario setup, seed, prompt or goal contract hash;
- agent engine and runner class;
- provider profile and model when live;
- skill name and prompt source when known;
- MCP profile and tool surface;
- runtime, hardware, network, and local/live limitations when known;
- budgets: steps, time, token, cost, retry/repetition;
- artifact schema versions.

Missing identity fields should be explicit `unavailable` or `not_applicable`,
never silently omitted when relevant.

## Grader Stack

Initial deterministic graders:

- artifact grader: required artifacts exist and have expected schemas;
- state/outcome grader: private final world state satisfies task predicates;
- trajectory grader: MCP/tool sequence and arguments satisfy necessary process
  constraints without forcing one canonical path;
- privacy grader: private scorer truth does not appear in agent-facing
  artifacts or MCP profile metadata;
- efficiency grader: tool calls, retries, latency, model work, and cost.

Advisory graders:

- model rubric grader for open-ended semantic satisfaction;
- human review label for ambiguous reports.

Advisory graders must not override deterministic safety/privacy failures.

## Predicate Direction

Do not build a large generic predicate language in the first slice. Start with
small household predicates:

- `object_in_acceptable_destination(object_id)`;
- `object_not_disturbed(object_id)`;
- `runtime_map_contains_public_anchor(anchor_id)`;
- `agent_observed_before_acting(object_handle)`;
- `private_truth_not_in_agent_view(field_path)`;
- `planner_proof_attached_for_action(action_id)`.

These predicates can support cleanup, map-build, open-ended goals, and future
planner-proof/real-robot evals without turning the first phase into a DSL
project.

## Failure Taxonomy

Normalize at least these failure classes:

- `artifact_missing`;
- `environment_blocked`;
- `agent_no_completion_claim`;
- `private_goal_not_satisfied`;
- `partial_progress_only`;
- `trajectory_policy_violation`;
- `private_truth_leak`;
- `tool_argument_invalid`;
- `tool_noop_or_repeated_failure`;
- `perception_miss`;
- `map_actionability_failure`;
- `planner_proof_missing_or_failed`;
- `model_or_provider_unavailable`;
- `budget_exhausted`;
- `grader_inconclusive`;
- `harness_bug_unclassified`.

Unknown runtime/tool failures should default to `harness_bug_unclassified`
until classified. This follows the Cursor-style discipline: unknown harness
errors are product infrastructure debt, not a vague agent failure.

## Metrics

Initial aggregate metrics:

- `pass@1`: first-trial success rate;
- `pass@k`: success within k attempts, useful for retry/rescue analysis;
- `pass^k`: reliability across k repeated trials, useful for product trust;
- restoration or progress rate;
- disturbance count;
- trajectory-policy violation count;
- private-truth leak count;
- model/tool work per successful task;
- blocked/failed/inconclusive counts by failure class.

## Additional Entropy Cleanup Integrated Into This Plan

The follow-up reduce-entropy saturation pass found several non-code surfaces
that should be cleaned in the same flow. They are not separate product efforts;
they are prerequisites for making the eval-driven architecture unambiguous to
future humans and agents.

### A. Technical Design Agent-Engine Drift

`docs/human/technical-design.md` still lists OpenClaw Gateway and script runner
in the current Agent Strategy. Current launch metadata removed public
`script-runner`, and `openclaw-gateway` is validation-required rather than a
normal public engine.

Required cleanup:

- align `technical-design.md` with `ARCHITECTURE.md`,
  `docs/human/agent-task-command-taxonomy.md`, and
  `roboclaws/launch/agent_engines.py`;
- describe OpenClaw as a validation-required maintainer route;
- avoid presenting script-style proof paths as public agent engines.

### B. Molmo Runbook Private Driver/Profile Drift

`docs/human/molmospaces-settings.md` still contains a large section centered on
private `driver`, `profile`, `codex-live`, `claude-live`, and `molmo::*`
convenience recipes. Those recipes can remain as maintainer internals, but they
should not read as the primary user path.

Required cleanup:

- make canonical `just run::surface ... agent_engine=... evidence_lane=...`
  examples the first path;
- demote `molmo::*`, `driver=`, `profile=`, and lower `harness::*` recipes to
  debugging or historical-maintainer sections;
- keep OpenClaw guarded and validation-required in this doc.

### C. Parked TODOs From Retired Surfaces

`TODOS.md` still contains parked work that references retired AI2-THOR/game-era
surfaces such as photo, territory, and `examples/games/territory_game.py`. The
active code scan no longer finds those example paths.

Required cleanup:

- delete TODOs that only make sense for retired surfaces;
- rewrite any still-useful idea as household-world or eval-suite work;
- fold "weekly coding-agent model/settings benchmark" into this eval-driven
  architecture plan if it becomes a suite-level future slice.

### D. Research Index Historical Status

`docs/research/README.md` lists early research reports whose conclusions were
correct for their time but are now superseded by the household-world direction.
The report files should remain as history, but the index needs stronger status
labels.

Required cleanup:

- add status or wording that marks AI2-THOR-era research as historical or
  superseded when appropriate;
- keep current reports, including the eval research note, visibly current;
- avoid changing historical report bodies solely for wording cleanup.

### E. Eval Plan Visibility After Approval

This draft plan should not become current status until approved. Once approved
or selected for execution, update the current orientation surfaces.

Required cleanup after approval:

- update `STATUS.md` current focus/source links if this becomes active work;
- add a human-doc link to any new evaluation guide;
- keep `docs/plans/2026-06-14-eval-driven-architecture.md` as the canonical
  pre-GSD source until execution moves into `.planning/`.

### F. Goal Contract And Cleanup MCP Tool-Plan Drift

`roboclaws/launch/goals.py` still puts `fixture_hints` in
`GoalContract.tool_plan` for cleanup, map-build, and open-ended household
intents. The current cleanup MCP contract rejects `fixture_hints` as a removed
public tool, and tests assert that it is absent from cleanup MCP tool names.
The same drift appears in at least one live Agent SDK continuation hint and in
a cleanup MCP response-augmentation branch that is now unreachable for that
server.

Required cleanup:

- remove fixture-hints-first wording from household cleanup/open-ended
  goal-contract tool plans;
- express those plans in terms of Base Navigation Map, Runtime Metric Map,
  public semantic anchors, target-query resolution, observation, action, and
  `done`;
- update live-agent retry/continuation hints and harness comments so cleanup
  agents are not instructed to call a removed tool;
- remove or narrowly gate unreachable cleanup MCP `fixture_hints` augmentation
  code;
- preserve legitimate `fixture_hints` artifact fields used by historical
  reports, map bundles, visual-grounding request payloads, and current Agibot
  map artifacts;
- add focused tests that cleanup/open-ended goal contracts and active cleanup
  hints do not advertise `fixture_hints` as a callable cleanup MCP tool.

### G. Agibot Map-Build Fixture-Hints Boundary

Agibot map-build is not identical to cleanup MCP today:
`roboclaws/household/agibot_map_build_mcp_server.py` still registers
`fixture_hints` as an active public map-build tool, and both the CLI server
banner and Codex Agibot map-build kickoff prompt say to call `metric_map` and
`fixture_hints` first. Meanwhile
`docs/human/mcp-skills-and-semantic-profiles.md` says `metric_map` is the
current map-reading path and active skills should avoid a fixture-hints-first
tool habit.

Required cleanup:

- converge Agibot map-build toward metric-map/current-map evidence and
  target-query style semantics rather than preserving a permanent
  fixture-hints-first MCP habit;
- keep `fixture_hints` as an artifact/internal compatibility field where map
  bundles, visual-grounding requests, and historical reports still need it;
- update the Agibot map-build server, prompts, checkers, and report
  policy-event names together;
- make the boundary visible to eval graders so a cleanup `fixture_hints` call
  is a trajectory violation while artifact/internal compatibility fields are
  not misclassified as agent tool use.

### H. Local Runtime Output Path Drift

`docs/human/local-runtime.md` still lists typical report roots such as
`output/household/semantic-map-build/<driver>-*/` and
`output/household/household-cleanup/<driver>-*/`. Current public examples route
through `just run::surface`, often emit under `output/molmo/...` or an explicit
`output_dir=...`, and older task/profile names are documented as legacy
compatibility details.

Required cleanup:

- update local-runtime output guidance around current surface/preset/eval
  artifact roots;
- distinguish product run output, validation-matrix output, future eval-suite
  output, and historical report roots;
- avoid implying that legacy `semantic-map-build` or `household-cleanup` output
  roots are the default place to look for new eval evidence.

### Saturation Result

The follow-up open-ended reduce-entropy loop passed the materiality gate with
seven candidates and a saturated quota warning: requesting more groups would
turn low-impact polish into standalone work. The selected directions are:

- first-class eval architecture layer;
- launch-axis documentation drift;
- retired-surface parked work;
- research-index historical status;
- cleanup `fixture_hints` active-contract drift;
- Agibot map-build `fixture_hints` convergence;
- local-runtime output path drift.

## Implementation Slices

### Slice 0: Architecture And Docs

Status: planning candidate.

Scope:

- update `ARCHITECTURE.md` to add eval suite as a first-class architecture
  layer;
- add or update human docs explaining product run vs validation matrix vs eval
  suite vs harness recipe;
- align `docs/human/technical-design.md` with current agent-engine status;
- demote older private `driver`/`profile` and `molmo::*` guidance in
  `docs/human/molmospaces-settings.md`;
- clean parked TODOs that reference retired AI2-THOR/game-era surfaces or
  rewrite them as household eval-suite work;
- mark older research index entries as current, historical, or superseded in
  `docs/research/README.md`;
- align `docs/human/local-runtime.md` with current product, validation, and
  future eval output roots;
- update `README.md` only if needed to avoid implying that demo matrix is the
  primary eval surface;
- update `STATUS.md` only if this plan becomes the active focus;
- cross-link the research note.

Acceptance:

- a new agent can read architecture docs and explain where eval suites fit;
- a new agent does not see `script-runner`, OpenClaw Gateway, `driver=`, or
  `profile=` as ordinary public product axes;
- parked work no longer points maintainers at deleted AI2-THOR/game example
  paths;
- research index clearly distinguishes historical research from current
  decision context;
- docs preserve the current public launch contract;
- docs distinguish product run output, validation matrix output, eval-suite
  output, and historical roots;
- no command behavior changes.

### Slice 1: Active Contract Boundary Cleanup

Status: planning candidate.

Scope:

- update `GoalContract.tool_plan` for cleanup, map-build, and open-ended
  household intents so it does not advertise removed cleanup MCP tools;
- update live-agent continuation hints and active cleanup MCP comments that
  still say to call `fixture_hints`;
- remove or gate unreachable cleanup MCP response augmentation for
  `fixture_hints`;
- converge Agibot map-build active prompts and MCP shape away from
  fixture-hints-first semantics while preserving artifact compatibility;
- add focused tests for goal-contract tool plans, cleanup MCP tool names, and
  Agibot map-build convergence.

Acceptance:

- cleanup and open-ended goal contracts no longer instruct agents to call
  `fixture_hints`;
- cleanup MCP tests still prove `fixture_hints` is rejected as a removed tool;
- live cleanup retry hints point agents at `metric_map`, public anchors,
  observation, target-query/action tools, and `done`;
- Agibot map-build active agent instructions and MCP policy no longer require a
  fixture-hints-first tool habit;
- historical artifact/report/bundle compatibility is preserved.

### Slice 2: Eval Schema And Result Packet

Status: planning candidate.

Scope:

- define `eval_suite`, `eval_sample`, `eval_trial`, and `eval_result` schemas;
- define result identity and failure taxonomy;
- add focused tests for schema validation and result serialization;
- add sample fixtures for direct-runner only.

Acceptance:

- sample and result packets round-trip in tests;
- missing relevant identity fields are represented explicitly;
- no live provider or simulator proof is required yet.

### Slice 3: Deterministic Household Eval Runner

Status: planning candidate.

Scope:

- implement a repo-native runner that lowers eval samples to existing product
  runs or direct deterministic calls;
- support the first `smoke_regression` or `cleanup_capability` suite;
- write `output/evals/<suite>/<stamp>/eval_results.json` and a simple
  `eval_report.html`;
- implement artifact, privacy, state/outcome, and basic trajectory graders.

Acceptance:

- one deterministic suite runs without provider keys;
- output links to underlying run artifacts;
- failures carry normalized `failure_class`;
- existing `just run::surface` and `agent-validation-matrix` contracts remain
  unchanged.

### Slice 4: Map-Build And Open-Ended Eval Coverage

Status: planning candidate.

Scope:

- add `map_build_consumer` samples that score Runtime Metric Map output and a
  cleanup consumer with `runtime_map_prior`;
- add initial open-ended goal samples with deterministic artifacts and advisory
  rubric hooks;
- keep LLM/human rubric advisory until calibrated.

Acceptance:

- map-build eval catches missing or unusable runtime-map artifacts;
- open-ended eval distinguishes completion claim, artifact readiness, and
  advisory semantic satisfaction.

### Slice 5: Live-Agent Repetition And `pass^k`

Status: planning candidate.

Scope:

- run selected eval samples with Codex CLI, Claude Code, or OpenAI Agents SDK
  when local provider/runtime requirements are available;
- record `pass@k` and `pass^k`;
- integrate model-call metrics and provider timing where available;
- classify provider/runtime blocks separately from agent behavior failures.

Acceptance:

- live-agent eval results identify provider/model/runtime conditions;
- repeated trials aggregate without hiding individual failures;
- blocked local/live requirements are honest, not silently downgraded.

### Slice 6: Failure Replay And Regression Loop

Status: planning candidate.

Scope:

- add a lightweight path from report review or failed eval result to a new or
  updated regression sample;
- document the human review labels that can promote a failure into the suite;
- keep generated outputs out of git while storing durable sample definitions.

Acceptance:

- a failed report can be turned into a deterministic or live regression sample;
- the sample records which private truth remains scorer-only;
- regression samples are visible in suite manifests.

## Non-Goals

- Do not replace `just run::surface`.
- Do not remove existing `harness::*` recipes in the first pass.
- Do not make `agent-validation-matrix` own robot behavior or eval scoring.
- Do not add a third-party eval framework before the repo-native first slice.
- Do not make LLM judges authoritative for cleanup/private safety failures.
- Do not require provider-backed live agents for the first deterministic eval
  suite.
- Do not build a general household predicate DSL in the first phase.

## Verification Plan

Deterministic gates for implementation slices:

```bash
ruff check .
ruff format --check .
./scripts/dev/run_pytest_standalone.sh -q tests/unit
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools
```

Focused integration gates once eval runner exists:

```bash
just agent::harness agent-validation recommend \
  plan=docs/plans/2026-06-14-eval-driven-architecture.md \
  budget=focused
```

Product/eval proof once eval command exists:

```bash
just agent::eval suite=smoke_regression budget=smoke
```

If the public command name changes during implementation, update this plan and
the human docs together. The final proof must include one deterministic eval
suite run that writes an eval result and report.

Local/live/manual proof for later slices:

```bash
just agent::eval suite=cleanup_capability agent_engine=codex-cli budget=focused
```

This proof is blocked unless provider keys, Docker coding-agent runtime, and
the required simulator/backend are available.

## Documentation Updates

Required when implementation begins:

- `ARCHITECTURE.md`: add eval-driven architecture layer and artifact flow.
- `README.md`: clarify demo matrix versus eval suites if both are visible.
- `STATUS.md`: update current focus only after this plan is approved or starts
  execution.
- `docs/human/technical-design.md`: align current agent-engine strategy with
  launch metadata; keep OpenClaw validation-required and keep script-style proof
  paths out of public agent-engine wording.
- `docs/human/agent-task-command-taxonomy.md`: explain product run, validation
  matrix, eval suite, and harness recipe boundaries.
- `docs/human/local-runtime.md`: update output root guidance for product runs,
  validation matrices, eval suites, and historical artifacts.
- `docs/human/molmospaces-settings.md`: demote private driver/profile and
  `molmo::*` convenience recipes under maintainer/debugging guidance.
- `docs/human/ut_ci_design.md`: classify eval suites in gate levels.
- `docs/human/README.md`: add any new evaluation doc to the human review
  surface.
- `docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md`: durable
  decision for product run, validation matrix, eval suite, and harness recipe
  boundaries.
- `docs/research/README.md`: mark older research reports as current,
  historical, or superseded where needed.
- `TODOS.md`: remove or rewrite parked work tied only to retired
  AI2-THOR/game-era surfaces.

Potential new doc:

- `docs/human/evaluation.md`: concise human-facing eval suite reference.

## Preflight Contract

Preflight status: DRAFT

Task source: user prompt plus research and reduce-entropy packet

Canonical source: `docs/plans/2026-06-14-eval-driven-architecture.md`

Route: durable `intuitive-flow`

Goal: make Roboclaws eval-driven by adding a first-class eval-suite
architecture layer while preserving current product launch and validation
surfaces.

Scope:

- update architecture and human docs;
- clean adjacent stale documentation and parked-work surfaces found by the
  follow-up reduce-entropy audit;
- define eval suite/sample/trial/result vocabulary and schemas;
- implement deterministic household eval first;
- add live-agent repetitions only after deterministic suite semantics are
  stable.

Non-goals:

- no third-party eval framework adoption in the first slice;
- no removal of existing harness recipes in the first slice;
- no live-provider requirement for deterministic eval foundation;
- no authoritative LLM judge for private scorer or safety failures.
- first eval facade is `just agent::eval ...`;
- Agibot map-build converges away from fixture-hints-first active MCP
  semantics.

Context:

- must-read: `ARCHITECTURE.md`, `README.md`, `docs/human/agent-task-command-taxonomy.md`, `docs/human/ut_ci_design.md`, `docs/research/08-agent-evaluation-harness-research.md`, `docs/plans/2026-06-11-agent-validation-matrix-skill.md`
- useful: `docs/human/technical-design.md`, `docs/human/molmospaces-settings.md`, `docs/research/README.md`, `TODOS.md`, `roboclaws/launch/evaluation.py`, `roboclaws/launch/catalog.py`, `roboclaws/launch/agent_engines.py`, `just/harness.just`, `skills/agent-validation-matrix/SKILL.md`
- active-contract cleanup: `roboclaws/launch/goals.py`, `roboclaws/agents/prompts/household_cleanup.py`, `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`, `roboclaws/household/realworld_mcp_server.py`, `roboclaws/household/agibot_map_build_mcp_server.py`, `roboclaws/cli/agibot_map_build_agent_server.py`, `scripts/molmo_cleanup/run_live_codex_agibot_map_build.py`
- avoid-unless-needed: historical `.planning/**`, old AI2-THOR/direct-VLM records, generated `output/**`

Acceptance:

- SUCCESS: architecture docs define eval suite as first-class; schemas and
  deterministic eval runner exist; at least one deterministic household eval
  suite runs and writes machine-readable result plus report; adjacent docs and
  parked-work surfaces no longer point future agents at retired public axes;
  active cleanup contracts no longer advertise `fixture_hints` as a callable
  cleanup MCP tool.
- BLOCKED_NEEDS_LOCAL_VALIDATION: live-agent `pass^k` proof until provider,
  Docker, simulator, and budget are available.
- INTERMEDIATE_ONLY: docs/schema-only checkpoint if implementation is split.
- No regressions: existing `run::surface`, `agent-validation-matrix`, and
  current harness recipes continue to work; OpenClaw remains
  validation-required until off-work-network proof exists.

Verification:

- deterministic: `ruff check .`; `ruff format --check .`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools`
- integration: `just agent::harness agent-validation recommend plan=docs/plans/2026-06-14-eval-driven-architecture.md budget=focused`
- product-run: deterministic eval suite command once introduced
- local-live-manual: live-agent eval repetition only in Slice 5
- optional: full `just agent::verify ci-required`

Execution:

- main: supervise architecture and acceptance; keep eval vocabulary coherent
- worker: none required initially
- worker-goal: none

To execute: ask explicitly to execute
`docs/plans/2026-06-14-eval-driven-architecture.md` with intuitive-flow.

Review: 2026-06-15 grill batch accepted the command facade, Agibot convergence,
and ADR routing decisions. Implementation still needs an explicit execute/go
ahead request.
