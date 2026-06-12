# Environment Setup Relocation Contract

**Status:** Proposed source plan
**Created:** 2026-06-10
**Source:** Operator-console discussion on replacing generic "mess up" /
`generated_mess_count` with task-neutral environment setup and relocation
policy vocabulary.
**Workflow:** Pre-GSD plan. Use this as the source for a bounded implementation
slice.

## Problem

The operator console currently exposes `Generated mess count` as a common setup
field. That makes a cleanup-shaped scenario knob look like a universal task
parameter.

The underlying product need is broader than cleanup: operators should be able
to run the same task intent against a baseline room or a pre-run environment
variation. For example, an open-ended "find the remote" task may be more useful
when loose objects have been relocated before the agent starts. That setup
should not make the task a cleanup task, and it must not leak private setup
truth into Agent View.

## Goals

- Replace generic "mess up" / `Generated mess count` with a task-neutral
  **Environment Setup** concept.
- Express setup variation as relocation, not cleanup:
  - `baseline`
  - `relocate-loose-objects`
  - `relocate-cleanup-related-objects`
- Keep task intent and evaluation separate from setup:
  - cleanup uses cleanup evaluation;
  - map-build uses runtime-map evaluation;
  - open-ended goals use agent-declared/advisory evaluation.
- Make relocation private to environment initialization. The agent faces a
  normal room and is not told whether objects were relocated.
- Keep setup provenance available in private/report artifacts after the run.
- Do not preserve the old public `generated_mess_count` name. This repo has no
  backward-compatibility burden for this cleanup.

## Non-Goals

- Do not introduce a separate public `Cleanup mess scenario` concept.
- Do not expose moved object IDs, before/after locations, target membership, or
  relocated-object counts to the agent.
- Do not make relocation a task intent or MCP capability.
- Do not require goal-target relocation in the first slice; generic target
  extraction can come later.
- Do not retain old public UI labels or command arguments solely for
  compatibility.

## Terminology

**Environment Setup**:
A private pre-run world initialization choice that prepares the room before the
agent starts. It is independent of task intent and evaluation policy.
_Avoid_: task intent, cleanup scenario, agent-facing context

**Relocation Policy**:
An Environment Setup mode that moves eligible objects before the run starts.
The agent is not told the policy or exact relocated objects.
_Avoid_: mess generator, cleanup worklist, private scoring truth

**Relocation Count**:
The operator-controlled number of objects the setup may relocate when the
selected Environment Setup is not `baseline`.
_Avoid_: generated mess count, target count

**Cleanup-Related Objects**:
Objects eligible for cleanup evaluation after relocation. This is private setup
and scorer-side truth, not Agent View.
_Avoid_: public cleanup targets, observed object handles

## Public Contract

New public setup arguments:

```text
environment_setup=baseline|relocate-loose-objects|relocate-cleanup-related-objects
relocation_count=<N>
```

`relocation_count` is only meaningful when `environment_setup` is not
`baseline`. The existing run `seed` may continue to seed deterministic
environment setup unless implementation evidence shows a separate
`relocation_seed` is needed.

The operator-console UI should show:

- `Environment setup`
  - `Baseline`
  - `Relocate loose objects`
  - `Relocate cleanup-related objects`
- `Relocation count`, visible only when the setup is not `Baseline`

Recommended route defaults:

- cleanup: `relocate-cleanup-related-objects`
- map-build: `baseline`
- open-ended: `baseline`

## Agent And Report Boundary

Agent View must not include:

- selected environment setup;
- relocation policy;
- relocation count;
- moved object IDs;
- before/after relocation positions;
- cleanup-related object membership;
- private scoring truth.

Reports and private artifacts may include setup provenance after the run:

- selected setup mode;
- seed;
- relocation count;
- moved objects;
- before/after positions;
- whether relocation fed cleanup scoring.

## Implementation Sketch

- Update the operator-console setup UI:
  - replace `Generated mess count` with `Environment setup`;
  - show `Relocation count` only for relocation modes;
  - keep seed and agent port separate from relocation-specific fields.
- Update console route metadata so setup fields are route/intent aware rather
  than part of one broad `common` group.
- Update launch request construction to send `environment_setup` and
  `relocation_count` instead of `generated_mess_count`.
- Update the household launch/catalog and lower cleanup/map-build runner
  plumbing to consume the new setup arguments.
- Remove or rename public `generated_mess_count` references in console tests,
  docs, and supported run surfaces touched by this slice.
- Keep private setup metadata out of Agent View and public runtime-map payloads.
- Add or adjust report/private artifact fields for relocation provenance.

## Acceptance Criteria

- The operator console no longer shows `Generated mess count`.
- The operator console shows `Environment setup` and only shows
  `Relocation count` when a relocation setup is selected.
- Cleanup launches default to `environment_setup=relocate-cleanup-related-objects`.
- Map-build and open-ended launches default to `environment_setup=baseline`.
- Launch argv and API tests prove the console sends `environment_setup` /
  `relocation_count`, not `generated_mess_count`.
- Agent View fixtures/tests prove relocation setup metadata is not exposed to
  the agent.
- Report/private artifact tests prove relocation provenance remains visible for
  human review and private evaluation.
- Stale-path searches show no active public operator-console label or route
  argument named `Generated mess count` or `generated_mess_count`.

## Verification Ladder

Deterministic gates:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_routes.py tests/unit/operator_console/test_operator_console.py tests/unit/operator_console/test_static_assets.py`
- Focused household tests covering Agent View/private report relocation
  boundaries after implementation.
- `ruff check .`
- `ruff format --check .`
- `rg -n "Generated mess count|generated_mess_count|Mess up" roboclaws docs tests just`
  with any remaining hits explained as historical/private-only or removed.

Integration gates:

- Route/catalog tests must prove supported console routes resolve with
  `environment_setup` and `relocation_count`.
- Launch construction tests must prove cleanup, map-build, and open-ended
  requests send the new setup arguments and do not send `generated_mess_count`.
- Report/artifact tests must prove relocation provenance stays in private or
  report evidence and does not enter Agent View.

Product run gates:

- Operator console manual/browser proof:
  `just console::run`, select a cleanup route, a map-build route, and an
  open-ended goal route, and verify the setup controls and command preview show
  `Environment setup` / `Relocation count` instead of `Generated mess count`.
- Cleanup coding-agent proof:
  `just run::surface surface=household-world driver=codex intent=cleanup evidence_lane=world-oracle-labels backend=molmospaces_subprocess seed=7 environment_setup=relocate-cleanup-related-objects relocation_count=5`
- Map-build coding-agent proof:
  `just run::surface surface=household-world driver=codex intent=map-build evidence_lane=world-oracle-labels backend=molmospaces_subprocess seed=7 environment_setup=baseline`
- Open-ended coding-agent proof:
  `just run::surface surface=household-world driver=codex intent=open-ended evidence_lane=world-oracle-labels backend=molmospaces_subprocess seed=7 environment_setup=baseline prompt="帮我找遥控器"`

Local/live/manual gates:

- The Codex product run gates require repo-local provider configuration and the
  supported Docker-backed coding-agent route. If provider keys, Docker, MuJoCo,
  or operator-browser validation are unavailable, the implementation may land
  only as an intermediate branch and must report `BLOCKED_NEEDS_LOCAL_VALIDATION`
  rather than claiming complete/no-regression success.
- Do not require Isaac, Agibot G2 hardware, OpenClaw Gateway, or real VLM
  evidence unless implementation unexpectedly changes those paths.

## Open Implementation Defaults

- Whether to reuse `seed` for relocation determinism or introduce
  `relocation_seed`.
- Exact private artifact field names for relocation provenance.
- Whether cleanup direct-run defaults outside the operator console should change
  in the same slice or a follow-up slice.

## Preflight Contract

**Preflight status:** Draft
**Route:** durable `intuitive-flow`

Goal:
Implement the environment setup relocation contract so operator-console setup
is task-neutral, relocation is private setup truth, and the old public
`generated_mess_count` surface is removed.

Scope:

- Replace operator-console `Generated mess count` UI with `Environment setup`
  and conditional `Relocation count`.
- Add public setup args: `environment_setup` and `relocation_count`.
- Remove active public `generated_mess_count` usage in the console/run surface
  touched by this slice.
- Wire cleanup/map-build/open-ended defaults as agreed.
- Keep relocation metadata out of Agent View.
- Preserve relocation provenance in private/report artifacts.
- Update focused docs/tests.

Non-goals:

- No goal-target relocation extraction.
- No new MCP tool or task intent.
- No backward compatibility for old public names.
- No Isaac, Agibot G2 hardware, OpenClaw Gateway, or physical robot validation
  unless implementation unexpectedly changes those paths.

Context package:

- Must read:
  - `docs/plans/environment-setup-relocation-contract.md`
  - `CONTEXT.md`
  - `docs/human/domain.md`
  - `roboclaws/operator_console/routes.py`
  - `roboclaws/operator_console/static/index.html`
  - `roboclaws/operator_console/static/app.js`
  - `roboclaws/operator_console/launcher.py`
  - `roboclaws/launch/catalog.py`
  - `roboclaws/launch/intents.py`
- Useful evidence:
  - `tests/unit/operator_console/test_routes.py`
  - `tests/unit/operator_console/test_operator_console.py`
  - relevant household cleanup scenario/report tests discovered by
    `rg generated_mess_count`
- Do not read unless needed:
  - old phase logs, retrospectives, large output artifacts, full contract
    checker files.

Definition of Done:

- Success only if all deterministic, integration, product run, and required
  local/live/manual gates above pass or are explicitly classified.
- `BLOCKED_NEEDS_DECISION` if implementation needs target-specific relocation
  semantics now, or if cleanup scoring cannot distinguish relocation setup from
  public Agent View without a new contract decision.
- `BLOCKED_NEEDS_LOCAL_VALIDATION` if provider keys, Docker, MuJoCo, or
  operator-browser validation are unavailable for the required product run
  gates.
- Must not regress route catalog validation, provider/port/lock gates, cleanup
  private scoring boundaries, or map-build runtime-map evaluation.

Execution surface:

- Main session supervises scope, diff, verification, and final status.
- Worker: none by default; use the main session unless implementation grows
  unexpectedly.

To execute:

```text
/goal execute docs/plans/environment-setup-relocation-contract.md with intuitive-flow
```
