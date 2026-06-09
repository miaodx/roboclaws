---
plan_scope: task-surface-intent-goal-contract-refactor
status: DONE
source:
  - 2026-06-09 custom prompt / cleanup prompt abstraction discussion
  - intuitive-reduce-entropy
  - grill-with-docs-batch
last_reviewed: 2026-06-09
completed: 2026-06-09
---

# Task Surface, Intent, And Goal Contract Refactor

## Goal

Replace the current cleanup/custom-prompt split with a repo-wide launch and
prompt model where execution surfaces, task intents, normalized goals, and
evaluation policies are separate concepts.

The target model is:

```text
TaskSurfaceSpec
  -> TaskIntentSpec
  -> GoalContract
  -> Execution prompt
  -> AgentCompletionClaim
  -> EvaluationSpec
```

This makes open-ended user goals first-class instead of routing them through a
cleanup-specific `custom` branch.

## Problem

The current household live-agent path treats default cleanup and custom prompts
as two paths inside the `household-cleanup` route. That creates several sources
of drift:

- `household-cleanup` acts both as the runnable environment and as the cleanup
  intent.
- `semantic-map-build` is a separate public task even though it uses the same
  household world and MCP capability surface.
- `task_intent_mode=custom` is a cleanup-specific boolean-like mode instead of
  a general goal contract.
- Prompt logic, done readiness, checker gates, and operator-console launch
  behavior all special-case custom prompts independently.
- Some routes can receive a prompt but do not treat it the same way, which
  makes user-facing behavior depend on driver internals.

## Decisions

1. Use **TaskSurfaceSpec** for execution surfaces.
   A surface names the runnable environment and capability surface. It owns
   supported drivers, MCP server choice, backend defaults, evidence lanes or
   report variants, and capability profiles.

2. Use **TaskIntentSpec** for goal types.
   An intent names what the agent is trying to accomplish inside a surface. It
   owns prompt layers, done-readiness policy, checker policy, required
   artifacts, and evaluator expectations.

3. Use **GoalContract** for the normalized goal instance.
   Raw `prompt=` text is source material. It must be normalized into a concrete
   goal contract before execution begins.

4. Use **EvaluationSpec** for verification semantics.
   Evaluation is always present and is composed from hard gates, intent-specific
   gates, agent completion claims, and optional advisory evaluators.

5. Use named parameters only for the new canonical command surface.
   Do not add new positional shorthand.

6. Replace the canonical `task::run` grammar with `run::surface`.
   `task::run` and cleanup-specific public task names are not canonical after
   this refactor.

7. Treat `prompt=` as raw user goal text.
   If a prompt is supplied and `intent=` is omitted, infer `intent=open-ended`.

8. Keep cleanup prompt text scoped to cleanup intent.
   Common MCP/tool guidance should be shared. Cleanup-specific sweep, visual
   scan, pick/place, and count instructions should not leak into open-ended
   intents.

9. Make goal normalization mandatory for every run.
   Even a default run gets a short normalized goal contract.

10. Allow clarification before execution.
    If the raw prompt is ambiguous, conflicts with the selected intent, or has
    unclear scope, normalization can produce a clarification question. A
    non-interactive CLI should fail before robot execution and print that
    question; an operator UI can let the user answer and relaunch.

11. Require an agent completion claim for every run.
    The run is not complete just because the agent calls `done`; the report must
    include why the agent believes the normalized goal is complete.

12. Do not preserve obsolete compatibility paths.
    The refactor should migrate in-repo callers, docs, and tests to the new
    canonical model instead of keeping cleanup/custom wrapper aliases alive.

## Canonical Command Shape

Cleanup:

```bash
just run::surface \
  surface=household-world \
  driver=codex \
  evidence_lane=world-oracle-labels \
  intent=cleanup
```

Prompt-scoped cleanup:

```bash
just run::surface \
  surface=household-world \
  driver=codex \
  evidence_lane=world-oracle-labels \
  intent=cleanup \
  prompt="收拾桌面和地上的杂物"
```

Open-ended household goal:

```bash
just run::surface \
  surface=household-world \
  driver=codex \
  evidence_lane=world-oracle-labels \
  intent=open-ended \
  prompt="我渴了，帮我找些解渴的东西"
```

Map build:

```bash
just run::surface \
  surface=household-world \
  driver=codex \
  evidence_lane=world-oracle-labels \
  intent=map-build
```

AI2-THOR navigation:

```bash
just run::surface \
  surface=ai2thor-world \
  driver=codex \
  report=visual \
  intent=navigate
```

## Concept Definitions

### TaskSurfaceSpec

Execution surface metadata.

Initial examples:

- `household-world`
- `ai2thor-world`

Likely fields:

```text
surface_id
domain
supported_drivers
default_driver
supported_intents
default_intent
supported_evidence_lanes
supported_reports
default_evidence_lane
default_report
default_backend
mcp_server_id
required_capability_profiles
checker_base
```

### TaskIntentSpec

Goal type metadata for a surface.

Initial household intents:

- `cleanup`
- `map-build`
- `open-ended`

Initial AI2-THOR intents:

- `navigate`
- `photo-capture`

Likely fields:

```text
intent_id
surface_ids
supported_drivers
default_goal_scope
prompt_layers
done_readiness_policy
checker_policy
required_artifacts
completion_claim_schema
evaluation_policy
```

### GoalContract

Normalized, run-specific goal.

Likely artifact: `goal_contract.json`.

Minimum fields:

```json
{
  "schema": "roboclaws_goal_contract_v1",
  "raw_prompt": "",
  "normalized_goal": "",
  "surface": "household-world",
  "intent": "cleanup",
  "goal_scope": "whole-room",
  "assumptions": [],
  "tool_plan": [],
  "success_criteria": [],
  "clarification_needed": false,
  "clarification_question": "",
  "safety_notes": []
}
```

Goal scope values:

- `whole-room`
- `prompt-scoped`
- `agent-declared`

Default rules:

- `intent=cleanup` without `prompt=` defaults to `goal_scope=whole-room`.
- `intent=cleanup` with `prompt=` defaults to `goal_scope=prompt-scoped`.
- If deterministic normalization cannot identify the scope, use
  `goal_scope=agent-declared` or ask a clarification question when the mismatch
  would change the route or safety boundary.
- `intent=open-ended` defaults to `goal_scope=agent-declared`.

### AgentCompletionClaim

The agent-facing `done` contract should require a structured completion claim
for every intent.

Minimum fields:

```text
completion_summary
why_done
evidence_used
remaining_risks
```

The checker should verify presence and shape. Intent-specific evaluators may
also use this claim.

### EvaluationSpec

Evaluation is layered:

1. Hard gates: machine-verifiable run integrity such as MCP `done`,
   `run_result.json`, `report.html`, trace artifacts, no private truth leakage,
   and required artifact presence.
2. Intent gates: deterministic requirements for known intents such as cleanup
   success counts or runtime map artifacts.
3. Agent completion claim: required for all intents.
4. Advisory evaluator: quality assessment for open-ended and prompt-scoped
   goals. Advisory evaluation should not initially become a hard failure unless
   the intent spec explicitly promotes it.

## Initial Mapping

| Old canonical route | New canonical route |
| --- | --- |
| `household-cleanup` | `surface=household-world intent=cleanup` |
| `semantic-map-build` | `surface=household-world intent=map-build` |
| `household-cleanup task_intent_mode=custom prompt=...` | `surface=household-world intent=open-ended prompt=...` |
| `ai2thor-nav` | `surface=ai2thor-world intent=navigate` |
| `photo-chairs` | `surface=ai2thor-world intent=photo-capture` |

## Scope

Included:

- Add generic surface and intent specs.
- Add goal-contract normalization and artifact writing.
- Add `just run::surface` with named parameters only.
- Migrate launch resolution from task names to surface plus intent.
- Migrate household kickoff prompt rendering to compose from common tool
  guidance, surface context, intent rules, and `GoalContract`.
- Migrate done readiness to intent-owned policy.
- Migrate checker flag generation out of shell/live-runner custom branches and
  into evaluation policy helpers.
- Migrate operator-console route metadata to surface/intent/prompt support.
- Update human docs and tests to stop treating `household-cleanup`,
  `semantic-map-build`, or `task_intent_mode=custom` as canonical.

## Non-Goals

- Do not redesign the household MCP tool catalog.
- Do not change private evaluation truth boundaries.
- Do not require an LLM-powered normalizer in the first implementation.
  Deterministic normalization plus execution-agent restatement is sufficient for
  the first slice.
- Do not run real OpenClaw Gateway, provider, GPU, or simulator validation as
  part of the deterministic refactor proof unless separately authorized.
- Do not keep obsolete route aliases solely for compatibility.

## Implementation Notes

Suggested first slice:

1. Rename launch metadata from `TaskSpec` to `TaskSurfaceSpec`.
2. Add `TaskIntentSpec`, `GoalContract`, and `EvaluationSpec` modules under
   `roboclaws/launch/` or a similarly generic package.
3. Add a `run::surface` just module and CLI parser for named parameters.
4. Keep implementation initially pointed at existing lower runners while
   changing the resolved canonical model.
5. Move household prompt rendering from `task_intent_mode` branches to
   intent-specific prompt layers.
6. Move live-runner checker policy into a shared evaluation helper.
7. Delete stale task-intent-mode branches after known in-repo callers are
   migrated.

## Acceptance Criteria

Success requires:

- The canonical command docs and tests use `run::surface` named parameters.
- Launch resolution can run at least:
  - `surface=household-world intent=cleanup`
  - `surface=household-world intent=open-ended prompt=...`
  - `surface=household-world intent=map-build`
  - `surface=ai2thor-world intent=navigate`
- Every resolved run has a `GoalContract`.
- Prompt rendering uses shared tool guidance plus surface/intent/goal layers.
- `open-ended` prompts do not inherit cleanup sweep/count/pick-place mandates.
- `cleanup` prompts may narrow the cleanup scope without switching to
  open-ended.
- `done` requires a structured completion claim for every intent.
- Checker policies are generated from evaluation specs instead of shell or
  runner custom-branch filters.
- In-repo references to canonical `household-cleanup`, `semantic-map-build`,
  and `task_intent_mode=custom` are either migrated or deliberately marked as
  historical/non-canonical.
- A Codex live-agent cleanup run works through the new canonical surface/intent
  pipeline and passes the cleanup checker without relying on obsolete
  task-name or custom-mode branches.
- A Codex live-agent open-ended/custom user task works through the same
  canonical surface/intent pipeline, writes a normalized `goal_contract.json`,
  produces a structured completion claim, generates the report artifacts, and
  passes the open-ended evaluation gates without inheriting cleanup-only
  success requirements.
- The two Codex live-agent runs above prove there is no regression in the full
  MCP server -> agent prompt -> tool trace -> done -> report -> checker
  pipeline for both cleanup and custom/open-ended goals.

## Verification Plan

Required deterministic gates:

```bash
.venv/bin/ruff check roboclaws/launch roboclaws/agents roboclaws/household roboclaws/operator_console scripts/molmo_cleanup tests/contract/dev_tools tests/unit/agents tests/unit/operator_console tests/unit/molmo_cleanup
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/agents/test_live_runtime.py tests/unit/operator_console tests/unit/molmo_cleanup
```

Useful focused checks:

```bash
.venv/bin/python -m roboclaws.cli.main run surface \
  surface=household-world \
  driver=codex \
  evidence_lane=world-oracle-labels \
  intent=open-ended \
  prompt="我渴了，帮我找些解渴的东西"
```

Required local/live gates for a full product claim:

- One local Codex live-agent household cleanup run for `intent=cleanup`,
  exercising the full MCP server -> Codex prompt -> tool trace -> `done` ->
  report -> checker pipeline.
- One local Codex live-agent household open-ended/custom task run for
  `intent=open-ended prompt=...`, exercising the same full pipeline and proving
  the run does not regress into cleanup-only prompt or checker behavior.
- One local mock/smoke household run for `intent=cleanup`.
- One local mock/smoke household run for `intent=open-ended`.
- One local map-build run for `intent=map-build`.
- Operator-console launch preview for a custom prompt showing the normalized
  goal contract.

## Implementation Evidence

Completed on 2026-06-09.

Implemented:

- Added the canonical `just run::surface` named-parameter grammar backed by
  surface, intent, goal-contract, and evaluation specs.
- Migrated household cleanup, map-build, and open-ended household goals onto
  `surface=household-world` with explicit intents.
- Migrated AI2-THOR navigation/photo and games routes onto surface/intent
  launch resolution.
- Wrote `goal_contract.json` for resolved runs and propagated the goal contract
  through lower household recipes and live-agent runners.
- Split common household MCP/tool guidance from cleanup-specific prompt
  instructions so `intent=open-ended` does not inherit cleanup sweep/count or
  pick/place mandates.
- Generated checker behavior from evaluation policy helpers, including
  open-ended `claim=present` handling.
- Updated operator-console route metadata, human docs, and contract/unit tests
  to treat `run::surface` as canonical and old task ids as lower-level or
  historical implementation details.

Live/local artifacts:

- Cleanup Codex live pass:
  `output/validation/task-surface-codex-cleanup/0609_1847/seed-7`
- Open-ended Codex live pass:
  `output/validation/task-surface-codex-open-ended/0609_1855/seed-7`
- Open-ended MCP smoke pass:
  `output/validation/task-surface-mcp-open-ended-fixed/0609_1931/seed-7`

Verification run:

```bash
.venv/bin/ruff check roboclaws/launch roboclaws/agents roboclaws/household roboclaws/operator_console scripts/molmo_cleanup tests/contract/dev_tools tests/unit/agents tests/unit/operator_console tests/unit/molmo_cleanup
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/agents/test_live_runtime.py tests/unit/operator_console tests/unit/molmo_cleanup
git diff --check
```

Result: all passed on 2026-06-09. Pytest emitted one existing Pillow
deprecation warning from `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`.

Integration validation requirement:

- The two Codex live-agent gates are hard completion gates for this refactor.
  They are not optional, advisory, or deferrable for merge/full-success
  acceptance.
- If the execution environment cannot run the required Codex live-agent gates,
  the implementation status is `BLOCKED_NEEDS_LOCAL_VALIDATION`, not `PARTIAL`.
- A deterministic-only implementation may be useful as an intermediate branch,
  but it must not be described as complete, merge-ready, or no-regression until
  the required Codex cleanup and open-ended/custom pipeline runs pass.
- Additional provider, Gateway, GPU, or real simulator coverage can remain
  follow-up scope unless this plan is expanded, but those optional gates do not
  replace the required Codex integration proof.

## Preflight Contract

Preflight status: `DONE`

Task source:

- 2026-06-09 task surface / intent / goal contract discussion.
- This plan file.

Canonical source:

- `docs/plans/task-surface-intent-goal-contract-refactor.md`

Route:

- `$intuitive-refactor`

Goal:

Refactor Roboclaws launch, prompt, goal, and evaluation plumbing so execution
surfaces, task intents, normalized goals, completion claims, and evaluation
policies are separate repo-wide concepts.

Scope:

- Add generic task surface, task intent, goal contract, and evaluation policy
  structures.
- Add `run::surface` as the new canonical named-parameter run surface.
- Migrate household cleanup, open-ended/custom prompt, and map-build behavior
  onto `surface=household-world` plus explicit intents.
- Migrate AI2-THOR navigation onto `surface=ai2thor-world intent=navigate`.
- Move prompt composition, done readiness, and checker policy out of
  cleanup/custom branches and into surface/intent/goal/evaluation layers.
- Update operator-console route metadata and current docs/tests to the new
  model.

Non-goals:

- Do not redesign the household MCP tool catalog.
- Do not change private evaluation truth boundaries.
- Do not require an LLM-powered goal normalizer in the first implementation.
- Do not claim completion from deterministic tests alone.
- Do not preserve obsolete route aliases solely for compatibility.

Context package:

- Must read:
  - `README.md`
  - `ARCHITECTURE.md`
  - `STATUS.md`
  - `AGENTS.md`
  - `CLAUDE.md`
  - `docs/plans/task-surface-intent-goal-contract-refactor.md`
  - `roboclaws/launch/task_specs.py`
  - `roboclaws/launch/catalog.py`
  - `roboclaws/launch/runners.py`
  - `roboclaws/agents/prompts/household_cleanup.py`
  - `roboclaws/household/task_intent.py`
  - `roboclaws/household/realworld_contract.py`
  - `roboclaws/household/realworld_mcp_server.py`
  - `just/task.just`
  - `just/molmo.just`
  - `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- Useful evidence:
  - `tests/unit/agents/test_live_runtime.py`
  - `tests/unit/operator_console/`
  - `tests/unit/molmo_cleanup/`
  - `scripts/molmo_cleanup/run_live_codex_cleanup.py`
  - `scripts/molmo_cleanup/run_live_claude_cleanup.py`
  - `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- Do not read unless needed:
  - `output/**`
  - historical retrospectives
  - Isaac/GPU-specific plans unrelated to launch/prompt/evaluation plumbing

Definition of Done / acceptance criteria:

- `SUCCESS` only if:
  - all acceptance criteria in this plan are implemented;
  - all required deterministic gates pass;
  - the required Codex cleanup live-agent integration run passes;
  - the required Codex open-ended/custom live-agent integration run passes;
  - generated artifacts show `goal_contract.json`, structured completion claim,
    report output, trace evidence, and checker success for the new model;
  - current docs/tests no longer present `household-cleanup`,
    `semantic-map-build`, or `task_intent_mode=custom` as canonical paths.
- `BLOCKED_NEEDS_DECISION` if:
  - a new public naming, compatibility, private-data, safety, or evaluation
    boundary decision is required before implementation can proceed honestly.
- `BLOCKED_NEEDS_LOCAL_VALIDATION` if:
  - the implementation is otherwise ready but the required Codex integration
    gates cannot run or cannot pass in the current environment.
- `INTERMEDIATE_ONLY` if explicitly approved:
  - deterministic contracts are migrated but required Codex integration proof is
    missing. This status is not complete, merge-ready, or no-regression.
- Must not regress:
  - private evaluation boundaries;
  - MCP `done` report generation;
  - Codex live-agent cleanup pipeline behavior;
  - operator-console custom prompt / steering launch metadata;
  - current report/checker artifact discoverability.

Verification:

- Required deterministic gates:
  - `.venv/bin/ruff check roboclaws/launch roboclaws/agents roboclaws/household roboclaws/operator_console scripts/molmo_cleanup tests/contract/dev_tools tests/unit/agents tests/unit/operator_console tests/unit/molmo_cleanup`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/agents/test_live_runtime.py tests/unit/operator_console tests/unit/molmo_cleanup`
- Required integration gates:
  - Codex live-agent household cleanup run through the new
    `run::surface surface=household-world intent=cleanup` pipeline.
  - Codex live-agent household open-ended/custom run through the same
    `run::surface surface=household-world intent=open-ended prompt=...`
    pipeline.
  - Local map-build run through `surface=household-world intent=map-build`.
- Required manual acceptance gate:
  - Operator-console launch preview shows the normalized goal contract for a
    custom prompt and routes through the new surface/intent model.

Execution surface:

- Main session: root supervisor for the refactor, route decisions, dirty
  worktree protection, verification review, and final success/block status.
- Worker: none by default. Use a worker only if implementation becomes
  long-running or needs isolated focused verification.
- Worker-local goal: none by default.

To execute:

```text
/goal execute docs/plans/task-surface-intent-goal-contract-refactor.md with intuitive-flow
```

Approval gate:

Approve this preflight before implementation. Execution must not mark the work
complete, merge-ready, or no-regression without the required Codex integration
proof.

## Parked Follow-Ups

- LLM-powered goal normalizer with interactive clarification loop.
- Advisory evaluator promotion to hard gate for selected open-ended intents.
- Richer scope vocabulary beyond `whole-room`, `prompt-scoped`, and
  `agent-declared`.
- Public UI redesign for normalized-goal review and approval.
