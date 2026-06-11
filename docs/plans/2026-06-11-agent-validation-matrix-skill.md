# Agent Validation Matrix Skill

**Status:** Fully implemented; RAW-FPV behavior recovery parked
**Created:** 2026-06-11
**Last reviewed:** 2026-06-11
**Current implementation contract:** `just agent::harness agent-validation recommend|execute ...` selects and reports deterministic, product, live-agent, Agent SDK, perception, simulator, and map/cleanup-consumer gates from an explicit plan, `since=` diff, or explicit `changed_file=` / axis overrides. The retired fixed `codex-cleanup-harness8` and `molmo::codex-harness8` routes are unsupported.
**Related ADRs:** None yet.
**Supersedes / Superseded by:** Supersedes the fixed `skills/codex-cleanup-harness8` shape during implementation; no backwards-compatible command or preset is required.

## Problem

Roboclaws plans repeatedly hand-write which live/product gates to run. This is
fragile because the correct gates depend on what changed:

- Agent SDK changes need Agent SDK runs.
- cleanup skill or prompt changes need live coding-agent cleanup runs.
- MCP/server/checker changes need deterministic contract gates plus at least one
  affected live path.
- camera/visual-grounding changes need camera-grounded and DINO evidence.
- semantic-map and waypoint/actionability changes need map-build lanes and a
  cleanup consumer prior gate.

The current `codex-cleanup-harness8` skill is too narrow: it is a fixed Codex
cleanup grid with pinned `agent_engine=codex-cli` and
`provider_profile=codex-env`. The next useful abstraction is not "8 cases with
more flags"; it is a validation skill that can choose a matrix from the current
task.

## Decision

Create an adaptive Agent Validation Matrix skill under `skills/` and let it
replace the fixed 8-case harness skill. No backwards-compatible preset or command
surface is required.

This is a live-at-HEAD replacement. Do not preserve the old
`codex-cleanup-harness8` command, JSON schema, row naming, provider pinning, or
test contract unless the new selector independently chooses an equivalent row as
part of the adaptive matrix.

Proposed layout:

```text
skills/agent-validation-matrix/
  SKILL.md
  skill.json
  scripts/select_validation_matrix.py
  scripts/run_validation_matrix.py
```

The skill owns verification orchestration, not robot capability semantics:

- MCP tools and servers remain the capability surface and tested implementation.
- task skills such as `molmo-realworld-cleanup` still own agent behavior.
- this skill selects, explains, executes, and reports validation gates.

## Non-Goals

- Preserve the fixed 8-case `codex-cleanup-harness8` public surface.
- Preserve the old `codex_cleanup_harness8_v1` manifest schema.
- Keep `agent_engine=codex-cli` or `provider_profile=codex-env` pinned as
  special harness defaults.
- Keep stale tests, docs, wrappers, or scripts solely for compatibility.
- Move task behavior into the validation skill.

## Modes

`recommend`
: Select gates and explain why. Do not run commands.

`execute`
: Default mode for plan/implementation use. Run all relevant gates available in
  the current environment, including expensive provider-backed, DINO, simulator,
  live coding-agent, and Agent SDK gates when related.

`execute --budget=smoke`
: Cheap confidence only.

`execute --budget=focused`
: Default execution budget. Run required deterministic gates plus the smallest
  relevant live/product gates.

`execute --budget=full`
: Broader comparison matrix, including slower live-agent/provider variants when
  relevant.

Rule: do not skip an expensive gate because it is expensive. Skip only when it
is irrelevant, impossible in the current environment, blocked by network/key/
hardware/runtime, or explicitly budget-capped by the user.

## Matrix Axes

First-class axes:

- `agent_engine`: `direct-runner`, `codex-cli`, `openai-agents-sdk`,
  `claude-code` when relevant.
- `provider_profile`: `codex-env`, `mify`, `mimo-anthropic`,
  `kimi-anthropic`, and related supported profiles.
- `intent`: `map-build`, `cleanup`, `open-ended`, `navigate`,
  `photo-capture`, or other cataloged intents.
- `evidence_lane`: `world-oracle-labels`, `world-public-labels`,
  `camera-grounded-labels`, `camera-raw-fpv`, and future lanes.
- `camera_labeler`: `sim-projected-labels`, `grounding-dino`, or other
  supported camera labelers, only when valid for the evidence lane.
- `backend` / `world`: MuJoCo, Isaac, Agibot, AI2-THOR, and related launch
  catalog entries.

Model is recordable and overrideable, but not a primary comparison axis unless
the task is specifically provider/model behavior.

## Selection Rules

The first implementation should use deterministic rule tables from changed
files, plan text, and explicit user overrides. Do not add an LLM classifier in
the first version; selector output should be auditable from the matched signals
and rule table.

Examples:

| Change signal | Required validation direction |
| --- | --- |
| `roboclaws/agents/drivers/openai_agents_live.py`, Agent SDK runner scripts, SDK prompts | Agent SDK live/product gates |
| `skills/molmo-realworld-cleanup/**`, cleanup prompts, cleanup scratch/routine code | live coding-agent cleanup gates plus deterministic cleanup contracts |
| `realworld_mcp_server`, household contract, `done` readiness, checker/report contracts | focused MCP/server/checker tests plus at least one affected live/product row |
| `visual_grounding`, `camera_labeler`, DINO sidecar, camera-grounded evidence | camera-grounded sim control plus real `camera_labeler=grounding-dino` gate |
| `camera-raw-fpv`, RAW-FPV prompt/context/report | RAW-FPV direct or live run gate |
| `semantic-map-build`, Runtime Metric Map, target actionability, generated waypoints | map-build lane gates plus cleanup consumer with `runtime_map_prior=...` |
| launch catalog, provider profile, operator console launch route | route trace tests plus at least one representative product launch |

Every selected or skipped gate must include rationale in the output manifest.

## Output Contract

The skill writes a run directory such as:

```text
output/agent-validation-matrix/<stamp>/
  validation_matrix.json
  validation_matrix.md
  validation_matrix.html
  gates/<gate-id>/...
```

Each gate records:

- selected command;
- axes;
- reason selected;
- source signals from plan/diff/user input;
- status: `required_ran`, `required_blocked`,
  `required_skipped_by_user_budget`, `recommended_ran`,
  `recommended_skipped_irrelevant`, or `optional_not_run`;
- blocker category when not run;
- output artifacts and report links.

## Command Shape

Preferred public entry stays under the agent harness router:

```bash
just agent::harness agent-validation recommend \
  plan=docs/plans/2026-06-11-adaptive-target-inspection.md
```

```bash
just agent::harness agent-validation execute \
  plan=docs/plans/2026-06-11-adaptive-target-inspection.md \
  budget=focused
```

Diff-based use:

```bash
just agent::harness agent-validation execute \
  since=origin/main \
  budget=focused
```

Direct override examples:

```bash
just agent::harness agent-validation execute \
  plan=docs/plans/example.md \
  agent_engine=codex-cli,openai-agents-sdk \
  provider_profile=codex-env \
  evidence_lane=camera-grounded-labels,camera-raw-fpv
```

Do not expose this through `just run::surface`; that grammar remains for running
task/product surfaces, while this skill selects and orchestrates validation
gates around those surfaces.

After implementation, `codex-cleanup-harness8` and `molmo::codex-harness8`
should no longer be accepted command names. The only way to get the old-style
Codex cleanup row set is for the new selector to emit equivalent gates under
`agent-validation` because the current plan or diff actually needs them.

## Implementation Slices

1. Replace the fixed skill surface.
   - Add `skills/agent-validation-matrix`.
   - Replace `skills/codex-cleanup-harness8`; no compatibility command,
     tombstone preset, or legacy manifest is required.
   - Remove or replace `scripts/molmo_cleanup/run_codex_cleanup_harness8.py`
     and the copied skill wrapper script if it remains redundant.
   - Remove `codex-cleanup-harness8` from `just agent::harness` allowlists and
     replace the `just harness::codex-cleanup-harness8` and
     `just molmo::codex-harness8` recipes with `agent-validation` routing.
   - Remove or rewrite `docs/human/codex-cleanup-harness8.md` and remove stale
     links from `docs/human/README.md`.
   - Replace `tests/unit/molmo_cleanup/test_codex_cleanup_harness8.py` with
     tests for the adaptive selector and runner.
   - Replace contract tests that assert the old command is advertised or
     routable.
   - Keep the old 8-case behavior only if it naturally falls out as one
     recommended matrix, not as a preserved public contract.

2. Implement recommendation-only selection.
   - Parse plan path and/or git diff.
   - Produce `validation_matrix.json` and Markdown.
   - Cover the current common signals: cleanup skill, Agent SDK, visual
     grounding, RAW-FPV, map-build, MCP/checker, and launch catalog.
   - Emit a route trace showing which deterministic rule selected or skipped
     each gate.

3. Implement focused execution.
   - Run deterministic gates first.
   - Run relevant live/product gates unless blocked.
   - Classify blocked local/live gates honestly instead of silently downgrading
     to cheap substitutes.

4. Add reporting and docs integration.
   - Render HTML summary.
   - Add plan-template wording that points future plans to this skill.
   - Update `skills/README.md` and harness docs.

5. Broaden to full matrix support.
   - Add provider/profile variants when the task needs provider comparison.
   - Add optional Claude Code/OpenClaw/real-robot gates only when relevant and
     allowed by network/runtime gates.

## Live Doc Cleanup

The implementation must clean the active documentation surface so later agents
do not keep following the fixed harness by mistake:

- delete or rewrite `docs/human/codex-cleanup-harness8.md`;
- remove the fixed-harness link from `docs/human/README.md`;
- replace `skills/codex-cleanup-harness8/**` with
  `skills/agent-validation-matrix/**`;
- update `skills/README.md` to describe the adaptive validation skill as the
  maintained surface;
- replace tests that assert `codex-cleanup-harness8` or `molmo::codex-harness8`
  as live routes.
- add tests that prove the old route is no longer accepted and that equivalent
  Codex cleanup gates, when needed, appear only inside an `agent-validation`
  manifest.

Historical plans, retrospectives, and run reports should not be churned solely
for naming cleanup. Touch them only if they are indexed as current guidance or
are used by tests.

## Preflight Contract

**Preflight status:** Draft execution contract, ready for approval.
**Route:** durable `intuitive-flow`.
**Execution command:** `/goal execute docs/plans/2026-06-11-agent-validation-matrix-skill.md with intuitive-flow`

Goal: replace the fixed `codex-cleanup-harness8` route with an adaptive
`agent-validation` skill that recommends and executes relevant validation gates
from plan/diff signals.

Implementation scope:

- add `skills/agent-validation-matrix/` with manifest, instructions, selector,
  and runner;
- add `just agent::harness agent-validation recommend|execute ...`;
- remove old accepted routes: `codex-cleanup-harness8` and
  `molmo::codex-harness8`;
- replace active docs/tests that still teach or assert the old harness;
- implement deterministic rule-table selection first, including Agent SDK,
  cleanup, MCP/checker, visual grounding/DINO, RAW-FPV, map-build, and
  launch-catalog signals;
- produce JSON, Markdown, and HTML manifests with selected/skipped/blocked
  rationale.

Execution non-goals:

- no backwards compatibility, tombstone preset, old schema, or silent redirect;
- no LLM classifier in the first version;
- no task behavior moved into this skill;
- no churn of historical plans, retrospectives, or run reports unless they are
  current guidance or test-referenced.

Context package:

- must read: this plan, `CONTEXT.md`, `skills/README.md`, `just/agent.just`,
  `just/harness.just`, `just/molmo.just`,
  `skills/codex-cleanup-harness8/**`,
  `scripts/molmo_cleanup/run_codex_cleanup_harness8.py`,
  `tests/unit/molmo_cleanup/**`, and
  `tests/contract/dev_tools/test_task_agent_just_recipes.py`;
- useful evidence: `docs/human/codex-cleanup-harness8.md`,
  `docs/human/README.md`, and launch-catalog docs/tests;
- do not read unless needed: old retrospectives, output run artifacts, and
  historical plans that are not indexed as current.

Success criteria:

- the new `agent-validation` route works through `just agent::harness`;
- the old fixed-harness routes fail unsupported instead of redirecting;
- manifests explain selected, skipped, and blocked gates with source signals;
- active docs/tests no longer point future agents at the fixed harness;
- existing public task launch surfaces under `just run::surface` still work;
- public/private evidence boundaries and network/provider guards are preserved.

Stop states:

- `BLOCKED_NEEDS_DECISION` if implementation discovers a still-live user route
  that cannot be removed without breaking a current public contract;
- `BLOCKED_NEEDS_LOCAL_VALIDATION` if required live/provider/Docker/DINO/
  simulator gates cannot run in the current environment;
- `INTERMEDIATE_ONLY` only if explicitly approved before claiming complete,
  merge-ready, or no-regression.

## Verification

Deterministic implementation gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_agent_validation_matrix.py
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
ruff check skills scripts roboclaws tests
ruff format --check skills scripts roboclaws tests
```

New tests should prove:

- the old `codex-cleanup-harness8` and `molmo::codex-harness8` routes are no
  longer accepted;
- old-style Codex cleanup gates can appear only as selected rows inside a new
  `agent-validation` manifest;
- recommendation mode selects Agent SDK gates for Agent SDK changes;
- cleanup skill changes select live coding-agent cleanup gates;
- visual-grounding changes select real DINO gates;
- map-build/actionability changes select map-build lanes and cleanup consumer
  prior gates;
- expensive gates are not skipped by default when relevant;
- blocked live/local gates are reported as blocked, not passed;
- `agent_engine` and `provider_profile` are first-class matrix axes.

Required product gates for implementation closeout:

- one focused `recommend` run against this plan;
- one focused `execute` run against a small relevant local diff;
- one run that selects at least Codex cleanup and OpenAI Agents SDK gates when
  the diff touches both surfaces;
- one run that selects `camera_labeler=grounding-dino` for a visual-grounding
  change and marks it blocked only if the local sidecar/runtime is genuinely
  unavailable.

Hosted CI may stop at deterministic confidence: selector unit tests, manifest
shape, route-trace assertions, and recommendation-mode smoke runs. Full
`execute` validation is a local/live gate because provider keys, Docker gateway,
DINO sidecars, MuJoCo/Isaac, GPU, and hardware availability are environment
dependent.

## Implementation Evidence

Implemented in the 2026-06-11 local Flow slice:

- added `skills/agent-validation-matrix/` with `SKILL.md`, `skill.json`,
  deterministic selector, and runner;
- added `just agent::harness agent-validation recommend|execute ...`;
- removed the fixed `skills/codex-cleanup-harness8` skill, wrapper script,
  `scripts/molmo_cleanup/run_codex_cleanup_harness8.py`, and the
  `molmo::codex-harness8` route;
- replaced fixed-harness tests with adaptive selector/runner and route tests;
- cleaned active human/skill docs so they point to `agent-validation`.

Shipped evidence generated during this slice:

- `output/agent-validation-matrix/0611_plan_recommend/validation_matrix.json`
  and `.html`: focused recommend run against this plan.
- `output/agent-validation-matrix/0611_diff_execute_fixed/validation_matrix.json`
  and `.html`: focused execute run for cleanup + Agent SDK signals. It ran
  route/cleanup tests and direct product gates, selected live Codex and OpenAI
  Agents SDK gates, and recorded OpenAI Agents SDK as
  `required_blocked: missing_optional_dependency`.
- `output/agent-validation-matrix/0611_raw_fpv_active_session_block/validation_matrix.json`
  and `.html`: focused execute run proving live Codex active-session conflicts
  are reported as `required_blocked: live_session_active`, while direct RAW-FPV
  evidence ran and wrote `report.html`.
- `output/agent-validation-matrix/0611_visual_grounding_recommend_fixed/validation_matrix.json`
  and `.html`: focused recommend run proving visual-grounding changes select
  `camera_labeler=grounding-dino` without unrelated dirty-worktree widening.
- `output/agent-validation-matrix/0611_visual_grounding_execute/validation_matrix.json`
  and `.html`: local execute evidence from before the explicit-source
  isolation fix. It still proves the real DINO gate is selected and marked
  `required_blocked: dino_sidecar_unavailable` when the sidecar is not
  reachable.
- `output/agent-validation-matrix/0611_visual_grounding_execute/gates/codex-cleanup-world-oracle/run/0611_1329/seed-7/report.html`:
  serialized live Codex world-oracle cleanup finished after the active-session
  blocker cleared with `completion=success`, `restored=4/5`, and `sweep=1.0`.
- `output/agent-validation-matrix/0611_raw_fpv_serialized_codex/validation_matrix.json`
  and `.html`: focused RAW-FPV execute run launched after the active-session
  blocker cleared. The matrix records both RAW-FPV gates as run, but the live
  Codex row was detached and finalized after the matrix command returned. It
  stopped at 2026-06-11 14:13 CST with `exit=1`, no final
  `run_result.json`/`report.html`, and a RAW-FPV done-readiness failure at
  `output/agent-validation-matrix/0611_raw_fpv_serialized_codex/gates/codex-cleanup-camera-raw-fpv/run/0611_1347/seed-7`
  after cleaning 2 grounded objects; the runtime required 4 grounded cleanup
  chains before `done`.
  Check it with
  `just molmo::status output/agent-validation-matrix/0611_raw_fpv_serialized_codex/gates/codex-cleanup-camera-raw-fpv/run/0611_1347/seed-7`.
- Follow-up decision on 2026-06-11: leave RAW-FPV live Codex as a known
  performance/readiness limitation for this plan instead of blocking the
  validation-matrix skill closeout on a RAW-FPV behavior recovery slice.
- Follow-up fix on 2026-06-11: move `openai-agents==0.17.4` into the `dev`
  extra, while keeping the dedicated `openai-agents` extra, so the Agent SDK
  validation row is available after normal `uv sync --extra dev`.
- Follow-up fix on 2026-06-11: align the matrix DINO sidecar reachability
  default with the documented visual-grounding service port
  `http://127.0.0.1:18880`. The observed DINO block was connection refused
  before model inference, not a Grounding DINO inference failure.
- Follow-up rerun on 2026-06-11:
  `output/agent-validation-matrix/0611_dino_execute_rerun/validation_matrix.json`
  passed the focused visual-grounding matrix against the real sidecar. Selected
  gates `route-trace-contract-tests`,
  `direct-camera-grounded-sim-control`, and
  `direct-camera-grounded-grounding-dino` all passed. Grounding DINO is no
  longer a validation-matrix blocker for this plan.
- Follow-up rerun on 2026-06-11:
  `output/agent-validation-matrix/0611_agent_sdk_execute_rerun/validation_matrix.json`
  confirmed the Agent SDK row now gets past dependency/provider setup and starts
  the MCP-backed route through `codex-env`, but the live cleanup row fails before
  task execution with
  `Agent model must be a string, Model, or None, got _RetryingModel`. Treat this
  as an OpenAI Agents SDK driver compatibility follow-up, not an
  agent-validation matrix skill blocker.
- Follow-up fix on 2026-06-11: make `_RetryingModel` subclass the installed
  OpenAI Agents SDK `Model` interface when the optional SDK is available, while
  preserving importability without the optional dependency.
- Follow-up rerun on 2026-06-11:
  `output/agent-validation-matrix/0611_agent_sdk_execute_rerun_fixed/validation_matrix.json`
  passed the focused Agent SDK matrix. Selected gates
  `route-trace-contract-tests` and `openai-agents-sdk-cleanup` both passed.
  The live SDK cleanup run wrote `run_result.json`, `report.html`, and
  `live_timing.json` under
  `output/agent-validation-matrix/0611_agent_sdk_execute_rerun_fixed/gates/openai-agents-sdk-cleanup/run/0611_1507/seed-7/`,
  with `cleanup_status=success`, `restored_count=4`, semantic acceptability
  success, and `sweep_coverage_rate=1.0`.

Closeout decision for this plan:

- the adaptive matrix skill is implemented and has deterministic,
  recommendation, focused execute, real DINO, and live Agent SDK pass evidence;
- RAW-FPV live behavior recovery remains parked because the user accepted it as
  a known performance/readiness limitation.

Parked follow-ups:

- RAW-FPV live Codex recovery: keep the 4-chain done-readiness failure parked as
  a known RAW-FPV performance/readiness limitation, not a validation-matrix
  skill blocker. Source:
  `output/agent-validation-matrix/0611_raw_fpv_serialized_codex/gates/codex-cleanup-camera-raw-fpv/run/0611_1347/seed-7`.
  Unpark when RAW-FPV live-agent behavior is the target of a focused recovery
  slice, or when the validation policy explicitly requires RAW-FPV live success
  for matrix closeout.

## ADR Threshold

No ADR is required for the first implementation. Create an ADR only if the repo
decides that Agent Validation Matrix is the mandatory repo-wide verification
layer for all agent-facing plans or if the public command surface becomes a
durable contract future agents must not relitigate.

## Open Defaults For Implementer

- Prefer simple rule tables over an LLM classifier for the first version.
- Prefer JSON manifest first, HTML second.
- Keep command execution in scripts; keep strategy and operating instructions in
  `SKILL.md`.
- Reuse the existing launch catalog and underlying product commands for selected
  gates, while keeping this skill's public entry under `just agent::harness
  agent-validation`.
- Preserve public/private evidence boundaries: validation selection may inspect
  plans and diffs, but it must not expose hidden evaluator truth to agents.
