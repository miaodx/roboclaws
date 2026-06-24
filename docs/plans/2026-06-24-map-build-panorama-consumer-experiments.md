---
plan_scope: map-build-panorama-consumer-experiments
status: DRAFT
created: 2026-06-24
last_reviewed: 2026-06-24
implementation_allowed: false
source:
  - user discussion on making dedicated MapBuild improve downstream open-ended and cleanup tasks
  - current MapBuild default/config and Runtime Metric Map prior audit
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md
  - docs/plans/2026-06-15-non-cleanup-eval-support.md
  - docs/plans/2026-06-16-open-ended-eval-matrix-expansion.md
  - docs/human/mcp-skills-and-semantic-profiles.md
---

# MapBuild Panorama And Downstream Consumer Proof

## Goal

Make dedicated `preset=map-build` produce richer public Runtime Metric Map
evidence, then prove that the result improves downstream open-ended household
goals and cleanup runs.

The success claim is not "MapBuild writes an artifact". The success claim is:

- open-ended tasks find requested stable anchors or target categories with less
  search;
- cleanup tasks use the prior as useful context without treating stale movable
  objects as immediately actionable;
- model/provider profiles expose whether stronger tool-use and prior-use
  behavior changes the measured benefit;
- reports and evals expose the difference with tool-call, observation, and
  time-to-target metrics.

## Owning Layers

- Product run: keeps the public command shape,
  `just run::surface surface=household-world preset=map-build ...`, plus
  existing open-ended and cleanup consumer runs.
- Skills/prompts: own the MapBuild scan strategy and downstream prior-use
  policy.
- MCP tools: expose primitive robot capabilities only. Use the existing
  `navigate_to_relative_pose(..., yaw_delta_deg=...)` body-turn primitive
  before adding any composite "rotate 360" tool.
- Runtime Metric Map: owns semantic enrichment, public anchors, observed-object
  evidence, target candidates, and Runtime Map Prior Snapshot output.
- Eval suites and reports: own comparison experiments, aggregate metrics, and
  pass/fail thresholds.
- Server/runtime adapters: stay thin transport and lifecycle plumbing.

## Current State

Dedicated MapBuild currently defaults to the household-world map-build route
with camera-grounded labels. It produces Runtime Metric Map artifacts, but the
current proof does not yet show that those artifacts improve later open-ended
or cleanup behavior.

Known behavior from the current audit:

- direct MapBuild visits inspection waypoints and uses a small camera yaw sweep;
- SDK MapBuild asks the agent to inspect waypoints and use `adjust_camera` when
  evidence is incomplete, but does not require robot-body panorama scanning;
- `adjust_camera` only changes camera yaw/pitch within a bounded range and
  resets after navigation;
- robot-relative body turns already exist through
  `navigate_to_relative_pose(yaw_delta_deg=...)`;
- operator-console `turn left` / `turn right` already exercise the same
  relative-navigation control concept;
- cleanup consumes a previous MapBuild only when an explicit
  `runtime_map_prior=...` artifact is provided;
- prior movable-object observations are non-actionable until confirmed by
  current run evidence.

## Product Hypothesis

MapBuild should be most useful when it prebuilds stable semantic context:

- large fixtures: sofa, cabinet, fridge, bed, table, shelf;
- surfaces and receptacles: table top, counter, shelf, cabinet area, sink area;
- room or area anchors: kitchen, living room, dining area, hallway;
- navigation-visible landmarks that help future target search.

Movable objects are still worth recording, but they are weaker priors because
they can move between MapBuild and the consumer run. Downstream agents may use
them to choose where to look first, but must re-observe before acting.

## Proposed MapBuild Change

### 1. Add A Scan Profile Contract

Introduce an explicit MapBuild scan profile in the map-build task/runtime
configuration, without changing the public MCP tool set.

The scan profile starts as task/runtime or eval-row configuration. It is not a
new public `just run::surface` launch axis unless a later review explicitly
approves that command-surface growth. The baseline `standard` profile must stay
runnable after the dedicated MapBuild default changes, otherwise the downstream
A/B comparison loses its denominator.

Initial profiles:

| Profile | Behavior | Intended Use |
| --- | --- | --- |
| `standard` | Current waypoint inspection plus small camera yaw sweep | cheapest regression baseline |
| `panorama` | At each inspection waypoint, rotate robot body through bounded headings and observe after each turn | richer Runtime Metric Map evidence |
| `fixture-focused` | Panorama scan plus prompt/report emphasis on stable fixtures, surfaces, receptacles, and room anchors | default dedicated MapBuild candidate |

Dedicated `preset=map-build` should default to `fixture-focused` once the
profile is implemented and verified. Regular cleanup should not inherit the
extra rotation cost by default.

### 2. Use Existing Body-Turn Primitive First

Do not add a new `rotate_360` MCP tool in the first implementation.

At each inspection waypoint, `panorama` / `fixture-focused` should use repeated
bounded calls equivalent to:

```text
observe
navigate_to_relative_pose(forward_m=0, lateral_m=0, yaw_delta_deg=90)
observe
navigate_to_relative_pose(forward_m=0, lateral_m=0, yaw_delta_deg=90)
observe
navigate_to_relative_pose(forward_m=0, lateral_m=0, yaw_delta_deg=90)
observe
navigate_to_relative_pose(forward_m=0, lateral_m=0, yaw_delta_deg=90)
```

The exact heading count can be configurable, but the first experiment should
use four headings so reports can compare a clear panorama budget against the
current camera-only scan.

Add a composite `rotate_360` MCP tool only if execution traces show repeated
body-turn calls are a real agent reliability problem rather than just a prompt
or direct-runner profile concern.

### 3. Clarify Stable Versus Movable Prior Semantics

MapBuild output should distinguish:

- stable semantic anchors: fixtures, room/area anchors, surfaces, receptacles;
- movable observations: objects seen at a waypoint or on a surface, with
  observation timestamp/provenance and current-confirmation required;
- target candidates: public search candidates that can seed future inspection,
  not hidden fixture truth.

Downstream cleanup and open-ended prompts should explicitly say:

- use stable MapBuild anchors as preferred search/navigation priors;
- use movable-object prior observations only to choose the next look location;
- do not pick, place, or declare success on a movable prior without current
  observation evidence.

## Targeted Experiments

Run experiments as paired A/B comparisons. Each pair should use the same world,
seed, backend, agent engine, provider profile, prompt, and generated mess setup
where applicable.

### Comparison Result Contract

The existing `map_build_consumer` suite is a useful baseline contract, but it is
not enough to prove downstream improvement by itself. The implementation should
add an explicit comparison result artifact or eval-report section for these
experiments.

Each comparison should record:

- variant ids: `no_prior`, `standard_prior`, `fixture_focused_prior`;
- denominator parity: same world, seed, backend, prompt, generated mess setup,
  agent engine, provider profile, and timeout class where applicable;
- model/provider identity: `provider_profile`, resolved model id, wire API,
  thinking mode, route-health verdict, and provider/runtime blocker if any;
- first relevant evidence step/time;
- first actionable object discovery step/time for cleanup;
- per-tool request counts for `observe`, `adjust_camera`,
  `navigate_to_waypoint`, and `navigate_to_relative_pose`;
- current-evidence source used for the final claim or action;
- prior-use verdict: `stable_anchor_used`, `movable_hint_rechecked`,
  `prior_ignored`, `stale_prior_rejected`, or `unsafe_prior_use`;
- comparison label: `improved`, `no_regression`, `inconclusive`, or
  `regressed`, with a short machine-readable reason.

Live-agent comparisons are noisy. A live result can support the claim only when
the comparison artifact preserves denominator parity and separates behavior
failure from provider/runtime unavailability.

### Model Matrix Axis

Run the consumer experiments across several OpenAI Agents SDK provider/model
routes. This is a second experiment axis, not a replacement for the MapBuild
prior axis.

Initial target matrix:

| Label | `provider_profile` | Model | Notes |
| --- | --- | --- | --- |
| GPT | `codex-router-responses` | `gpt-5.5` | Preferred product route when provider capacity is healthy. |
| MiMo 1000 | `mimo-inside-openai-chat` | `mimo-1000` | On-demand benchmark/text route; verify tool transport before counting behavior. |
| Kimi K2.7 Code | `kimi-openai-chat` | `kimi-k2.7-code` | Experimental SDK route; keep canonical model id. |
| MiniMax M3 | `minimax-responses` | `MiniMax-M3` | Current explicit MiniMax Responses route. |

Rules:

- Do not compare models by overriding model ids across incompatible provider
  profiles. Use the cataloged profile/model pair.
- First isolate prior-consumption behavior by building one canonical
  `fixture-focused` prior, then running the same open-ended and cleanup
  consumer prompts against every model profile.
- Separately test SDK MapBuild quality per model only after the canonical-prior
  consumer comparison exists. SDK MapBuild quality answers "which model builds
  the better map"; canonical-prior consumer runs answer "which model uses the
  same map better."
- Provider route health is not behavior. If a route fails preflight, rate
  limit, authentication, transport, or tool-call support, mark the cell
  `provider_unavailable` or `tool_transport_blocked`, not `regressed`.
- MiMo 1000 and Kimi K2.7 Code are useful for tool-use behavior comparison, but
  they should not silently become default cleanup product routes from this
  experiment.

### Parallel Execution Strategy

The target local execution shape is four concurrent model-profile cells per
experiment wave, one for each provider/model profile above.

Parallelism requirements:

- Every cell must use its own run directory, log directory, MCP/server port
  allocation if applicable, and comparison cell id.
- Shared inputs such as the canonical Runtime Map Prior Snapshot should be
  read-only.
- Do not run two cells that mutate the same simulator scene instance, output
  path, lock file, or operator-console route state.
- Record `parallel_group_id`, `concurrency_width`, start/end time, and per-cell
  route-health status in the comparison artifact.
- If a backend, provider, port allocator, detector, or simulator lock prevents
  safe parallel execution, keep the same matrix but execute the blocked cells in
  queued waves and record the reason.

Recommended wave order:

1. Deterministic MapBuild baseline: direct-runner `standard` and
   `fixture-focused` profiles, producing canonical prior artifacts.
2. Four-way model consumer wave for open-ended stable-anchor search using the
   same canonical prior.
3. Four-way model consumer wave for cleanup using the same canonical prior and
   same generated mess setup.
4. Optional four-way SDK MapBuild wave, comparing whether each model can build
   the richer map itself.

### Experiment A: Open-Ended Stable Anchor Search

Purpose: prove that MapBuild helps tasks whose target is a stable fixture,
surface, receptacle, or area anchor.

Example prompts:

- "find the fridge and report where it is"
- "find a cabinet or shelf that could store household items"
- "go to the table or countertop area and summarize what you can see"
- "find the sofa or living-room seating area"

Variants:

- no runtime prior;
- prior from `standard` MapBuild;
- prior from `fixture-focused` MapBuild.
- the same three prior variants across each target model profile when live
  route health allows.

Required metrics:

- success/failure and terminate reason;
- time to first relevant target evidence;
- current public evidence source for the final report;
- number of `navigate_to_waypoint` calls;
- number of `navigate_to_relative_pose` body turns;
- number of `adjust_camera` calls;
- number of `observe` calls;
- whether the final report cites current public evidence.

Expected result: `fixture-focused` prior should reduce target-search steps or
time-to-first-target versus no prior, while preserving current-evidence proof.
If the agent reaches a plausible target only because of private fixture truth
or a prior that was not re-observed, the sample must fail even if the final text
sounds correct.

### Experiment B: Open-Ended Movable Object Search

Purpose: test whether MapBuild can seed search for movable objects without
creating false confidence.

Example prompts:

- "find the remote control"
- "find something useful to drink"
- "find a small object on a table or shelf"

Variants:

- no runtime prior;
- prior from `fixture-focused` MapBuild;
- optional changed-scene variant where the movable object is relocated after
  MapBuild.
- the same prior/no-prior split across each target model profile when live
  route health allows.

Required metrics:

- same search metrics as Experiment A;
- whether the agent uses the prior as a search hint instead of final truth;
- whether stale prior evidence is rejected or rechecked when current evidence
  disagrees.

Expected result: MapBuild may reduce first-look search cost when the object is
still near the prior, but must not be counted as success without current
observation. The changed-scene variant should validate stale-prior safety.
This experiment is safety evidence first and optimization evidence second.

### Experiment C: Cleanup With And Without Runtime Prior

Purpose: prove that MapBuild improves cleanup task efficiency while preserving
actionability rules.

Variants:

- cleanup with no `runtime_map_prior`;
- cleanup with `standard` MapBuild prior;
- cleanup with `fixture-focused` MapBuild prior.
- the same three prior variants across each target model profile when live
  route health allows.

Required metrics:

- cleanup success/failure and terminate reason;
- number of moved objects;
- first actionable object discovery step;
- total `observe`, `adjust_camera`, `navigate_to_waypoint`, and
  `navigate_to_relative_pose` counts;
- stale-prior checks: movable prior candidates require current confirmation;
- report evidence: actions cite current observation, not only prior evidence.

Expected result: `fixture-focused` prior should reduce exploratory camera or
navigation attempts by making likely surfaces/receptacles easier to inspect.
It must not increase false-positive cleanup actions from stale movable-object
observations.

Cleanup may ship with a `no_regression` result only if the report explicitly
says MapBuild consumer value is not yet proven for cleanup and stale-prior
safety is preserved. It must not present `no_regression` as proof of cleanup
optimization.

### Experiment D: MapBuild Coverage Quality

Purpose: show that the new MapBuild scan profile actually creates richer map
evidence before consumer runs.

Compare `standard` versus `fixture-focused` MapBuild reports. Compare
direct-runner MapBuild first. Then compare SDK MapBuild across the target model
profiles as a separate model-build-quality experiment, not as the canonical
denominator for consumer proof.

Required metrics:

- inspection waypoint count;
- body-heading observations per waypoint;
- stable anchor count by category;
- surface/receptacle anchor count;
- room/area anchor count;
- movable observation count;
- target candidate count;
- per-run cost: wall time and tool-call counts.

Expected result: `fixture-focused` should produce materially more stable
anchors and surface/receptacle evidence than the current camera-only baseline,
with an explicit runtime/tool-call cost.

Stable-anchor counts should be bucketed from public runtime-map evidence, not
private fixture tables. The initial buckets should be fixtures,
surfaces/receptacles, room/area anchors, and navigation-visible landmarks.

## Acceptance Criteria

Implementation is complete only when all of these are true:

- `preset=map-build` has an explicit scan profile contract and a documented
  default.
- The first implementation uses existing robot-relative body turns instead of
  adding a new MCP composite tool.
- MapBuild prompts and direct-runner behavior agree on stable-anchor priority
  and movable-prior safety.
- Runtime Map Prior Snapshot consumption keeps prior movable objects
  non-actionable until current confirmation.
- At least one open-ended stable-anchor experiment shows a measurable downstream
  improvement from `fixture-focused` MapBuild versus no prior.
- At least one cleanup experiment shows either improved efficiency or a clear
  no-regression result with explicit explanation; false-positive stale-prior
  actions are not allowed.
- Reports expose enough metrics to compare search cost, camera cost, body-turn
  cost, and time-to-target across variants.
- The comparison artifact separates provider/runtime availability from agent
  behavior.
- `standard` remains available as the explicit baseline after the dedicated
  MapBuild default changes.
- The first live model matrix attempts the four target provider/model profiles:
  `codex-router-responses` / `gpt-5.5`,
  `mimo-inside-openai-chat` / `mimo-1000`,
  `kimi-openai-chat` / `kimi-k2.7-code`, and
  `minimax-responses` / `MiniMax-M3`.
- Parallel execution records concurrency width, isolated run dirs, and blocked
  cells rather than silently serializing or dropping model rows.

## Non-Goals

- Do not expose private fixture tables, scorer truth, or hidden relocation
  metadata to agents.
- Do not make cleanup automatically consume the latest MapBuild artifact by
  path convention; consumer runs must provide `runtime_map_prior=...`
  explicitly.
- Do not add a public `rotate_360` MCP tool unless the first implementation
  proves the repeated primitive calls are the blocker.
- Do not make regular cleanup runs perform panorama scanning by default.
- Do not count movable-object prior evidence as task success without current
  observation.
- Do not promote any tested model profile to the default product route as part
  of this experiment.

## Implementation Slices

### Slice 1: MapBuild Scan Profile

- Add scan profile configuration for MapBuild.
- Implement `standard`, `panorama`, and `fixture-focused` semantics where the
  current map-build runner and SDK prompts consume scan policy.
- Ensure the default dedicated MapBuild route selects the intended profile.
- Record profile, heading count, body turns, camera adjustments, and observe
  counts in run artifacts/reports.
- Keep scan profile out of the public launch grammar unless separately
  reviewed.

### Slice 2: Prior Semantics And Prompt Contract

- Update MapBuild prompt language to prioritize stable anchors and surfaces.
- Update downstream open-ended and cleanup prompt language to use priors as
  search context, with movable-prior current-confirmation required.
- Keep the Runtime Metric Map / Runtime Map Prior Snapshot schema explicit about
  stable anchors versus movable observations.
- Require SDK MapBuild and direct-runner MapBuild to both record whether
  `fixture-focused` actually exercised body-turn observations. If SDK traces do
  not use `navigate_to_relative_pose`, mark that variant not comparable instead
  of silently counting it as panorama proof.

### Slice 3: Experiment Harness Rows

- Add or extend eval-harness rows for:
  - MapBuild coverage comparison;
  - open-ended stable-anchor consumer comparison;
  - open-ended movable-prior safety comparison;
  - cleanup consumer comparison.
- Add a model-matrix execution mode for the comparison rows that expands each
  selected live consumer sample across the four target provider/model profiles.
- Support a bounded parallel wave width of four cells when run isolation and
  provider route health allow it.
- Prefer public command routes and existing eval-suite infrastructure over
  bespoke scripts.

### Slice 4: Reports And Decision Thresholds

- Add report summaries that compare no-prior, `standard`, and
  `fixture-focused` variants.
- Include per-tool counts and time-to-target metrics.
- Mark results as `improved`, `no_regression`, `inconclusive`, or `regressed`
  with the reason visible in report data.
- Aggregate results by model/profile as well as by prior variant, so the report
  can show whether a model is better at using the same prior or better at
  building the prior.
- Keep private scorer truth, hidden target sets, generated-mess membership,
  relocation truth, and raw provider logs out of public reports and eval
  manifests.

## Verification Plan

Deterministic gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/evals \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup
```

MapBuild product proof:

```bash
just run::surface surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  preset=map-build \
  agent_engine=direct-runner \
  evidence_lane=camera-grounded-labels \
  camera_labeler=grounding-dino
```

Open-ended consumer proof:

```bash
just run::surface surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  agent_engine=openai-agents-sdk \
  provider_profile=codex-router-responses \
  evidence_lane=world-public-labels \
  runtime_map_prior=<map-build-run>/runtime_map_prior_snapshot.json \
  prompt="find the fridge and report where it is"
```

Cleanup consumer proof:

```bash
just run::surface surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  preset=cleanup \
  agent_engine=openai-agents-sdk \
  provider_profile=codex-router-responses \
  evidence_lane=world-public-labels \
  runtime_map_prior=<map-build-run>/runtime_map_prior_snapshot.json
```

Eval-harness proof after rows exist:

```bash
just agent::eval recommend plan=docs/plans/2026-06-24-map-build-panorama-consumer-experiments.md budget=focused
just agent::eval execute since=<base> budget=focused
```

Model-matrix proof after rows exist:

```bash
just agent::eval execute \
  plan=docs/plans/2026-06-24-map-build-panorama-consumer-experiments.md \
  budget=focused \
  agent_engine=openai-agents-sdk \
  provider_profile=codex-router-responses,mimo-inside-openai-chat,kimi-openai-chat,minimax-responses \
  live_execution=run
```

The implementation may expose the four-way matrix through a more specific
eval-harness argument if needed, but the final report must preserve the same
profile/model cells and comparison contract.

Local/live/manual gates:

- OpenAI Agents SDK runs require a healthy provider profile and repo-local
  credentials.
- The active behavior-proof provider row should use a currently healthy
  OpenAI Agents SDK profile. Provider-availability rows such as a transient
  `codex-router-responses` failure may be reported separately, but they do not
  prove or disprove MapBuild behavior.
- Each target model route needs a route-health preflight before being counted
  as behavior evidence. Missing credentials, provider outage, model/profile
  incompatibility, or tool-transport failure blocks only that cell.
- Camera-grounded MapBuild with Grounding DINO may require local detector
  availability.
- Real-robot or non-Molmo backend confirmation is out of scope for the first
  implementation unless requested separately.

## Stop Gates

- Stop if MapBuild would need private fixture/scorer truth to show improvement.
- Stop if the implementation would make prior movable objects actionable
  without current observation.
- Stop if body-turn support is missing in the selected backend rather than
  silently falling back to camera-only scanning.
- Stop before adding a new MCP composite tool unless the existing primitive
  route has been tried and measured.
- Stop before adding `scan_profile` or an equivalent knob to the public
  `just run::surface` grammar without plan or ADR review.
- Stop if an SDK/direct-runner comparison cannot preserve denominator parity but
  the report would still label the result `improved`.
- Stop if four-way parallel execution would share mutable simulator state,
  output paths, server ports, or lock files.
- Stop before substituting `mimo-mify-responses` / `xiaomi/mimo-v2.5` for the
  requested MiMo 1000 row without explicitly reporting that MiMo 1000 was not
  available.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/2026-06-24-map-build-panorama-consumer-experiments.md`

Canonical source: `docs/plans/2026-06-24-map-build-panorama-consumer-experiments.md`

Route: durable `$intuitive-flow`

Goal: implement MapBuild fixture-focused panorama scanning and prove downstream
benefit through targeted open-ended and cleanup experiments.

Scope:

- MapBuild scan profile contract and default dedicated MapBuild behavior.
- Prompt/direct-runner alignment for stable-anchor priority and movable-prior
  safety.
- Runtime/report metrics needed to compare downstream consumer behavior.
- Focused eval/product proof rows for open-ended and cleanup consumer impact.
- Four-profile OpenAI Agents SDK model matrix and bounded parallel execution
  reporting.

Non-goals:

- new MCP composite rotate tool in the first slice;
- automatic cleanup consumption of latest MapBuild output;
- private fixture truth exposure;
- regular cleanup panorama scanning by default;
- real-robot proof;
- product default model-route changes.

Acceptance:

- SUCCESS: deterministic tests pass, MapBuild product proof produces richer
  stable-anchor evidence, and at least one open-ended plus one cleanup consumer
  comparison reports useful downstream effect or explicit no-regression across
  the attempted model matrix cells.
- BLOCKED_NEEDS_DECISION: any request to add `rotate_360` before primitive
  body-turn measurements, any need to expose private truth, or any request to
  promote a model route to default product status.
- BLOCKED_NEEDS_LOCAL_VALIDATION: provider, detector, simulator, or credential
  route unavailable for product/eval proof.
- No regressions: existing no-prior open-ended and cleanup routes still run
  without requiring MapBuild artifacts.

To execute:

```text
/goal execute docs/plans/2026-06-24-map-build-panorama-consumer-experiments.md with intuitive-flow
```
