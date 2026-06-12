---
plan_scope: open-ended-household-default-architecture
status: PARTIALLY_IMPLEMENTED
created: 2026-06-12
last_reviewed: 2026-06-13
implementation_allowed: true
compatibility_policy: forward-only; no backward compatibility required
source:
  - user request to make open-ended household tasks the default architecture
  - intuitive-reduce-entropy discovery loop
  - architecture zoom-out and engineering-review frame
related_context:
  - README.md
  - ARCHITECTURE.md
  - docs/human/mcp-skills-and-semantic-profiles.md
  - docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md
  - docs/plans/2026-06-11-open-ended-proof-status.md
  - docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md
  - docs/adr/0139-use-household-open-task-surface-with-presets.md
---

# Open-Ended Household Default Architecture

## Implementation Status

First public-contract slice implemented on 2026-06-12 and locally verified on
2026-06-13 CST:

- `surface=household-world` now defaults to the no-preset household open-task
  contract.
- `preset=cleanup` and `preset=map-build` select the existing cleanup and
  map-build internal intent policies through a small household preset registry.
- Open-task routes use the `household-open-task` skill; cleanup routes use
  `molmo-realworld-cleanup`.
- Required capabilities are preset/skill-scoped: no-preset open tasks and
  map-build require world+episode, while cleanup adds manipulation.
- Operator-console no-preset selection ids use `open-task`; cleanup/map-build
  selection ids use their preset names.
- OpenAI Agents SDK has an enabled no-preset open-task route and validation
  matrix gate.
- Active docs and ADR-0139 describe the public command contract as
  `surface + prompt + optional preset`.

Verified product evidence for this slice:

- `preset=cleanup` direct product gate passed with report:
  `output/agent-validation-matrix/20260612T182533Z/gates/household-direct-world-oracle-product/run/0613_0231/seed-7/report.html`.
- `preset=map-build` direct product gate passed with Runtime Metric Map and
  report:
  `output/agent-validation-matrix/20260612T182533Z/gates/direct-map-build-world-oracle/run/0613_0233/seed-7/report.html`.
- No-preset Codex open-task product gate passed with `done`, an open-ended
  completion claim, `run_result.json`, model usage metrics, and report:
  `output/agent-validation-matrix/20260612T182533Z/gates/codex-open-task-world-oracle/run/0613_0235/seed-7/report.html`.
- No-preset OpenAI Agents SDK open-task product gate reached the MCP server but
  stopped before robot action with upstream `provider_transient_failure`
  (`502 bad_response_status_code`) from the `codex-env` provider route:
  `output/agent-validation-matrix/20260612T182533Z/gates/openai-agents-sdk-open-task/run/0613_0239/seed-7/live_status.json`.

Remaining required proof before this plan is fully implemented:

- Re-run the no-preset OpenAI Agents SDK product gate when the provider route is
  healthy; current status is `BLOCKED_NEEDS_LOCAL_VALIDATION` on external
  provider availability, not on deterministic launch-contract behavior.
- Runtime/server naming cleanup and task-neutral artifact schema replacement
  remain parked follow-up slices.

## Current Finding

The repo already has most of the right public vocabulary for household goals,
but the current `intent=` axis is too heavy for the desired direction:

```text
surface=household-world
  -> household open-task contract
  -> prompt=... by default
  -> optional preset=cleanup | map-build | ...
  -> agent_engine=codex-cli | claude-code | openai-agents-sdk | direct-runner
  -> evidence_lane + optional camera_labeler
  -> MCP public household capabilities
  -> report/checker artifacts
```

The target shape is stronger than "make `intent=open-ended` another
first-class option." Open-ended household task execution should become the
base contract selected by `surface=household-world`. Cleanup, map-build, and
future repeated tasks should be compressed behind optional `preset=` entries,
not exposed as peer public intents or as several new public axes.

Today, the implemented default path is still cleanup-heavy. Open-ended runs
exist and have intent-aware terminal status, but they are frequently lowered
through cleanup implementation names, cleanup skills, cleanup server aliases,
cleanup checker/report schemas, and cleanup validation gates. This creates real
friction for future household tasks such as "I am thirsty, find something to
drink", "take useful photos", "inspect this room", "find my mug", or later
robot-backed goal execution.

The target architecture should make open-ended household work the default
mental model for Coding Agent and Agent SDK routes. Cleanup remains important,
but it should be one constrained preset on top of the household open-task
contract, not the implicit parent of every future task.

## Accepted Direction To Review

This document is not execution approval. It records the recommended
architecture packet for review, grill-batch, and preflight.

Recommended direction:

- Make `surface=household-world` resolve to one open household task contract
  for live agent routes. A natural-language `prompt=` should be the primary
  way to state the goal.
- Demote `cleanup`, `map-build`, and future named jobs from peer public intents
  into optional `preset=` entries.
- Let each preset registry row own its default skill, capability requirements,
  completion policy, evaluation policy, report profile, scenario setup, and
  validation gates.
- Model cleanup evaluation, generated mess relocation, cleanup gates, and
  cleanup-specific reports behind `preset=cleanup`.
- Model map evidence sweeps and downstream Runtime Metric Map / Actionable
  Semantic Map Snapshot production behind `preset=map-build`.
- Split task-neutral household prompt/skill scaffolding from the current
  cleanup skill so open-ended work does not need cleanup-negation rules.
- Make required capabilities preset/skill-scoped instead of surface-heavy.
- Promote OpenAI Agents SDK open-ended support from disabled route to an
  explicit experimental/proven base household route only after a real or smoke
  evidence gate exists.
- Migrate active in-repo routes, tests, docs, skills, and reports forward.
  Historical cleanup-named artifacts and command shapes are not compatibility
  constraints.

## Base Definition And Cross-Scene Examples

This plan should not add a mandatory new public layer. The target is to make
`surface` the domain contract selector and use optional `preset` entries to
replace the overgrown peer `intent=` axis. `preset` is a compression mechanism
for known tasks, not a required axis for every natural-language run.

Recommended split:

- **Robot episode base**: an internal reusable protocol for `prompt`, public
  agent view, MCP trace, `done`, `blocked_capability`, artifacts, reports, and
  provider/runtime telemetry. This is shared code/schema, not an operator-facing
  product taxonomy.
- **Surface-owned domain open-task contract**: the base contract selected by
  one surface, such as `household-world` or a future `retail-store`. It owns
  domain language, public context, capability boundaries, private-data
  exclusions, completion semantics, and evidence/report expectations for that
  scene family.
- **Preset registry row**: optional typed configuration for repeated or
  benchmarked jobs on top of a surface. A preset owns the skill, required
  capabilities, completion/evaluation policy, report profile, allowed scenario
  setup, and validation gates. Ad-hoc goals should not need a preset.

Example target shapes:

```text
surface=household-world
  prompt="我渴了，帮我找些解渴的东西"
  -> household open-task contract
  -> default agent-declared completion with public evidence

surface=household-world
  preset=cleanup
  scenario_setup=relocate-cleanup-related-objects
  -> household open-task contract
  -> registry row: cleanup skill, manipulation required, cleanup-score,
     cleanup report profile

surface=household-world
  preset=map-build
  -> household open-task contract
  -> registry row: map-building skill, map-evidence, map report profile

surface=retail-store
  prompt="帮我找到一瓶常温矿泉水"
  -> retail open-task contract
  -> default agent-declared completion with public evidence

surface=retail-store
  preset=shelf-audit
  -> retail open-task contract
  -> registry row: shelf-audit skill, shelf-compliance, audit report profile
```

Create a new domain base when the public context, capability boundary,
private-data boundary, safety rule, or evaluation/report semantics are
different enough that reusing an existing surface would make future agents
learn the wrong nouns. Household examples center rooms, furniture,
receptacles, loose objects, search, inspection, and cleanup. Retail examples
would center aisles, shelves, SKUs, price tags, customer-safe areas, stock
state, spill checks, product search, and shelf audit. Both can share the robot
episode base without forcing retail to inherit household cleanup vocabulary.

## Chosen Entropy-Reducing Pattern

Use one pattern: **surface-owned open-task contract plus optional preset
registry**.

`surface` selects the domain contract. For household, that means the system
loads household language, household public map context, household private-data
boundaries, household open-task prompt scaffolding, household capability
allow-list, and household evidence/report semantics. For a future retail
surface, the same robot episode base can be reused, but the selected domain
contract would load retail language, retail map/product context, retail
private-data boundaries, retail capabilities, and retail evidence/report
semantics.

`preset` is the only compression layer above the surface contract. It is a
small registry row for known repeated jobs such as `cleanup`, `map-build`, or
future `shelf-audit`. Internally, a preset may point to a skill, required
capabilities, completion policy, evaluation policy, report profile, allowed
scenario setup, and validation gates. Those fields should not become separate
operator-facing axes unless a future product need proves that one axis must vary
independently.

Implementation may still use small policy functions or validators behind the
registry row. That is an implementation detail, not a second architecture
pattern.

Patterns to avoid:

- A class inheritance tree such as `OpenTask -> HouseholdTask -> CleanupTask`.
  It encourages framework gravity and hides the actual public contract in code
  structure.
- Mandatory public axes for every run. If operators must always type
  `preset`, evaluation policy, skill, and report profile separately, this plan
  has added ceremony instead of removing entropy.
- A generic workflow engine before there are several proven presets with real
  shared behavior.
- Cross-domain reuse by vocabulary inheritance. A future retail scene should
  reuse the robot episode base and capability/profile machinery, not household
  cleanup nouns.
- MCP mega-tools such as `do_cleanup`, `do_open_task`, or `do_shelf_audit`
  unless the MCP promotion rule is satisfied and trace semantics remain
  visible.

## Grill-Batch Decisions

### Batch 1: Default Contract And Deletion Boundary

Accepted:

- `surface=household-world` should default to open-ended household work for all
  agent engines. Cleanup and map-build should be explicit selections, not the
  silent default.
- Do not rename or remove all cleanup-shaped runtime/server paths in the first
  implementation slice. First prove the open-ended default, prompt/skill
  selection, capability metadata, and validation gates; then do a second
  forward-only runtime/server naming cleanup.
- Wire deterministic OpenAI Agents SDK open-ended route/gate support in the
  first slice, but treat the live SDK run as a local/provider validation gate.

### Batch 2: Base Task Contract

Accepted:

- Do not keep `cleanup`, `map-build`, and `open-ended` as peer public
  household intents in the target architecture.
- Make open-ended household execution the single base task contract for
  `surface=household-world`.
- Represent cleanup, map-build, search, inspection, and future repeated jobs as
  optional `preset=` entries layered over that base contract.
- Keep goal/evaluation policies, required capabilities, report profiles, and
  default skills inside the preset registry row instead of exposing them as
  separate public axes.
- Because backward compatibility is not required, active cleanup-shaped public
  commands, route ids, artifact writers, skill names, and tests may be
  migrated or removed instead of shimmed.

Terminology clarification:

- In the original candidate text, "first-class intent" meant a named public
  launch contract such as `intent=cleanup`, with its own checker/evaluation
  policy, docs, routes, and tests.
- The accepted target is stronger: open-ended household task execution is the
  base contract. Cleanup and map-build are typed configurations on that base,
  not public peers beside it.

## Zoom-Out Map

```text
natural-language operator goal
  -> just run::surface / operator console selection
  -> roboclaws.launch.catalog.resolve_surface_launch
  -> TaskSurfaceSpec + DomainOpenTaskContract + optional PresetSpec + GoalContract
  -> agent runner lowering through just agent::run
  -> live runtime (Codex, Claude Code, OpenAI Agents SDK, or direct smoke)
  -> kickoff prompt and mounted skill context
  -> household MCP server public tools
  -> done(reason) writes run_result/report/trace/goal_contract
  -> base completion or preset-owned evaluation and operator-console proof status
  -> validation matrix chooses regression/product gates
```

Current invariant to preserve:

- Public/private evaluator boundaries stay intact.
- Base Navigation Map remains start-of-run context.
- Runtime Metric Map owns semantic enrichment.
- The base household task terminal outcome is authoritative; cleanup score is
  authoritative only when `preset=cleanup` selects the cleanup evaluation
  policy and advisory otherwise.
- Physical backends may return structured `blocked_capability` responses until
  manipulation is proven.

## Engineering Review Recommendation

Do not rewrite the whole household stack. The current surface/intent/profile
architecture is close enough. The high-value refactor is to move the default
product center of gravity:

```text
before:
  cleanup implementation with open-ended exceptions

after:
  open household task runtime with cleanup as one optional preset
```

Use migration slices that keep current supported behavior verifiable while
making new entrypoints, prompts, routes, and validation gates
open-task-first. Do not keep compatibility shims for obsolete cleanup-shaped
public commands, route ids, skill names, intent ids, or artifact schemas unless
a selected slice explicitly parks them as archived evidence.

Rejected alternatives:

- Keep adding more "do not cleanup" clauses to the cleanup prompt. This makes
  every future task rediscover cleanup-specific negatives.
- Add a new opaque MCP tool such as `do_open_task`. This would hide robot work
  behind one tool and conflict with the skill-first MCP contract.
- Split simulator and real robot into separate task taxonomies. Backend
  variants, provenance, safety gates, and blocked capabilities should vary
  under the same public surface/preset/profile shape.

## Discovery Rounds

### Round 1: Orientation And Existing Contract

Evidence:

- `README.md`, `ARCHITECTURE.md`, and
  `docs/human/mcp-skills-and-semantic-profiles.md` already describe
  open-ended goals as the top of the abstraction ladder.
- `roboclaws/launch/intents.py` defines `intent=open-ended` with
  `default_goal_scope=agent-declared` and required capabilities limited to
  `household_world` plus `household_episode`.
- `roboclaws/household/realworld_mcp_server.py` already writes
  `intent_status`, `goal_status`, and `cleanup_status_role=advisory` for
  open-ended artifacts.

Candidate-level finding: the current public model is a useful migration source,
but the peer `intent=` axis should not be the target architecture. Runtime
lowering and validation still make cleanup the default implementation frame.

### Round 2: Launch, Console, Runner, And Prompt Probes

Targeted probes:

- `default_intent`
- `prompt=`
- `household-world.open-ended`
- `implementation_task_name`
- `molmo-realworld-cleanup`
- `task_intent_mode`
- `openai-agents-sdk`

Evidence:

- `surface=household-world` still has `default_intent="cleanup"`.
- Prompt inference maps supplied prompts to `open-ended`, but omitted prompts
  fall back to the surface default.
- `just agent::run household-world.open-ended` lowers to
  `implementation_task_name="household-cleanup"`.
- The live prompt file is `roboclaws/agents/prompts/household_cleanup.py`.
- Open-ended prompt text correctly says the operator task is authoritative,
  but it still exists as a cleanup-prompt branch.
- Operator console enables open-ended Codex/Claude routes, but disables
  `open-ended::openai-agents-sdk` as not proven.

Candidate-level finding: the entrypoint is partially open-ended, while the
public axis, implementation names, and SDK route support still teach agents and
maintainers to think in cleanup terms.

### Round 3: Skills, SDK Runtime, And Validation Matrix

Targeted probes:

- mounted skills
- Agent SDK skill context
- incomplete-turn continuation prompt
- validation gates
- open-ended checker exceptions

Evidence:

- `skills/molmo-realworld-cleanup/skill.json` requires world, manipulation, and
  episode profiles even though map-build/open-ended can be lighter.
- OpenAI Agents SDK runner loads `skills/molmo-realworld-cleanup/SKILL.md` as
  `skill_name="molmo-realworld-cleanup"`.
- SDK continuation prompt says "same live household cleanup run" and asks the
  model to continue missing cleanup steps.
- Agent Validation Matrix maps Agent SDK file changes to
  `openai-agents-sdk-cleanup`, not an open-ended SDK gate.
- Checker has scan-only exceptions for open-ended, but they remain inside
  cleanup trace/worklist/report vocabulary.

Candidate-level finding: validation can pass cleanup gates while missing a
base-household-task failure mode. SDK support needs its own open-task proof
path before it can be considered part of the default architecture.

### Round 4: Saturation Sweep

Additional checked surfaces:

- `docs/human/**` profile docs
- `just/README.md`
- `tests/unit/operator_console/**`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `tests/unit/agents/test_live_runtime.py`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`

No additional P1 candidate was found beyond the groups below. Parked items are
listed near the end.

### Materiality Gate

The reduce-entropy materiality gate was run against the candidate set after
Round 4. Result:

```text
eligible_count=7
rejected_count=0
stop_recommended=false
```

The five P1 candidates passed directly. Candidate 6 passed after being bundled
with the Agent SDK open-task proof. Candidate 7 passed as a material P2, but
remains intentionally later in the review order unless another non-cleanup
preset makes the artifact-schema risk immediate.

## Recommended Packet

Plan entropy conclusion:

- The single target pattern is `surface + prompt + optional preset`.
- Candidates 1-4 should be implemented as one coherent public-contract slice
  if selected: add the surface-owned open-task contract, add a small preset
  registry for `cleanup` and `map-build`, move skill/capability/evaluation/gate
  defaults into registry rows, and prove Codex plus Agent SDK on the default
  no-preset path.
- Do not implement Candidates 1-4 as four independent abstractions. That would
  recreate the entropy this plan is trying to remove.

### Candidate 1: Collapse Household Entry To One Open Task Contract

Severity: P1

Entropy source: public contract drift / real workflow friction

Materiality: future users and agents can launch a household agent without
realizing omitted `intent=` still means cleanup, while the product goal is one
open-ended household task contract.

Why now: public docs already say supplied prompts infer `intent=open-ended`, but
`TaskSurfaceSpec.default_intent` is still cleanup and several examples still
lead with cleanup. The target should remove the peer intent default instead of
choosing a different peer intent as the new default.

Impact radius: repo-wide public launch and operator workflow

Maintainer test: A maintainer should be able to explain the default household
agent route without saying "it is cleanup unless a prompt flips it" or
"open-ended is one of three equal household intents."

Affected paths:

- `roboclaws/household/tasks.py`
- `roboclaws/launch/catalog.py`
- `just/README.md`
- `README.md`
- `ARCHITECTURE.md`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `tests/unit/operator_console/test_routes.py`

Owner skill: `$grill-with-docs-batch`, then `$intuitive-preflight`

Zen hint: one base contract beats a default plus an implicit prompt exception.

Pattern hint: public contract simplification; do not add a generic policy
engine before the first cleanup/map-build presets exist.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/unit/operator_console/test_routes.py
```

Execution risk: needs approval because changing default public behavior can
affect docs, console defaults, and rerun commands. Because no backward
compatibility is required, migrate or remove active peer-intent command shapes
instead of preserving them as shims.

### Candidate 2: Split Household Open Task Prompt/Skill From Cleanup Prompt

Severity: P1

Entropy source: recurring rediscovery / stale surface

Materiality: open-ended prompt logic currently works by negating cleanup
behavior from a cleanup prompt module and cleanup skill context.

Why now: future tasks will keep adding "do not cleanup" clauses unless
task-neutral household goal guidance exists.

Impact radius: live-agent prompt and skill layer

Maintainer test: A maintainer adding "take useful photos" should not edit a
cleanup skill or prove that cleanup instructions were successfully suppressed.

Affected paths:

- `roboclaws/agents/prompts/household_cleanup.py`
- `skills/molmo-realworld-cleanup/SKILL.md`
- `skills/molmo-realworld-cleanup/skill.json`
- `skills/README.md`
- `just/molmo.just`
- `scripts/molmo_cleanup/run_live_codex_cleanup.py`
- `scripts/molmo_cleanup/run_live_claude_cleanup.py`
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `tests/unit/agents/test_live_runtime.py`

Owner skill: `$intuitive-refactor` after grill-batch accepts the skill split

Zen hint: prefer an affirmative open-task skill over cleanup instructions plus
negative exceptions.

Pattern hint: split by surface open-task contract plus optional preset; shared
world evidence rules can become a small common prompt helper.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py \
  tests/unit/agents/test_live_runtime.py
```

Execution risk: mounted skill names are part of Docker agent workspaces and
OpenClaw examples. Because backward compatibility is not required, migrate
known in-repo callers to the new skill name and remove stale aliases in the
same slice.

### Candidate 3: Move Required Capabilities To Preset/Skill Requirements

Severity: P1

Entropy source: false capability signal

Materiality: current `intent=open-ended` declares only world+episode
requirements, but the launch plan merges in surface-level manipulation
requirements, making open household search/inspection look manipulation-heavy.
In the target model, required capabilities should belong to presets and
selected skills, not the household surface.

Why now: real robot parity depends on distinguishing "can inspect/search" from
"can pick/place"; otherwise routes imply physical capabilities that may still
be blocked.

Impact radius: launch metadata, console route gates, skill manifests

Maintainer test: A real-robot open-ended route that only searches for a drink
should not advertise full manipulation as required before the task asks for it.

Affected paths:

- `roboclaws/household/tasks.py`
- `roboclaws/launch/catalog.py`
- `roboclaws/launch/intents.py`
- `roboclaws/launch/plans.py`
- `roboclaws/operator_console/routes.py`
- `skills/molmo-realworld-cleanup/skill.json`
- `docs/human/mcp-skills-and-semantic-profiles.md`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `tests/contract/mcp/test_semantic_profiles.py`

Owner skill: `$intuitive-refactor`

Zen hint: capability requirements should describe the selected task, not the
largest task on the surface.

Pattern hint: small preset registry row; avoid a generic policy engine until
more presets exist.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/unit/operator_console/test_routes.py
```

Execution risk: safe if launch-plan assertions are updated intentionally; risky
if downstream route gating silently assumes manipulation is always present.

### Candidate 4: Promote Agent SDK Open Task To A Proven Experimental Route

Severity: P1

Entropy source: false confidence / workflow friction

Materiality: the desired product path includes Agent SDK, but the operator
console explicitly disables the current `open-ended::openai-agents-sdk` route
while validation only selects cleanup SDK gates.

Why now: SDK cleanup success does not prove open-ended prompt scoping,
continuation recovery, or checker semantics.

Impact radius: operator console, live SDK runner, validation matrix

Maintainer test: An SDK runner change should fail a focused validation matrix
when it breaks "find something useful to drink", not only when it breaks
cleanup.

Affected paths:

- `roboclaws/operator_console/routes.py`
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `skills/agent-validation-matrix/scripts/select_validation_matrix.py`
- `skills/agent-validation-matrix/SKILL.md`
- `tests/unit/operator_console/test_routes.py`
- `tests/unit/molmo_cleanup/test_agent_validation_matrix.py`
- `tests/unit/agents/test_live_runtime.py`

Owner skill: `$intuitive-preflight` for proof contract, then
`$intuitive-refactor`

Zen hint: do not call an engine supported for the base path until a matching
base-path gate exists.

Pattern hint: validation selection from surface contract plus optional preset
and engine; extend the existing matrix rather than adding ad hoc checks.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/operator_console/test_routes.py \
  tests/unit/molmo_cleanup/test_agent_validation_matrix.py \
  tests/unit/agents/test_live_runtime.py

just agent::harness agent-validation recommend \
  agent_engine=openai-agents-sdk budget=focused
```

Local/live proof after preflight:

```bash
just run::surface surface=household-world world=molmospaces/val_0 \
  backend=mujoco agent_engine=openai-agents-sdk provider_profile=codex-env \
  evidence_lane=world-oracle-labels prompt="我渴了，帮我找些解渴的东西"
```

Execution risk: needs local/provider approval because live SDK runs may cost
tokens and depend on keys/network.

### Candidate 5: Replace Cleanup-Shaped Runtime Names With Task-Neutral Household Names

Severity: P1

Entropy source: live source drift / recurring rediscovery

Materiality: `household-world.open-ended` currently lowers to
`implementation_task_name="household-cleanup"`, outputs under cleanup-shaped
paths, and connects to a cleanup-named MCP server. With no backward
compatibility requirement, these should become migration targets rather than
public or semi-public compatibility surfaces.

Why now: once the base open task path is the default, cleanup-lowered task
names will make logs, timing, rerun commands, and tests look like the wrong
task.

Impact radius: runner scripts, logs, reports, tests

Maintainer test: A report or timing timeline for "find water" should not require
the reader to know that `task_name=household-cleanup` really means
an ad-hoc open household goal.

Affected paths:

- `just/agent.just`
- `just/molmo.just`
- `roboclaws/cli/household_agent_server.py`
- `roboclaws/household/realworld_mcp_server.py`
- `scripts/molmo_cleanup/run_live_codex_cleanup.py`
- `scripts/molmo_cleanup/run_live_claude_cleanup.py`
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/household_live.py`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `tests/unit/agents/test_live_runtime.py`

Owner skill: `$intuitive-refactor`

Zen hint: implementation reuse can stay private during the edit, but active
logs, routes, and artifacts should name the selected task honestly.

Pattern hint: Adapter/facade only as a short implementation tactic inside the
slice; delete obsolete cleanup-shaped public wrappers after known in-repo
callers migrate.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/unit/agents/test_live_runtime.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
```

Execution risk: path names and report rerun commands can be user-facing, but
no backward compatibility is required. Update active docs/tests/recipes and
remove obsolete cleanup-shaped public paths in the same slice.

### Candidate 6: Add Task-Aware Continuation And Done-Recovery Text

Severity: P2

Entropy source: false confidence

Materiality: SDK continuation recovery currently says "cleanup run" and asks
the model to continue missing cleanup steps even when the selected task is an
ad-hoc open household goal.

Why now: open-ended Agent SDK support cannot be trusted if retries can steer
the model back into cleanup after an incomplete turn.

Impact radius: OpenAI Agents SDK live runner

Maintainer test: A continuation after "find something to drink" should preserve
the operator goal rather than resume a cleanup routine.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `tests/unit/agents/test_live_runtime.py`

Owner skill: `$intuitive-refactor`, bundled with Candidate 4 when implemented

Zen hint: recovery text must restate the selected surface contract, goal, and
optional preset, not the historical runner name.

Pattern hint: no pattern; direct task-aware prompt rendering is clearer.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py
```

Execution risk: safe if bundled with SDK open-ended route proof; too small as a
standalone slice unless it blocks Candidate 4.

### Candidate 7: Separate Base Task Validation From Cleanup Checker/Report Vocabulary

Severity: P2

Entropy source: false confidence / recurring rediscovery

Materiality: checker logic already has open-ended exceptions, but the artifact
contract still uses `cleanup_policy_trace`, `cleanup_worklist`, and cleanup
report sections for scan-only or information-gathering tasks.

Why now: this is not required for the first default-entry refactor, but future
tasks beyond cleanup will keep adding exceptions unless the task-neutral
episode/result contract is named.

Impact radius: artifacts, reports, checker, operator console

Maintainer test: A future information-gathering or search task should not pass
or fail only because it happens to satisfy legacy trace/worklist exceptions
instead of its selected surface contract or preset-owned evaluation policy.

Affected paths:

- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/household/report.py`
- `roboclaws/household/artifact_report.py`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- `tests/unit/operator_console/test_state.py`

Owner skill: `$grill-with-docs-batch` before implementation

Zen hint: terminal outcome already has one authority; artifact names should
eventually follow it.

Pattern hint: small state/result schema split; do not introduce a large event
framework unless multiple non-cleanup presets demand it.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/unit/operator_console/test_state.py \
  tests/contract/reports/test_molmo_cleanup_report.py
```

Execution risk: defer until the public entry and skill split are accepted.
No backward compatibility is required, so old cleanup-shaped schemas can be
retired from active writers/checkers once known in-repo consumers migrate.

## Suggested Review Order

1. Candidates 1-3: product contract and capability boundary. These decide what
   "default open household task" means.
2. Candidates 4 and 6: Agent SDK proof and continuation semantics. These make
   SDK part of the default story without false confidence.
3. Candidate 5: neutral runtime names. This is most valuable after the default
   and skill/capability decisions are accepted.
4. Candidate 7: task-neutral artifacts. This should wait until at least two
   non-cleanup presets need stronger report/checker semantics.

## Verification Ladder For An Accepted Implementation Slice

Cheap contract tests:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/unit/operator_console/test_routes.py \
  tests/unit/molmo_cleanup/test_agent_validation_matrix.py
```

Prompt/runner tests:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/agents/test_live_runtime.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
```

Checker/report tests:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/unit/operator_console/test_state.py
```

Adaptive matrix:

```bash
just agent::harness agent-validation recommend \
  plan=docs/plans/2026-06-12-open-ended-household-default-architecture.md \
  budget=focused
```

Optional local live proof after preflight:

```bash
just run::surface surface=household-world world=molmospaces/val_0 \
  backend=mujoco agent_engine=codex-cli provider_profile=codex-env \
  evidence_lane=world-oracle-labels prompt="我渴了，帮我找些解渴的东西"

just run::surface surface=household-world world=molmospaces/val_0 \
  backend=mujoco agent_engine=openai-agents-sdk provider_profile=codex-env \
  evidence_lane=world-oracle-labels prompt="我渴了，帮我找些解渴的东西"
```

## Stop Conditions

Discovery stop condition:

- No new P0/P1 candidate appears after launch, runner, console, skill, SDK,
  checker/report, and validation-matrix probes.
- Remaining observations are either historical compatibility names or parked
  artifact-schema cleanup.

Implementation stop condition for the first accepted slice:

- New natural-language household agent route is visibly the base household task
  contract.
- Cleanup is selected as `preset=cleanup`, and still requires cleanup gates and
  relocation setup when that preset is selected.
- Base household prompts/skills do not import cleanup strategy as their default
  instruction surface.
- Required capability metadata distinguishes world/episode-only tasks from
  manipulation tasks.
- Validation matrix can select base-household Codex/Agent SDK proof rows and
  cleanup/map-build preset proof rows when relevant.
- Obsolete cleanup-shaped open-ended command, route, skill, and artifact
  surfaces are removed from active code/docs/tests after known in-repo
  consumers migrate.

## Parked Items

- Full rename of `molmo_cleanup_realworld` MCP server id. This is allowed under
  the forward-only policy, but it may still be a later slice if doing it in the
  first pass makes the diff too broad.
- Full replacement of `cleanup_policy_trace` and `cleanup_worklist` schemas.
  Candidate 7 records the direction, but this should wait until the base
  household contract and skill split are accepted unless the selected first
  slice deliberately includes artifact-schema migration.
- OpenClaw base household default. OpenClaw remains validation-required on this
  host/work network, so do not include it in the first local proof path.
- Direct-runner base household task as a product route. Current value is in
  coding-agent / SDK behavior; direct smoke remains useful as a cheap gate.

## Next Options

- Run `$intuitive-preflight` for Candidates 1-4 if the desired first
  implementation is "base household task contract plus Agent SDK proof".
- Create a short ADR only if implementation will change the durable public
  command contract from `intent=` to `surface + prompt + optional preset` in
  one slice.
- Park Candidate 7 until after at least one more non-cleanup preset is proven,
  unless the first slice deliberately includes artifact-schema migration.

## Preflight Contract: First Public-Contract Slice

Preflight status: DRAFT

Task source: user request plus this plan.

Canonical source:
`docs/plans/2026-06-12-open-ended-household-default-architecture.md`

Route: durable `$intuitive-flow`

Goal: implement the first public-contract slice so `surface=household-world`
selects the household open-task contract by default, with `preset=cleanup` and
`preset=map-build` as optional compressed standard tasks.

Scope:

- Replace active peer household intents with the target public shape:
  `surface=household-world prompt=...` for default open tasks and
  `surface=household-world preset=cleanup|map-build` for standard tasks.
- Add a small household preset registry for `cleanup` and `map-build`; move
  skill, required capability, completion/evaluation, report-profile, scenario,
  and validation defaults into registry rows.
- Split task-neutral household open-task prompt/skill scaffolding from the
  cleanup prompt/skill; open-task routes must not rely on cleanup-negation
  instructions.
- Make required capabilities preset/skill-scoped so search/inspection/open
  tasks do not inherit cleanup-level manipulation requirements.
- Promote deterministic OpenAI Agents SDK support for the no-preset household
  open-task route, including route metadata, continuation/recovery text, and
  validation-matrix selection.
- Migrate active docs, tests, routes, and in-repo callers forward. Because
  backward compatibility is not required, remove active obsolete peer-intent or
  cleanup-shaped public wrappers instead of preserving shims.
- Create or update a short ADR in the same slice if implementation changes the
  durable public command contract from `intent=` to `surface + prompt +
  optional preset`.

Non-goals:

- Do not implement `retail-store`, warehouse, or any new non-household surface.
- Do not complete Candidate 5 full runtime/server/path renaming unless it is
  required to remove an active public wrapper touched by this slice.
- Do not complete Candidate 7 artifact-schema replacement for
  `cleanup_policy_trace` / `cleanup_worklist`.
- Do not add MCP mega-tools such as `do_open_task` or `do_cleanup`.
- Do not validate OpenClaw; it remains work-network/provider gated.
- Do not keep backward-compatible public aliases unless a currently working
  in-repo route has no migrated replacement inside the slice.

Context:

- must-read: `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`,
  `CLAUDE.md`, this plan, `docs/human/mcp-skills-and-semantic-profiles.md`,
  `docs/human/domain.md`, `docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md`
- must-inspect code: `roboclaws/household/tasks.py`,
  `roboclaws/launch/catalog.py`, `roboclaws/launch/intents.py`,
  `roboclaws/launch/plans.py`, `roboclaws/launch/evaluation.py`,
  `roboclaws/launch/goals.py`, `roboclaws/operator_console/routes.py`,
  `roboclaws/agents/prompts/household_cleanup.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `skills/molmo-realworld-cleanup/`, `just/agent.just`, `just/README.md`,
  `skills/agent-validation-matrix/scripts/select_validation_matrix.py`
- useful: tests named in the Verification section, active examples in
  `README.md` and `ARCHITECTURE.md`, `docs/plans/2026-06-11-open-ended-proof-status.md`
- avoid-unless-needed: historical `.planning/`, shipped retrospectives,
  generated `output/`, old AI2-THOR/direct-VLM docs, OpenClaw local proof docs

Acceptance:

- SUCCESS: `surface=household-world prompt="我渴了，帮我找些解渴的东西"`
  resolves through the household open-task contract without selecting cleanup;
  `preset=cleanup` selects cleanup-specific skill, manipulation requirements,
  relocation setup, cleanup gate/report behavior, and private scorer boundary;
  `preset=map-build` selects map evidence behavior without cleanup/manipulation
  requirements; Codex and OpenAI Agents SDK route metadata and validation
  matrix can target the no-preset open-task path.
- BLOCKED_NEEDS_DECISION: none expected; if implementation discovers a public
  grammar conflict between `preset=` and existing `intent=`, stop and bring
  back one concrete recommendation.
- BLOCKED_NEEDS_LOCAL_VALIDATION: provider-backed Codex/Agent SDK product runs
  require local keys, Docker/runtime availability, and allowed network. If those
  cannot run, the branch can be an intermediate checkpoint but is not complete.
- INTERMEDIATE_ONLY: acceptable only if explicitly approved after deterministic
  tests pass and required local/live commands are documented as pending.
- No regressions: Base Navigation Map remains start-of-run context; Runtime
  Metric Map remains semantic enrichment; private relocation/scoring truth
  remains hidden from agent inputs; cleanup scoring is authoritative only for
  `preset=cleanup`; open tasks use agent-declared completion with public
  evidence unless a preset selects another policy.

Verification:

- deterministic:
  `ruff check .`
  `ruff format --check .`
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/operator_console/test_routes.py tests/unit/molmo_cleanup/test_agent_validation_matrix.py tests/unit/agents/test_live_runtime.py tests/contract/mcp/test_semantic_profiles.py tests/contract/skills/test_molmo_realworld_cleanup_skill.py`
- integration:
  `just agent::harness agent-validation recommend plan=docs/plans/2026-06-12-open-ended-household-default-architecture.md budget=focused`
  plus any focused checker/report tests touched by the implementation.
- product-run:
  `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels prompt="我渴了，帮我找些解渴的东西"`
  `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=direct-runner evidence_lane=world-oracle-labels preset=cleanup seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5`
  `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=direct-runner evidence_lane=world-oracle-labels preset=map-build seed=7 scenario_setup=baseline`
- local-live-manual:
  `just dev::network-status` before guarded/provider-backed workflows;
  run the Codex product command above with repo-local `.env` provider keys; run
  the matching OpenAI Agents SDK no-preset open-task command when keys/network
  allow:
  `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=openai-agents-sdk provider_profile=codex-env evidence_lane=world-oracle-labels prompt="我渴了，帮我找些解渴的东西"`.
- optional: full `./scripts/dev/run_pytest_standalone.sh -q` after focused
  gates are green.

Harness Matrix baseline:

- Command run on 2026-06-12:
  `just agent::harness agent-validation recommend plan=docs/plans/2026-06-12-open-ended-household-default-architecture.md budget=focused`
- Report:
  `output/agent-validation-matrix/20260612T142121Z/validation_matrix.md`
- Selected pre-migration gates: route trace contract tests, cleanup contract
  tests, one direct cleanup world-oracle product route, open-ended contract
  tests, live Codex cleanup, live OpenAI Agents SDK cleanup, camera-grounded
  direct gates, direct map-build, and direct cleanup runtime-prior consumer.
- Important interpretation: this is a pre-migration baseline. The matrix still
  selects legacy `intent=cleanup` and `intent=map-build` product gates because
  current code has not migrated to `surface + prompt + optional preset`.
- Post-implementation result: rerunning the matrix selected no-preset
  household open-task gates for Coding Agent and Agent SDK, plus
  `preset=cleanup` and `preset=map-build` product gates, instead of legacy
  peer-intent gates.
- Product proof priority: the highest-signal gates are the real no-preset
  Coding Agent run and the real no-preset OpenAI Agents SDK run:
  `surface=household-world prompt="我渴了，帮我找些解渴的东西"`.
  The Codex run passed on 2026-06-13 CST. The OpenAI Agents SDK run is
  `BLOCKED_NEEDS_LOCAL_VALIDATION` because the configured provider route
  returned upstream 502 before robot action.

Execution:

- main: supervise with this plan as source of truth; keep the slice coherent
  rather than splitting Candidates 1-4 into independent abstractions.
- worker: none by default; use an isolated worker only for bounded code-search
  or verification-log probes if implementation context gets noisy.
- worker-goal: none.

To execute:

```text
/goal execute docs/plans/2026-06-12-open-ended-household-default-architecture.md with intuitive-flow
```

Approval: `LGTM`, `approve`, `go ahead`, or `do this` approves this preflight;
edits request a revised contract before execution.
