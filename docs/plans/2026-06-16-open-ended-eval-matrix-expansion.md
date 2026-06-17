---
plan_scope: open-ended-eval-matrix-expansion
status: IMPLEMENTED
created: 2026-06-16
last_reviewed: 2026-06-16
implementation_allowed: true
source:
  - user request to make eval harness carry most open-ended coding-agent and Agent SDK testing
  - live Codex CLI / OpenAI Agents SDK open-ended eval results on 2026-06-16
  - intuitive-reduce-entropy saturation loop
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md
  - docs/adr/0141-use-eval-harness-as-maintainer-orchestration-facade.md
  - docs/plans/2026-06-14-eval-driven-architecture.md
  - docs/plans/2026-06-15-non-cleanup-eval-support.md
  - evals/household_world/README.md
  - evals/household_world/suites/open_ended_goals.json
  - evals/household_world/samples/open_ended/drink_seed7.json
  - skills/eval-harness/scripts/eval_harness_rows.py
---

# Open-Ended Eval Matrix Expansion

Implemented on 2026-06-16 after grill-batch convergence. Scope remained the
eval-suite / eval-harness / report layer; UI/manual dogfood and money-cost
evaluation are intentionally out of scope.

## Goal

Turn open-ended household goals from a single live smoke sample into a small,
stratified eval matrix that can carry most coding-agent and OpenAI Agents SDK
validation in the background.

The matrix should let maintainers answer:

- Do open-ended household goals still run through the public no-preset route?
- Can Codex CLI and OpenAI Agents SDK finish both negative and positive
  open-ended tasks?
- Are failures caused by behavior, provider/runtime availability, weak evidence,
  or an underspecified task?
- Which prompt category regressed without requiring manual UI inspection?

## Owning Layers

- Eval suites: own open-ended sample definitions, sample metadata, graders,
  thresholds, aggregate metrics, and regression promotion.
- Eval harness: owns row selection, engine/provider live matrix selection,
  runtime-scope behavior, and background execution.
- Product run: remains the public route,
  `just run::surface surface=household-world prompt=<goal> ...`.
- Operator console UI: remains a small manual dogfood surface, not the primary
  proof mechanism.
- Server/runtime: remains transport and lifecycle plumbing only; do not move
  open-ended strategy or private success predicates into server adapters.

## Current Evidence

The previous open-ended coverage was real but too narrow: it had one
negative/ambiguous drink-search sample and no authoritative positive
public-evidence sample. The implemented suite now contains:

- `open_ended.drink_seed7`: negative search / clean not-found completion.
- `open_ended.room4_anchor_seed7`: area inspection using public waypoint
  evidence.
- `open_ended.living_waypoint_seed7`: positive observable waypoint task using
  public waypoint evidence.

Latest pre-implementation live proof status from 2026-06-16:

| Agent route | Provider profile | Result | Timing |
| --- | --- | --- | --- |
| Codex CLI | `codex-env` | passed | MCP trace `178.064s`; 35 tool calls |
| OpenAI Agents SDK | `codex-env` | blocked | about `43.7s`; provider returned HTTP 502, classified as `provider_transient_failure` / `upstream_unavailable` and surfaced to eval as `model_or_provider_unavailable` |
| OpenAI Agents SDK | `minimax` | passed | runner `99.594s`; MCP trace `87.635s`; 32 tool calls |

Implemented live proof status from the expanded 3-sample suite:

| Agent route | Provider profile | Result | Timing and calls | Artifact |
| --- | --- | --- | --- | --- |
| Codex CLI | `codex-env` | passed 3/3 | wall time sum `389.823s`, min `47.747s`, max `249.487s`; 38 tool calls, 76 tool events | `output/open-ended-eval-matrix/live/household_world_open_ended_goals/open-ended-expanded-codex-live-20260616-rerun3/eval_results.json` |
| OpenAI Agents SDK | `minimax` | passed 3/3 | wall time sum `225.632s`, min `43.119s`, max `134.131s`; 43 tool calls, 86 tool events; 43 model attempts, 43 successes, 0 failures | `output/open-ended-eval-matrix/live/household_world_open_ended_goals/open-ended-expanded-agent-sdk-minimax-live-20260616/eval_results.json` |
| OpenAI Agents SDK | `codex-env` | blocked 3/3 | classified as `model_or_provider_unavailable`; no behavior verdict | `output/open-ended-eval-matrix/live/household_world_open_ended_goals/open-ended-expanded-agent-sdk-codex-env-availability-20260616/eval_results.json` |

## Grill Decisions

Accepted on 2026-06-16:

- The first implementation must include at least one authoritative positive
  open-ended sample whose success is checked by public artifact evidence, not
  only by completion text.
- `openai-agents-sdk + minimax` is the required SDK behavior row for this plan.
  `openai-agents-sdk + codex-env` remains provider availability evidence while
  that route is returning provider-side 502 / upstream unavailable responses.
- Cleanup-adjacent open-ended tasks are excluded from the first sample matrix.
  The first version should cover negative search, positive observable target,
  and area or room inspection. Cleanup-adjacent goals can be added later after
  the basic positive/negative open-ended matrix is stable.
- UI/manual testing is explicitly excluded from this plan's acceptance gates.
  The harness live matrix is the completion proof; UI dogfood is optional
  follow-up evidence.

Runtime, token, and tooling policy:

- The plan does not evaluate money cost. Current provider strategy is token-plan
  or internal models; speed and operational reliability matter, but saving
  money alone is not a product objective. The existing
  `budget=smoke|focused|full` eval-harness argument remains command vocabulary
  for run depth. Do not add sample-level `cost_tier`, money-cost metrics, or
  money-cost thresholds.
- The existing eval-result identity schema still has a legacy
  `identity.budgets.cost` sentinel field for compatibility. This plan does not
  populate it as a metric, report on it, or use it as an acceptance criterion.

## Target Matrix

Expand `open_ended_goals` from one sample to a smoke matrix of 3-5 samples.
The first implementation should keep all samples on `molmospaces/val_0`,
`backend=mujoco`, and `evidence_lane=world-oracle-labels` unless discovery
proves another admitted world is more stable.

Sample categories:

| Category | Purpose | Example shape | Required proof |
| --- | --- | --- | --- |
| Negative or not-found | Agent should search, report inability, and terminate cleanly | existing drink goal | completion claim, artifact readiness, no privacy leak |
| Positive observable target | Agent should find a stable public object or object category | "find the visible X and report where it is" | public observation/anchor predicate |
| Room or area inspection | Agent should inspect a requested public area and summarize evidence | "go to Generated exploration candidate 5's area and report the public position" | visited/observed public anchor or waypoint evidence |
| Regression seed | Preserve a previously failed/blocked real run as a regression sample | promoted from eval result | source artifact and review label |

The first pass should include only samples whose target and proof can be derived
from public agent-facing evidence. Do not write prompts from private fixture
truth, private scoring manifests, hidden generated-mess sets, or full object
tables.

## Sample Metadata Contract

Add minimal metadata to open-ended samples instead of creating a broad predicate
DSL. The first useful fields are:

```json
{
  "open_ended_category": "negative_search|positive_observable|area_inspection|cleanup_adjacent|regression",
  "expected_goal_outcome": "not_found_clean_finish|public_target_observed|area_inspected|world_state_changed|blocked_reproduction",
  "success_predicate": {
    "predicate_id": "completion_claim|public_anchor_observed|observed_category_present|waypoint_or_area_visited|cleanup_outcome_satisfied",
    "authoritative": true
  },
  "tags": ["open-ended", "coding-agent", "agent-sdk"]
}
```

Rules:

- Keep `semantic_satisfaction_authoritative=false` for samples that only have a
  completion claim and report text.
- A positive sample can become authoritative only when the grader can check a
  public artifact, such as `runtime_metric_map.public_semantic_anchors`,
  observed-object evidence, waypoint/area visit evidence, or an existing cleanup
  outcome predicate.
- Store private goal references under `private_goal_reference` with
  `private_truth_scope=grader_only`.
- Do not expose private object IDs, private relocation truth, or scorer-only
  labels in the prompt or agent-facing artifacts.

## Grader Plan

Use a small extension to the existing open-ended grader:

1. Preserve existing hard gates: artifacts, privacy, trajectory, completion
   claim, and artifact readiness.
2. Add sample-level open-ended category and expected outcome to grader output.
3. Add public-evidence predicates for positive samples:
   `public_anchor_observed`, `observed_category_present`,
   `waypoint_or_area_visited`, and `cleanup_outcome_satisfied`.
4. Report advisory semantic satisfaction separately from authoritative
   public-evidence predicates.
5. Normalize failure classes so reports distinguish:
   `agent_no_completion_claim`, `artifact_missing`,
   `private_goal_not_satisfied`, `partial_progress_only`,
   `model_or_provider_unavailable`, and `environment_blocked`.

Do not add an LLM-as-judge gate in this slice. Human or model rubric labels can
be advisory metadata after deterministic evidence is in place.

## Harness Matrix

Eval harness should be the primary test surface. UI/manual testing should only
dogfood final operator flows after the harness has evidence.

Required rows:

| Row | Engine | Provider | Requirement |
| --- | --- | --- | --- |
| `open-ended-goals-eval-suite` | direct-runner | `not_applicable` | deterministic smoke suite |
| `codex-open-task-live-eval` | `codex-cli` | `codex-env` | required focused live row |
| `openai-agents-sdk-open-task-live-eval` | `openai-agents-sdk` | `minimax` | required focused live row |
| `openai-agents-sdk-codex-env-availability` | `openai-agents-sdk` | `codex-env` | provider availability row, not behavior gate while HTTP 502 / upstream unavailable persists |

Runtime-scope behavior:

- `smoke`: deterministic direct-runner suite and blocked/live readiness
  manifests only.
- `focused`: Codex CLI `codex-env` and OpenAI Agents SDK `minimax` live rows
  against the current open-ended suite.
- `full`: all open-ended samples, repeated trials for live rows, and any
  promoted regression samples.

Do not add sample-level runtime or cost tiers in the first implementation.
If sample subset selection becomes necessary later, add it as an eval-harness
run-depth concern, not as money-cost evaluation.

## Reporting

Eval reports should aggregate open-ended outcomes by:

- `open_ended_category`;
- `expected_goal_outcome`;
- `agent_engine`;
- `provider_profile`;
- `failure_class`;
- wall time, tool calls, and provider/model-service attempt counts when
  available.
- MCP tool call count, MCP tool event count, and per-tool counts.
- Live runner status, timeout status, and retryable provider failure details.

The report should make a provider outage visibly different from a behavior
failure. The `openai-agents-sdk + codex-env` 502 route should not fail the
Agent SDK behavior gate when `openai-agents-sdk + minimax` is the current
working SDK route.

## Implementation Slices

### Slice 1: Evidence Discovery And Sample Design

- Run or reuse a deterministic public-evidence discovery pass on
  `molmospaces/val_0`.
- Identify 2-4 candidate positive prompts from public agent-facing artifacts.
- Document why each target is public and stable enough for eval use.
- Reject any candidate whose only proof comes from private scorer truth.

Proof:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels
```

### Slice 2: Sample And Suite Expansion

- Add the selected open-ended samples under
  `evals/household_world/samples/open_ended/`.
- Update `evals/household_world/suites/open_ended_goals.json`.
- Add sample metadata fields for category, expected outcome, and success
  predicate.
- Keep sample count small: 3-5 total in the first version.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_models.py
just agent::eval suite=open_ended_goals budget=smoke
```

### Slice 3: Open-Ended Grader Predicates

- Extend the open-ended grader to evaluate sample-level public-evidence
  predicates.
- Keep semantic satisfaction advisory unless an authoritative predicate exists.
- Add regression tests for negative, positive, and artifact-missing cases.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_runner.py
```

### Slice 4: Harness Provider Matrix

- Make the OpenAI Agents SDK working behavior row use `provider_profile=minimax`
  unless explicit axes override it.
- Keep `openai-agents-sdk + codex-env` as provider availability evidence while
  it is blocked by upstream 502.
- Preserve Codex CLI `codex-env` as the required coding-agent live row.
- Add tests showing explicit provider axes still override defaults.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_harness_selector.py
just agent::eval recommend intent=open-ended agent_engine=codex-cli budget=focused
just agent::eval recommend intent=open-ended agent_engine=openai-agents-sdk provider_profile=minimax budget=focused
```

### Slice 5: Live Matrix Proof

Run the focused live matrix after deterministic gates pass:

```bash
set -a && source .env && set +a
just agent::eval suite=open_ended_goals budget=focused agent_engine=codex-cli provider_profile=codex-env live_execution=run live_timeout_s=240
just agent::eval suite=open_ended_goals budget=focused agent_engine=openai-agents-sdk provider_profile=minimax live_execution=run live_timeout_s=240
```

Record:

- final status;
- failure class;
- wall time;
- MCP tool calls and tool events;
- provider/model-service attempts and successes;
- output artifact path.

## Non-Goals

- No new public launch grammar.
- No UI-first validation workflow.
- No broad predicate DSL.
- No OpenClaw, Gateway, or system-provider Claude Code validation on the work
  network.
- No private scorer truth in prompts, sample public fields, or agent-facing
  artifacts.
- No requirement that `openai-agents-sdk + codex-env` pass while the provider
  route is returning HTTP 502 / upstream unavailable responses.
- No multi-world scale-out until `val_0` has a credible positive and negative
  smoke matrix.
- No cleanup-adjacent open-ended task in the first implementation.
- No money-cost optimization, cost metric, sample `cost_tier`, or cost threshold
  in this plan.
- No UI/manual run as a required acceptance gate.

## Acceptance Criteria

- `open_ended_goals` contains 3-5 open-ended samples spanning at least one
  negative sample and two positive non-cleanup-adjacent categories.
- At least one positive sample has an authoritative public-evidence predicate.
- Eval reports group results by open-ended category, engine, provider, and
  failure class.
- Eval reports include wall time, MCP tool calls/events, per-tool counts, and
  provider/model-service attempt counts when available.
- Harness focused recommendation selects Codex CLI `codex-env` and OpenAI
  Agents SDK `minimax` live rows for open-ended changes.
- Live focused matrix has current results for Codex CLI and OpenAI Agents SDK,
  or records explicit provider/runtime blockers with non-secret preflight
  evidence.
- Existing cleanup and map-build suites continue to pass their focused unit and
  contract gates.

## Implementation Closeout

Implemented changes:

- Expanded `open_ended_goals` from 1 to 3 samples:
  `open_ended.drink_seed7`, `open_ended.room4_anchor_seed7`, and
  `open_ended.living_waypoint_seed7`.
- Added public-evidence predicates for positive open-ended samples:
  `completion_claim`, `public_anchor_observed`, `observed_category_present`,
  and `waypoint_or_area_visited`.
- Made report aggregation include open-ended category, expected outcome,
  engine/provider, failure class, wall time, MCP tool calls/events, per-tool
  counts, and model attempt counts when available.
- Made the OpenAI Agents SDK behavior row default to `provider_profile=minimax`
  while keeping `openai-agents-sdk + codex-env` as provider availability
  evidence only.
- Removed the open-ended suite metadata field that named money-cost evaluation.

Verification run:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals tests/contract/dev_tools/test_eval_just_recipe.py tests/contract/dev_tools/test_task_agent_just_recipes.py::test_live_runners_open_ended_checker_drops_full_cleanup_gates tests/unit/agents/test_live_runtime.py
ruff check roboclaws/evals/live_runtime.py roboclaws/evals/runner.py roboclaws/evals/reports.py skills/eval-harness/scripts/eval_harness_rows.py skills/eval-harness/scripts/select_eval_harness.py skills/eval-harness/scripts/run_eval_harness.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_eval_harness_selector.py
git diff --check -- docs/plans/2026-06-16-open-ended-eval-matrix-expansion.md evals/household_world/README.md evals/household_world/suites/open_ended_goals.json roboclaws/evals/live_runtime.py roboclaws/evals/runner.py roboclaws/evals/reports.py skills/eval-harness/scripts/eval_harness_rows.py skills/eval-harness/scripts/select_eval_harness.py skills/eval-harness/scripts/run_eval_harness.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_eval_harness_selector.py tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Live proof artifacts:

- Codex CLI `codex-env`: passed 3/3 at
  `output/open-ended-eval-matrix/live/household_world_open_ended_goals/open-ended-expanded-codex-live-20260616-rerun3/eval_results.json`.
- OpenAI Agents SDK `minimax`: passed 3/3 at
  `output/open-ended-eval-matrix/live/household_world_open_ended_goals/open-ended-expanded-agent-sdk-minimax-live-20260616/eval_results.json`.
- OpenAI Agents SDK `codex-env`: blocked 3/3 as
  `model_or_provider_unavailable` at
  `output/open-ended-eval-matrix/live/household_world_open_ended_goals/open-ended-expanded-agent-sdk-codex-env-availability-20260616/eval_results.json`.

## Reduce-Entropy Loop

Selected mode: plan entropy mode.

Why: the user approved the direction and asked for one plan, then a
reduce-entropy loop over that plan before implementation.

Redirect: none.

Discovery intensity: saturation scan.

### Round 1: Existing Coverage Inventory

Reviewed:

- `evals/household_world/suites/open_ended_goals.json`
- `evals/household_world/samples/open_ended/drink_seed7.json`
- `skills/eval-harness/scripts/eval_harness_rows.py`
- `tests/unit/evals/test_eval_harness_selector.py`
- `roboclaws/evals/runner.py`
- `docs/plans/2026-06-15-non-cleanup-eval-support.md`
- current live eval artifacts summarized in status docs

Finding:

- The suite and live routes exist, so the next plan should not recreate
  first-class open-ended support.
- The material gap is sample diversity and authoritative positive-task grading.

Plan change:

- Scope narrowed to matrix expansion, sample metadata, positive predicates, and
  provider-row semantics.

### Round 2: False-Confidence Audit

Finding:

- A single negative/ambiguous drink sample can pass while positive open-ended
  behavior is broken.
- Provider availability can be confused with Agent SDK behavior when
  `openai-agents-sdk + codex-env` returns upstream 502.
- A positive prompt can leak private truth if samples are hand-authored from
  fixture internals instead of public evidence.

Plan change:

- Added explicit negative/positive/inspection/cleanup-adjacent categories.
- Required public-evidence discovery before adding positive samples.
- Split SDK `minimax` behavior row from SDK `codex-env` availability row.

### Round 3: Grader And Runtime-Scope Audit

Finding:

- Completion claim plus artifact readiness is necessary but insufficient for
  positive tasks.
- A broad predicate DSL would slow the slice and create another maintenance
  surface.
- Background capacity needs explicit run-depth behavior, or live eval expansion
  will either run too little or consume too much wall-clock by default.
- Money cost is not an optimization target for this plan; wall time,
  MCP/tool-call counts, provider/model attempt counts, retries, and timeout
  status are the operational metrics that matter.

Plan change:

- Added minimal sample metadata and four public-evidence predicate IDs.
- Kept semantic satisfaction advisory unless a deterministic predicate exists.
- Kept existing `budget=smoke|focused|full` command vocabulary as run-depth
  behavior, not money-cost behavior.
- Removed sample-level cost/runtime tiers and made runtime/tool telemetry a
  reporting requirement.

### Round 4: Saturation Check

Checked and parked:

- Multi-world open-ended scale-out: useful later, but premature before `val_0`
  has positive samples.
- UI-driven testing expansion: rejected as a primary proof route; keep it as
  final dogfood.
- LLM-as-judge: parked until deterministic public evidence is insufficient for
  a concrete prompt class.
- OpenClaw and system-provider Claude Code live coverage: blocked on current
  work-network policy and outside this plan.
- Raw-FPV open-ended coverage: parked until world-oracle open-ended matrix is
  stable.

Materiality gate result:

```text
eligible_count=4
rejected_count=5
stop_recommended=true
```

## Entropy Packet

Entropy source:

- False confidence from a one-sample open-ended suite.
- Provider availability drift hidden inside agent behavior rows.
- Positive open-ended success without authoritative public evidence.
- Manual UI testing pressure where background eval should own the proof.

Selected candidates:

1. P0: Expand `open_ended_goals` to a 3-5 sample stratified smoke matrix.
2. P1: Add public-evidence predicates for positive open-ended tasks.
3. P1: Make Codex CLI `codex-env` and Agent SDK `minimax` the focused live
   behavior rows, with SDK `codex-env` treated as provider availability.
4. P2: Add category/provider/failure-class aggregation to reports.

Entity budget:

- Reuse existing eval suite, eval sample, grader, report, and harness-row
  entities.
- Add only small sample metadata fields and predicate IDs.
- Do not create a new framework, public command, UI workflow, or broad DSL.

Verification:

- Deterministic eval model/runner/selector tests.
- `just agent::eval suite=open_ended_goals budget=smoke`.
- Focused live Codex CLI `codex-env`.
- Focused live OpenAI Agents SDK `minimax`.
- Provider availability evidence for OpenAI Agents SDK `codex-env` when it is
  still blocked.

Parked items:

- Multi-world scale-out.
- Raw-FPV open-ended suite.
- LLM-as-judge authoritative scoring.
- OpenClaw/system-provider Claude Code routes on work network.
- Exhaustive repeated-trial scheduling across more machines.

Saturation status:

- Saturated for this plan. A fourth loop found no new P0/P1 or material P2
  candidate inside the approved scope.

Recommended next action:

- No more grill discussion is needed for this plan. The implemented matrix is
  ready to use as the current background proof surface.

Shortcut:

- `use open_ended_goals matrix`
