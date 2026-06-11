---
plan_scope: household-map-launch-open-ended-contracts
status: CONTINUE
created: 2026-06-11
last_reviewed: 2026-06-11
accepted_severities:
  - P1
  - P2
implementation_allowed: false
source:
  - user request to consolidate reduce-entropy directions into one plan file
  - intuitive-reduce-entropy discovery loop
  - room-category hint discussion for open-ended household goals
related_context:
  - CONTEXT.md#household-world-and-cleanup-vocabulary
  - docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md
  - docs/plans/refactor-reduce-entropy-minimal-semantic-map.md
  - docs/plans/refactor-evidence-lane-naming.md
  - docs/plans/task-surface-intent-goal-contract-refactor.md
  - docs/plans/operator-console-orthogonal-launch-refactor.md
---

# Household Map, Launch, And Open-Ended Contracts

Status: CONTINUE

This is a planning-only discovery artifact. Do not implement from this file
until a later workflow explicitly selects an execution slice.

## Loop Goal

Reduce current repo entropy around the household-world stack by collapsing
stale public abstractions, old compatibility surfaces, and repeated agent
rediscovery points.

The current target shape is:

```text
surface=household-world
  -> intent=map-build | cleanup | open-ended
  -> evidence_lane + optional camera_labeler
  -> Base Navigation Map
  -> Runtime Metric Map
  -> task skill / MCP tool loop
```

Current decision constraints:

- No backward compatibility is required for obsolete public surfaces.
- `Base Navigation Map` is the durable start-of-run map term. Historical
  `minimal` / `rich` map artifacts may still be read, but agents should not
  choose those modes as product behavior.
- Keep private evaluator truth and static fixture inventory hidden.
- Expose public room-category hints as search priors when available.
- For Agibot maps, derive `room_category_hints` only from public room/area
  anchors in `navigation_memory.json` or map context. If a map has no public
  room/area anchors, emit an empty hint list with unavailable provenance rather
  than guessing.
- For Gaussian/B1 map sources, do not treat Gaussian, PLY, mesh, or USD
  geometry as semantic truth. Expose room hints only from explicit public
  world/scene metadata or an attached robot-map overlay such as Map 12
  navigation memory; otherwise leave them empty.
- Let semantic-map-build and online observations produce fixture/object
  semantics as Runtime Metric Map evidence.
- Remove `fixture_hints()` from active MCP tools in the map-contract slice
  after prompts and tests migrate to Base Navigation Map + Runtime Metric Map
  discovery.
- Keep `smoke` as a verification preset or runner mode, not as
  `evidence_lane=smoke`. New public examples should use a preset axis such as
  `run_preset=smoke` with a real evidence lane, normally
  `evidence_lane=world-oracle-labels`.
- New open-ended artifacts should use `intent=open-ended`,
  `task_intent=open-ended`, and `goal_contract.intent=open-ended` directly;
  `task_intent_mode=custom` is historical compatibility only.
- Operator-console legacy route IDs are read-only history display only. New
  launches and reloads should use canonical launch selection ids.
- Keep historical report rendering best-effort, but do not preserve old command
  or API shapes as current product behavior.

## Discovery Rounds

### Round 1: Broad High-Noise Summary

Surface sampled with the reduce-entropy high-noise summary script:

- `.planning/` is large and historical; use only when resuming GSD.
- `docs/plans/` has 53 tracked plan files and is a live source of current and
  stale guidance.
- `tests/` has 198 tracked files and should be entered by targeted contract
  probes only.
- `tmp/` and `output/` are untracked local artifacts; no cleanup candidate was
  selected from them.

Deep-read trigger: active docs and code still reference old launch, evidence,
map, route, and fixture-hint concepts.

### Round 2: Targeted Contract Probes

Terms probed:

- `task::run`
- `profile=`, `cleanup_profile`, `--cleanup-profile`
- `map_mode`, `RICH_MAP_MODE`
- `fixture_hints`
- `visual_grounding`
- old lanes such as `world-labels`, `camera-labels`, `camera-raw`
- `smoke` as an evidence lane

Result: six already-discussed candidates remained material and one detail was
folded into the evidence-lane candidate: public docs say `smoke` is not a real
evidence lane, while examples and route validation still accept
`evidence_lane=smoke`.

### Round 3: Saturation Probes

Additional probes checked operator-console legacy route wrappers,
`task_intent_mode=custom`, current plan index/status drift, and Agent
Validation Matrix axis selection.

New material candidates found:

- operator-console legacy route wrappers still live behind catalog selections;
- `task_intent_mode=custom` still shadows first-class `intent=open-ended`;
- `STATUS.md` and `docs/plans/README.md` drift creates mandatory first-read
  confusion.

### Materiality Gate

The deterministic reduce-entropy materiality gate accepted all 9 candidates:

```text
eligible_count=9
rejected_count=0
stop_recommended=false
```

## Grill Batch 1 Decisions

Accepted on 2026-06-11:

- Use `Base Navigation Map` as the durable glossary term for current
  start-of-run map context. Keep `Minimal Navigation Map Artifact` only as
  historical/source-artifact language.
- Remove `fixture_hints()` from active MCP tools in the map-contract refactor.
  Historical report readers may still understand old `fixture_hints` artifacts.
- Replace public `evidence_lane=smoke` examples with an explicit smoke preset
  or runner setting plus a real evidence lane.
- Remove `task_intent_mode=custom` from new open-ended artifacts and runtime
  reasoning. Historical readers may tolerate it.
- Treat old operator-console route ids such as `codex-mujoco-cleanup` as
  read-only historical display records only.
- Candidate 5 is already implemented; keep it as an invariant/regression guard,
  not as a new execution candidate.

## Selected Candidates

### 1. Collapse Public Rich/Minimal Map Modes

Severity: P1

Entropy source: public contract drift between `map_mode=rich|minimal`,
Base Navigation Map, and Runtime Metric Map.

Materiality: live source drift, real workflow friction, recurring rediscovery.

Why now: open-ended goals need room-category search priors, but the current
`rich`/`minimal` abstraction forces agents to choose between blind sparse
navigation and overexposed static fixture truth.

Source-specific room hint policy:

- Agibot `navigation_memory.json` and map-context inputs may materialize public
  `room_area` anchors, such as `kitchen_center`, into Base Navigation Map
  `room_category_hints`. Fixture, receptacle, movable-object, and landmark
  anchors stay in Runtime Metric Map / Actionable Semantic Map Snapshot
  evidence.
- Gaussian/B1 inputs may materialize room hints only from explicit public scene
  metadata, world metadata, or an attached Agibot/Map12 overlay. Gaussian,
  PLY, mesh, and USD geometry alone must produce empty room hints and must not
  claim `semantic_anchors_are_usd_truth=true`.
- Empty room hints are valid when provenance is absent. Do not synthesize
  kitchens, bedrooms, or dining rooms from object/fixture guesses.

Impact radius: workflow.

Maintainer test: This removes a public map-mode choice that now misleads agents
about whether room hints, fixture truth, or runtime semantic evidence is
authoritative.

Affected paths:

- `docs/plans/refactor-reduce-entropy-minimal-semantic-map.md`
- `ARCHITECTURE.md`
- `just/README.md`
- `just/molmo.just`
- `just/agent.just`
- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/realworld_cleanup.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/cli/household_agent_server.py`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
- tests importing `RICH_MAP_MODE` or asserting rich static fixture behavior

Owner skill: intuitive-refactor.

Zen hint: one obvious map contract is better than parallel mode names with
hidden policy.

Pattern hint: no pattern; direct deletion and contract rename are clearer.

Suggested proof:

```bash
rg -n -F -e 'map_mode' -e 'RICH_MAP_MODE' -e 'rich' -- \
  README.md ARCHITECTURE.md docs/human docs/plans skills just roboclaws tests scripts
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Execution risk: high-impact execution slice because it removes a public option
and rewrites checker/report expectations. Keep it in a selected implementation
slice rather than mixing it into incidental docs cleanup.

### 2. Collapse Cleanup Profile Aliases Into Evidence Lane And Camera Labeler

Severity: P1

Entropy source: command and metadata names mix `profile`, `cleanup_profile`,
`evidence_lane`, `camera_labeler`, `visual_grounding`, and `smoke`.

Materiality: live source drift, real workflow friction.

Why now: the two-axis naming plan exists, but active commands and metadata still
carry compatibility-shaped names.

Impact radius: workflow.

Maintainer test: This prevents public runs from accepting profile-shaped names
and `evidence_lane=smoke` while docs say smoke is not a real lane.

Affected paths:

- `docs/plans/refactor-evidence-lane-naming.md`
- `roboclaws/household/profiles.py`
- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/cli/household_agent_server.py`
- `roboclaws/cli/agibot_map_build_agent_server.py`
- `roboclaws/launch/catalog.py`
- `just/molmo.just`
- `just/agent.just`
- `just/README.md`
- `AGENTS.md`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
- cleanup profile tests and route tests

Owner skill: intuitive-refactor.

Zen hint: explicit evidence and producer axes beat overloaded profile names.

Pattern hint: small Value Object or direct data table may help; do not preserve
old profile aliases as an adapter.

Suggested proof:

```bash
rg -n -F -e 'cleanup_profile' -e '--cleanup-profile' -e 'profile=' \
  -e 'visual_grounding=' -e 'evidence_lane=smoke' -- \
  README.md ARCHITECTURE.md AGENTS.md docs/human docs/plans skills just roboclaws tests scripts
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Execution risk: high-impact execution slice because it changes public CLI args,
artifact fields, and test fixtures. Keep historical readers best-effort without
preserving old public names as current behavior.

### 3. Finish Removing Legacy Task Route Shapes

Severity: P1

Entropy source: stale `task::run`, `household-cleanup`, and
`semantic-map-build` task IDs remain reachable or documented while
`run::surface` is canonical.

Materiality: stale surface, live source drift, real workflow friction.

Why now: root docs and launch architecture now use surface/intent, but CI rerun
strings, skills, private dispatch, and older docs still emit or normalize old
task names.

Impact radius: repo-wide.

Maintainer test: This stops generated reports, skills, CI rerun commands, and
private dispatch from pointing future users at removed or noncanonical route
shapes.

Affected paths:

- `.github/workflows/ci.yml`
- `skills/actionable-semantic-map-conversion/SKILL.md`
- `docs/human/agent-task-command-taxonomy.md`
- `just/agent.just`
- `just/molmo.just`
- `roboclaws/cli/agent_server.py`
- `roboclaws/launch/evaluation.py`
- route and command contract tests

Owner skill: intuitive-refactor.

Zen hint: one public command grammar should be obvious from every current
source.

Pattern hint: Facade is useful only at the private dispatch boundary; remove
public compatibility wrappers.

Suggested proof:

```bash
rg -n -F -e 'task::run' -e 'household-cleanup' -e 'semantic-map-build' -- \
  README.md ARCHITECTURE.md docs/human docs/plans skills just roboclaws tests scripts .github
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  intent=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  intent=cleanup agent_engine=direct-runner evidence_lane=world-oracle-labels
```

Execution risk: high-impact execution slice because current surfaces should be
changed while historical docs and logs should not be rewritten
indiscriminately. Leave historical records as history.

### 4. Reconcile Status And Plan Index Drift

Severity: P2

Entropy source: mandatory first-read docs do not reflect the current June
launch/map/open-ended focus.

Materiality: live source drift, recurring rediscovery.

Why now: every agent must read `STATUS.md` and often navigates
`docs/plans/README.md`; stale focus there costs time before any code task
starts.

Impact radius: workflow.

Maintainer test: The mandatory first-read dashboard can send agents toward
stale May Isaac work and force rediscovery of which June plans are active or
implemented.

Affected paths:

- `STATUS.md`
- `docs/plans/README.md`
- possibly supersession headers in selected `docs/plans/*.md`

Owner skill: intuitive-doc.

Zen hint: current truth should be short, explicit, and easy to find.

Pattern hint: no pattern; direct doc reconciliation is clearer.

Suggested proof:

```bash
sed -n '1,180p' STATUS.md
sed -n '1,180p' docs/plans/README.md
rg -n -F -e 'Status:' -e 'status:' -- docs/plans | sed -n '1,120p'
```

Execution risk: safe if limited to navigation/status metadata; do not rewrite
historical execution logs.

### 5. Keep Open-Ended Terminal Status Centralized

Severity: P1

Entropy source: artifact writer, checker, and operator-console Proof previously
derived terminal status from different fields.

Materiality: false confidence, live source drift.

Current status: implemented before this loop. Keep this item as a contract
invariant and regression guard while executing the surrounding open-ended
cleanup.

Why it stays in this plan: a recent operator-console run passed the open-ended
checker but showed Proof failed because cleanup-shaped status fields were
treated as terminal. Future removal of `task_intent_mode=custom` must preserve
the fixed intent-level status behavior.

Impact radius: workflow.

Maintainer test: This protects operator Proof from reporting failure when the
open-ended checker passed and cleanup scoring is only advisory.

Affected paths:

- `docs/plans/2026-06-11-open-ended-proof-status.md`
- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/operator_console/state.py`
- checker/report tests for open-ended and cleanup intent behavior

Owner skill: intuitive-refactor.

Zen hint: terminal outcome should have one authority per intent.

Pattern hint: State pattern is overkill; a small intent-aware status reducer is
clearer.

Suggested proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Execution risk: safe as a regression guard if kept intent-scoped; avoid
changing cleanup terminal semantics. Do not count this as a new implementation
slice unless regression coverage is missing after adjacent changes.

### 6. Align Agent Validation Matrix With Current Axes

Severity: P2

Entropy source: validation selector can become stale as task/profile/map-mode
surfaces are deleted or renamed.

Materiality: false confidence, live source drift.

Why now: `AGENTS.md` routes plans and diffs through Agent Validation Matrix;
after accepted refactors, stale rule signals could select the wrong gates or
miss required ones.

Impact radius: workflow.

Maintainer test: The validation matrix must not select stale
task/profile/map_mode gates after the route and map-contract refactors, or it
will hide missing product proof.

Affected paths:

- `skills/agent-validation-matrix/SKILL.md`
- `skills/agent-validation-matrix/scripts/select_validation_matrix.py`
- `skills/agent-validation-matrix/scripts/run_validation_matrix.py`
- `just/harness.just`
- tests for matrix recommendation and execution manifests

Owner skill: agent-validation-matrix plus intuitive-refactor.

Zen hint: verification should follow the public contract, not yesterday's
adapter names.

Pattern hint: Strategy/rule table already fits; keep rules deterministic and
auditable.

Suggested proof:

```bash
just agent::harness agent-validation recommend \
  plan=docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md budget=focused
just agent::harness agent-validation execute \
  plan=docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md budget=focused
```

Execution risk: safe if recommendation-mode is updated first; execution-mode
changes may touch local/live gate behavior and should report blocked gates
honestly.

### 7. Collapse Fixture-Hints-First Guidance Into Runtime Metric Map Discovery

Severity: P1

Entropy source: task skills and prompts still teach agents to start from
`fixture_hints` even though default task semantics should come from Base
Navigation Map, room-category hints, Runtime Metric Map anchors, and
`resolve_target_query`.

Materiality: real workflow friction, recurring rediscovery.

Why now: room-category hints are useful for open-ended search, but static
fixture hints should not be the default semantic source.

Impact radius: workflow.

Maintainer test: This prevents live agents from treating `fixture_hints` as the
primary semantic source when default tasks should use room hints, public
anchors, and `resolve_target_query`.

Affected paths:

- `skills/molmo-realworld-cleanup/SKILL.md`
- `skills/molmo-realworld-cleanup/scripts/target_query_recovery.py`
- `roboclaws/agents/prompts/household_cleanup.py`
- `roboclaws/household/realworld_mcp_server.py`
- `docs/human/mcp-skills-and-semantic-profiles.md`
- prompt and skill-manifest tests

Owner skill: intuitive-refactor.

Zen hint: teach the agent one semantic search path instead of a stale first
tool habit.

Pattern hint: no pattern; prompt/tool guidance consolidation is clearer.

Suggested proof:

```bash
rg -n -F -e 'fixture_hints' -e 'metric_map' -e 'resolve_target_query' -- \
  skills roboclaws/agents/prompts roboclaws/household docs/human tests
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
```

Execution risk: accepted direction is to remove `fixture_hints()` from active
MCP tools in the map-contract slice after prompt/test migration. Preserve
historical artifact/report reading as best-effort display only.

### 8. Collapse Operator-Console Legacy Route Wrappers

Severity: P1

Entropy source: operator console now has canonical launch selections, but
legacy route wrappers remain exported, accepted, and test-protected.

Materiality: stale surface, live source drift, real workflow friction.

Why now: the orthogonal launch refactor intended `route_id` to be only legacy
history display, but live server/query/test paths still accept route-style ids
such as `codex-mujoco-cleanup`.

Impact radius: module.

Maintainer test: This removes a live parallel route identity that still accepts
`codex-mujoco-cleanup` even though the console now operates on selection IDs.

Affected paths:

- `roboclaws/operator_console/routes.py`
- `roboclaws/operator_console/server.py`
- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/history.py`
- `roboclaws/operator_console/interactions.py`
- `roboclaws/operator_console/state.py`
- `roboclaws/operator_console/static/app.js`
- `tests/unit/operator_console/`

Owner skill: intuitive-refactor.

Zen hint: one operator launch identity should be enough.

Pattern hint: Adapter may remain for historical record parsing only; remove it
from launch and test APIs.

Suggested proof:

```bash
rg -n -F -e 'get_route(' -e 'list_console_routes' -e 'ConsoleRoute' \
  -e 'legacy_route_id' -e 'codex-mujoco-cleanup' -- \
  roboclaws/operator_console tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
```

Execution risk: accepted direction is read-only history only for old route ids.
Do not keep launch, reload, or semantic state lookup support through legacy
route ids.

### 9. Collapse `task_intent_mode=custom` Into `intent=open-ended`

Severity: P1

Entropy source: open-ended is now a launch intent, but the runtime still
threads a cleanup-specific custom-mode flag through just routing, MCP server,
prompt rendering, artifacts, and tests.

Materiality: live source drift, real workflow friction, recurring rediscovery.

Why now: the open-ended proof-status fix made terminal outcome intent-aware,
but the compatibility layer still makes future agents reason about open-ended
work through cleanup-mode language.

Impact radius: workflow.

Maintainer test: This prevents open-ended household runs from being reasoned
about through a cleanup-specific custom-mode flag after open-ended became a
launch intent.

Affected paths:

- `just/agent.just`
- `just/molmo.just`
- `roboclaws/household/task_intent.py`
- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/agents/prompts/household_cleanup.py`
- `roboclaws/launch/evaluation.py`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `tests/contract/molmo_cleanup/`
- `tests/unit/agents/test_live_runtime.py`
- `tests/unit/operator_console/`

Owner skill: intuitive-refactor.

Zen hint: a first-class intent should not require a boolean-like compatibility
mode to explain itself.

Pattern hint: State naming cleanup; no new abstraction needed unless artifacts
need a tiny intent-status helper.

Suggested proof:

```bash
rg -n -F -e 'task_intent_mode' -e 'custom_task' -e 'TASK_INTENT_MODE_CUSTOM' -- \
  just roboclaws tests docs
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/unit/agents/test_live_runtime.py \
  tests/unit/operator_console
```

Execution risk: accepted direction is to remove `task_intent_mode=custom` from
new open-ended runtime/artifact semantics. Historical readers may tolerate it,
but cleanup intent must remain terminally cleanup-scored.

## Suggested Execution Grouping

The selected candidates can be implemented independently, but the least
surprising order is:

1. Map and semantic-source contract:
   - Candidate 1: Base Navigation Map / Runtime Metric Map collapse.
   - Candidate 7: fixture-hints guidance collapse.
2. Launch and evidence surface cleanup:
   - Candidate 2: evidence lane / camera labeler / smoke cleanup.
   - Candidate 3: legacy task route removal.
3. Open-ended intent cleanup:
   - Candidate 5: open-ended status authority invariant/regression guard.
   - Candidate 9: remove `task_intent_mode=custom`.
4. Operator console route identity cleanup:
   - Candidate 8: legacy route wrappers.
5. Meta surfaces after contract changes:
   - Candidate 4: `STATUS.md` and plan index.
   - Candidate 6: Agent Validation Matrix axis sync.

Do not treat this order as approval to implement all candidates in one commit.
Each group should keep its own diff and proof.

## Parked Observations

- `visual_grounding` remains legitimate inside the External Visual Grounding
  Service, benchmark scripts, and provider-specific provenance. Only public
  task-axis use should collapse into `camera_labeler`.
- `cleanup_profile` may remain in historical artifacts and report readers until
  the evidence-lane slice decides the new artifact compatibility policy.
- OpenClaw `tools.profile=minimal|coding|messaging` is a different Gateway
  concept and is not part of household evidence-lane cleanup.
- `output/` and `tmp/` were not selected as cleanup candidates because they are
  untracked local artifacts and no current friction was found in this loop.
- Historical `docs/plans/` entries should be superseded or indexed clearly, not
  rewritten as if they were current implementation instructions.

## Saturation Stop Condition

This discovery loop is saturated when:

- no current public docs, active skills, launch catalog, prompts, or tests
  expose `rich`/`minimal` as a product map choice;
- no current command or route treats `smoke` as an `evidence_lane`;
- no current public route relies on `profile`, `cleanup_profile`,
  `visual_grounding`, `task::run`, `household-cleanup`, or
  `semantic-map-build` as the canonical operator shape;
- operator console launch identity is canonical selection id only, with old
  route ids limited to read-only historical display if still needed;
- open-ended household runs use `intent=open-ended` directly, not
  `task_intent_mode=custom`;
- Agent Validation Matrix selects gates from the surviving axes;
- `STATUS.md` and `docs/plans/README.md` point future agents at the current
  source of truth without forcing rediscovery.

After the final targeted probe in this loop, additional observations were
supporting evidence for these selected candidates or historical/local surfaces.
No extra standalone P0/P1 or materially useful P2 candidate was selected.

## Execution Log

### 2026-06-11 Partial Route/Console Cleanup Proof

Status remains `CONTINUE`.

Current tree state now overlaps this plan with
`docs/plans/refactor-retire-ai2thor-vlm-direct.md`: the worktree contains a
large AI2-THOR/direct-VLM retirement diff plus the household launch/open-ended
cleanup. The household plan is not complete yet because active first-read and
human docs still advertise retired AI2-THOR/direct coding-agent routes, and the
map/evidence/open-ended groups still have unchecked saturation items.

Verified this slice:

```bash
uv sync --extra dev
just --summary
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Observed proof:

- `just --summary` exposes only `run::surface`, `console::run`, and
  maintainer `agent::*` facades.
- Operator-console route tests pass with canonical household selection IDs and
  no AI2-THOR worlds.
- Dev-tool route tests pass with `surface=ai2thor-world` and
  `agent_engine=vlm-policy` rejected, while household route resolution remains
  green.

Remaining before this plan can be marked done:

- reconcile active docs (`README.md`, `ARCHITECTURE.md`, `AGENTS.md`,
  `CLAUDE.md`, `just/README.md`, and selected `docs/human/**`) with the
  surviving launch axes;
- finish or explicitly split the AI2-THOR/direct-VLM retirement plan, including
  full doc, CI, lockfile, skill, and test cleanup;
- complete the still-open map-mode/fixture-hints, evidence-lane/smoke,
  `task_intent_mode=custom`, Agent Validation Matrix, `STATUS.md`, and
  `docs/plans/README.md` saturation checks.

Commit closeout is intentionally deferred: the tree contains broad staged
deletions from the AI2-THOR retirement plan and several unstaged follow-up
edits, so a semantic commit for only this household route/console proof would
be unsafe without first separating or finishing the retirement slice.

### 2026-06-11 First-Read And Current Command Doc Alignment

Status remains `CONTINUE`.

Aligned the current first-read and command docs with the surviving public
catalog:

- `README.md`
- `ARCHITECTURE.md`
- `STATUS.md`
- `AGENTS.md`
- `CLAUDE.md`
- `just/README.md`
- `docs/human/contributing.md`
- `docs/human/mcp-skills-and-semantic-profiles.md`
- `docs/human/ut_ci_design.md`
- `docs/plans/README.md`

Focused behavior/test cleanup:

- adjusted the retired `ai2thor-nav` negative-route assertion to match the
  current resolver error;
- adjusted the operator-console mess-up preview test to assert the API's
  non-blocking route message, while the UI still owns the "baseline remains
  available" wording.

Verified this slice:

```bash
just --summary
rg -n -F \
  -e 'surface=ai2thor-world' -e 'surface=ai2thor-games' \
  -e 'backend=ai2thor' -e 'agent_engine=vlm-policy' \
  -e 'evidence_lane=smoke' -e 'map_mode=minimal' \
  -e 'map_mode=rich' -e 'mode=smoke' -- \
  README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md \
  just/README.md docs/human docs/plans/README.md
git diff --check -- \
  README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md \
  just/README.md docs/human/contributing.md \
  docs/human/mcp-skills-and-semantic-profiles.md \
  docs/human/ut_ci_design.md docs/plans/README.md \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/unit/operator_console/test_messup.py \
  docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/operator_console \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Observed proof:

- `just --summary` exposes only `run::surface`, `console::run`, and
  maintainer `agent::*` facades.
- The current first-read and selected human command docs no longer advertise
  retired AI2-THOR/direct-VLM public axes, `evidence_lane=smoke`, or
  `minimal`/`rich` as product map choices.
- Focused route and operator-console tests pass.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff,
  including remaining CI, lockfile, skill, report, and historical-doc cleanup;
- finish the code-level evidence-lane cleanup where `smoke` is still accepted
  as a private profile/evidence-mode compatibility value;
- finish the map-mode / `fixture_hints`, `task_intent_mode=custom`, Agent
  Validation Matrix, and remaining historical/human-doc profile terminology
  saturation checks.

### 2026-06-11 Open-Ended Intent Runtime Cleanup

Status remains `CONTINUE`.

Implemented Candidate 9's current-runtime slice:

- added canonical household-intent normalization around `intent=open-ended`;
- stopped `just agent::run` from auto-generating `task_intent_mode=custom` for
  open-ended launches;
- exported `ROBOCLAWS_TASK_INTENT` from private lowerer to `molmo::cleanup` so
  prompt, MCP setup, and checker filtering share the resolved first-class
  intent;
- made kickoff prompts, MCP setup text, MCP done readiness, deterministic MCP
  smoke, and live runner checker gates use `task_intent=open-ended` /
  `goal_contract.intent=open-ended` first;
- stopped new MCP `run_result.json` artifacts from writing
  `task_intent_mode`;
- kept `task_intent_mode=custom` only as a tolerated legacy/manual input and
  timing/history field while tests assert new artifacts use `task_intent`.

Verified this slice:

```bash
rg -n -F -e 'task_intent_mode' -e 'custom_task' -e 'TASK_INTENT_MODE_CUSTOM' -- just roboclaws tests docs
git diff --check -- \
  just/agent.just just/molmo.just \
  roboclaws/household/task_intent.py \
  roboclaws/agents/prompts/household_cleanup.py \
  roboclaws/household/realworld_contract.py \
  roboclaws/household/realworld_mcp_server.py \
  roboclaws/cli/household_agent_server.py \
  scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py \
  scripts/molmo_cleanup/run_live_codex_cleanup.py \
  scripts/molmo_cleanup/run_live_claude_cleanup.py \
  scripts/molmo_cleanup/run_live_openai_agents_cleanup.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/unit/agents/test_live_runtime.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/unit/agents/test_live_runtime.py \
  tests/unit/operator_console
```

Observed proof:

- open-ended prompt routing now keeps `task_intent_mode=default_cleanup` while
  carrying the first-class `task_intent=open-ended` and goal contract;
- open-ended MCP run results contain `task_intent=open-ended` and no
  `task_intent_mode` field;
- live runner checker gates drop cleanup-only success/sweep/count requirements
  when `ROBOCLAWS_TASK_INTENT=open-ended` is present;
- remaining current-code `task_intent_mode` references are compatibility input
  plumbing, prompt CLI arguments, operator-console history/state fields,
  readiness diagnostics, or live timing metadata.

Remaining before this plan can be marked done:

- finish the map-mode / `fixture_hints` active MCP and prompt cleanup;
- finish the evidence-lane/smoke cleanup where `smoke` remains a private
  compatibility profile/preset;
- align Agent Validation Matrix gate selection with the surviving axes;
- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff.

### 2026-06-11 Agent Validation Matrix Axis Sync

Status remains `CONTINUE`.

Implemented Candidate 6's focused matrix slice:

- added first-class `open_ended` signal detection for `open-ended`,
  `goal_contract`, `task_intent`, completion-claim, and agent-declared terms;
- added an `intent` explicit override to the selector and runner CLIs;
- added a deterministic `open-ended-household-contract-tests` gate covering
  route inference, MCP open-ended artifact shape, and checker acceptance;
- kept product gates on current public axes (`surface=household-world`,
  `intent=cleanup|map-build`, `agent_engine`, `provider_profile`,
  `evidence_lane`, `camera_labeler`) rather than stale task/profile names;
- classified live MCP port and MolmoSpaces visual-backend slot contention as
  blocked resource conditions instead of false test failures.

Verified this slice:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_agent_validation_matrix.py
just agent::harness agent-validation recommend \
  plan=docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md \
  budget=focused
just agent::harness agent-validation execute \
  plan=docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md \
  budget=focused
```

Observed proof:

- recommendation artifact:
  `output/agent-validation-matrix/20260611T100425Z/validation_matrix.json`;
- execute artifact:
  `output/agent-validation-matrix/20260611T102524Z/validation_matrix.json`;
- deterministic selected gates passed, including
  `open-ended-household-contract-tests`;
- selected live/DINO gates were environment-blocked by active live-session /
  visual-backend slot ownership or unavailable Grounding DINO sidecar, not by
  stale axis selection.

Remaining before this plan can be marked done:

- finish the map-mode / `fixture_hints` active MCP and prompt cleanup;
- finish the evidence-lane/smoke cleanup where `smoke` remains a private
  compatibility profile/preset;
- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff.

### 2026-06-11 Evidence-Lane And Smoke Cleanup

Status remains `CONTINUE`.

Implemented Candidate 2's public-route slice:

- made public `run::surface` reject `profile=...`, `visual_grounding=...`, and
  `evidence_lane=smoke`;
- kept `smoke` as a private runner compatibility mode while new public smoke
  examples use `run_preset=smoke` with a real evidence lane;
- preserved `evidence_lane=world-oracle-labels` as the deterministic household
  cleanup smoke lane.

Verified this slice:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/unit/agents/test_live_runtime.py \
  tests/unit/operator_console \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py
```

Observed proof:

- public route contract tests cover rejection of stale `profile`,
  `visual_grounding`, and `evidence_lane=smoke` inputs;
- the broad household launch/MCP/checker/operator-console verifier passes with
  the current evidence-lane shape;
- lower runner compatibility still accepts private smoke profile semantics
  where required by deterministic smoke helpers.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 1 and Candidate 3 saturation around public map-mode and
  legacy task-route terminology;
- finish Candidate 8 operator-console legacy route wrapper cleanup or prove it
  already collapsed to read-only history only.

### 2026-06-11 Rerun Command Surface Cleanup

Status remains `CONTINUE`.

Implemented a narrow Candidate 3 / Candidate 1 saturation slice:

- removed `map_mode=minimal` from current copyable `run::surface` rerun-command
  fixtures in MCP and report tests;
- updated the semantic map-build prompt helper docstring from
  `semantic-map-build lane` to `intent=map-build`;
- kept historical artifact paths, private server ids, and negative route tests
  unchanged.

Verified this slice:

```bash
rg -n -F -e 'map_mode=minimal' -e 'map_mode=rich' -- \
  README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md just/README.md \
  docs/human docs/plans skills just roboclaws tests scripts .github
rg -n -F -e 'semantic-map-build lane' -e 'household-cleanup lane' \
  -e 'This run is semantic-map-build' -e 'This run is household-cleanup' -- \
  README.md ARCHITECTURE.md STATUS.md docs/human skills roboclaws tests scripts just
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_done_persists_facade_rerun_command \
  tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_persists_facade_rerun_command \
  tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_prefers_recorded_rerun_command
uv run ruff check roboclaws/agents/prompts/household_cleanup.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py \
  tests/contract/reports/test_molmo_cleanup_report.py
git diff --check -- \
  roboclaws/agents/prompts/household_cleanup.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py \
  tests/contract/reports/test_molmo_cleanup_report.py \
  docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md
```

Observed proof:

- active generated rerun-command fixtures no longer include public
  `map_mode=minimal`;
- active prompt helper wording no longer describes map-build as a
  `semantic-map-build lane`;
- remaining `map_mode=minimal`, `household-cleanup`, and `semantic-map-build`
  hits are historical plans, private lowerer/server ids, artifact paths,
  compatibility tests, or negative public-route assertions.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 3 private-dispatch terminology audit where it still points
  future agents at legacy task names;
- finish Candidate 8 operator-console legacy route wrapper cleanup or prove it
  already collapsed to read-only history only.

### 2026-06-11 Active Skill Public Run Command Guard

Status remains `CONTINUE`.

Implemented a narrow Candidate 3 active-skill slice:

- changed the active Actionable Semantic Map Conversion skill from online
  `semantic-map-build` / `just task::run household-cleanup` wording to
  `intent=map-build` and the canonical `just run::surface ... intent=cleanup`
  downstream consumer example;
- added a tracked-skill contract guard so active skills do not teach retired
  `just task::run` commands.

Verified this slice:

```bash
rg -n -F 'just task::run' -- \
  README.md ARCHITECTURE.md docs/human skills just roboclaws tests scripts .github
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/skills/test_skill_manifests.py
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=agibot-g2/map-12 backend=agibot-gdk \
  intent=cleanup agent_engine=direct-runner evidence_lane=world-oracle-labels \
  seed=7 \
  runtime_map_prior=output/maps/robot_map_12/actionable_semantic_map_snapshot.json
```

Observed proof:

- the only remaining `just task::run` grep hit is historical implementation
  result text in `docs/human/molmospaces-cleanup-mode-architecture.md`;
- active tracked skills now reject retired `just task::run` examples in the
  contract suite;
- the replacement downstream command lowers through the public launch catalog
  in trace mode.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 3 private-dispatch terminology audit where lower
  implementation ids remain private and do not point users at legacy public
  commands;
- finish Candidate 8 operator-console legacy route wrapper cleanup or prove it
  already collapsed to read-only history only.

### 2026-06-11 Candidate 1 Minimal-Only Contract Saturation

Status remains `CONTINUE`.

Implemented Candidate 1's lower-contract saturation slice:

- removed the active `RICH_MAP_MODE` constant and left `REALWORLD_MAP_MODES`
  as minimal-only private compatibility;
- made private `molmo::cleanup map_mode=...` validation accept only `minimal`;
- migrated contract, checker, map-bundle, MCP, planner-binding, and cleanup
  skill tests from rich static fixture expectations to Base Navigation Map plus
  runtime public anchors;
- let deterministic direct cleanup re-evaluate same-anchor observations after
  visual confirmation and current worklist evidence so it can use discovered
  runtime anchors instead of stale first-sighting hints;
- kept planner-proof bindings strict while updating tests to bind cleanup
  proofs to public `anchor_fixture_*` target ids;
- updated active cleanup prompts, RAW-FPV recovery guidance, and the cleanup
  skill so agents are instructed in Base Navigation Map terms rather than
  `minimal map mode` terms;
- ran the final human-doc alignment check and updated README / human cleanup
  architecture wording from minimal-map / `map_mode` behavior to Base
  Navigation Map plus optional `runtime_map_prior` evidence.

Verified this slice:

```bash
uv sync --extra dev
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/maps/test_nav2_map_bundle_contract.py \
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py \
  tests/unit/molmo_cleanup/test_molmo_planner_observed_binding.py
uv run ruff check \
  roboclaws/agents/prompts/household_cleanup.py \
  roboclaws/household/raw_fpv_guidance.py \
  roboclaws/household/realworld_contract.py \
  roboclaws/household/realworld_cleanup.py \
  roboclaws/cli/household_agent_server.py \
  roboclaws/maps/bundle.py \
  skills/molmo-realworld-cleanup/SKILL.md \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py \
  tests/contract/maps/test_nav2_map_bundle_contract.py \
  tests/unit/molmo_cleanup/test_molmo_planner_observed_binding.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py::test_molmo_camera_raw_prompt_requires_exact_waypoint_checklist \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_minimal_raw_fpv_navigate_validation_returns_schema_recovery
rg -n -F -e 'RICH_MAP_MODE' -e 'map_mode=RICH_MAP_MODE' \
  -e 'rich is' -e 'expected rich|minimal' -- \
  roboclaws tests scripts skills docs/human docs/plans just
```

Observed proof:

- the focused household map-mode/checker/MCP suite passes with the
  Base Navigation Map contract;
- active production code and tests have no `RICH_MAP_MODE` or
  `expected rich|minimal` hits;
- remaining grep hits are plan-history references documenting this cleanup.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 3 generated rerun/private-dispatch terminology where it
  still points future agents at legacy task names;
- finish Candidate 8 operator-console legacy route wrapper cleanup or prove it
  already collapsed to read-only history only.

### 2026-06-11 Public Map Mode Facade Rejection

Status remains `CONTINUE`.

Implemented Candidate 1's public-facade slice:

- made public `run::surface` reject `map_mode=...` with Base Navigation Map /
  `runtime_map_prior=...` guidance;
- made public `agent::run` reject `map_mode=...` before lowering to private
  Molmo cleanup recipes;
- flipped route contract tests that previously asserted `map_mode=minimal` and
  `map_mode=rich` were accepted through public task-shaped calls;
- kept lower `molmo::cleanup` map-mode plumbing as private compatibility for
  historical/internal callers in this bounded slice.

Verified this slice:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Observed proof:

- public route resolution rejects `map_mode=minimal` and `map_mode=rich`;
- `agent::run household-world.cleanup ... map_mode=minimal` is rejected before
  private dispatch;
- the focused cleanup/MCP/checker contracts still pass with the private
  default map behavior.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 1 saturation around lower private `map_mode` plumbing,
  `RICH_MAP_MODE`, and stale plan/docs/tests that still treat `rich` or
  `minimal` as active map choices;
- finish Candidate 3 saturation around legacy task-route terminology.

### 2026-06-11 Maintainer MCP Facade Dispatch Targets

Status remains `CONTINUE`.

Implemented Candidate 3's maintainer-MCP slice:

- made `just agent::mcp up` accept canonical dispatch targets
  `household-world.cleanup` and `household-world.map-build`;
- kept `mcp::up household-cleanup|semantic-map-build` as the private lower
  helper behind the maintainer facade;
- updated current human debugging docs to use `agent::mcp` with canonical
  dispatch targets instead of direct `mcp::up` examples.

Verified this slice:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
ROBOCLAWS_JUST_TRACE=1 just agent::mcp up \
  household-world.cleanup 127.0.0.1 18788 output/debug/household-mcp
ROBOCLAWS_JUST_TRACE=1 just agent::mcp up \
  household-world.map-build 127.0.0.1 18788 output/debug/map-build-mcp
rg -n -F -e 'just mcp::up' -e 'task::run' -e 'household-cleanup' \
  -e 'semantic-map-build' -- \
  README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md just/README.md \
  docs/human skills/molmo-realworld-cleanup roboclaws/launch \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Observed proof:

- canonical `agent::mcp` targets lower to the existing private server ids in
  trace mode;
- current human docs no longer recommend direct `just mcp::up ...` commands;
- remaining `household-cleanup` / `semantic-map-build` hits are private
  implementation ids, artifact paths, active skill wording, historical docs,
  or tests asserting the private lowering.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 1 saturation around lower private `map_mode` plumbing,
  `RICH_MAP_MODE`, and stale plan/docs/tests that still treat `rich` or
  `minimal` as active map choices;
- finish Candidate 3 active skill wording and generated rerun/private-dispatch
  terminology where it still points future agents at legacy task names.

### 2026-06-11 Active Cleanup Skill Intent Wording

Status remains `CONTINUE`.

Implemented Candidate 3's active-skill wording slice:

- changed the mounted cleanup skill instructions from `semantic-map-build` task
  wording to `intent=map-build`;
- changed the skill manifest capability note from `household-cleanup` /
  `semantic-map-build` task IDs to `intent=cleanup` / `intent=map-build`.

Verified this slice:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
rg -n -F -e 'semantic-map-build' -e 'household-cleanup' -e 'task::run' -- \
  skills/molmo-realworld-cleanup
```

Observed proof:

- the active `molmo-realworld-cleanup` skill no longer contains
  `semantic-map-build`, `household-cleanup`, or `task::run` wording;
- skill and route contracts pass with the intent-based wording.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 1 saturation around lower private `map_mode` plumbing,
  `RICH_MAP_MODE`, and stale plan/docs/tests that still treat `rich` or
  `minimal` as active map choices;
- finish Candidate 3 generated rerun/private-dispatch terminology where it
  still points future agents at legacy task names.

### 2026-06-11 Agent Prompt Surface/Intent Headlines

Status remains `CONTINUE`.

Implemented Candidate 3's agent-facing prompt slice:

- changed cleanup kickoff prompt text from `This run is household-cleanup` to
  `This run is surface=household-world intent=cleanup`;
- changed map-build kickoff prompt text from `This run is semantic-map-build`
  to `This run is surface=household-world intent=map-build`;
- kept the cleanup-disabling instruction for map-build as plain behavior
  wording instead of naming the old cleanup task id in the prompt headline.

Verified this slice:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
rg -n -F -e 'This run is household-cleanup' \
  -e 'This run is semantic-map-build' -- roboclaws tests skills docs README.md \
  ARCHITECTURE.md just
```

Observed proof:

- route/prompt contracts pass;
- the old agent-facing prompt headlines no longer appear in current code,
  tests, docs, or skills.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 1 saturation around lower private `map_mode` plumbing,
  `RICH_MAP_MODE`, and stale plan/docs/tests that still treat `rich` or
  `minimal` as active map choices;
- finish Candidate 3 generated rerun/private-dispatch terminology where it
  still points future agents at legacy task names.

### 2026-06-11 Operator Console Legacy Route Launch Boundary

Status remains `CONTINUE`.

Implemented Candidate 8's public launch-boundary slice:

- stopped `get_selection()` from resolving legacy route ids such as
  `codex-mujoco-cleanup`;
- stopped `LaunchRequest(route_id=...)` and `/api/runs` from treating legacy
  route ids as runnable launch identity;
- carried canonical `selection_id` through legacy route payloads, history
  attachment, attachable-run payloads, and next-goal auto-start so old artifacts
  can remain displayable while new launches use canonical selection ids;
- kept `ConsoleRoute`, `get_route()`, and `legacy_route_id` only for historical
  display/test fixtures and old state parsing.

Verified this slice:

```bash
rg -n -F -e 'get_route(' -e 'list_console_routes' -e 'ConsoleRoute' \
  -e 'legacy_route_id' -e 'codex-mujoco-cleanup' -- \
  roboclaws/operator_console tests/unit/operator_console
git diff --check -- \
  roboclaws/operator_console/routes.py \
  roboclaws/operator_console/launcher.py \
  roboclaws/operator_console/server.py \
  roboclaws/operator_console/history.py \
  roboclaws/operator_console/interactions.py \
  tests/unit/operator_console/test_routes.py \
  tests/unit/operator_console/test_launcher.py \
  tests/unit/operator_console/test_operator_console.py
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
```

Observed proof:

- `get_selection("codex-mujoco-cleanup")` is rejected;
- direct and HTTP launch attempts using only `route_id=codex-mujoco-cleanup`
  are rejected as display-only legacy identity;
- terminal next-goal auto-start uses the canonical selection id while preserving
  the open-ended intent override;
- remaining legacy route references are historical display wrappers, state
  derivation fixtures, or explicit negative tests.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 1 and Candidate 3 saturation around public map-mode and
  legacy task-route terminology.

### 2026-06-11 Operator Console Reload Selection Boundary

Status remains `CONTINUE`.

Implemented Candidate 8's reload-boundary cleanup:

- changed browser polling from `/api/runs/<run_id>?route=...` to
  `/api/runs/<run_id>?selection_id=...`;
- changed the reload handler to resolve only canonical selection ids with
  `get_selection()`, so `?route=codex-mujoco-cleanup` can no longer inject a
  legacy route wrapper into current run state;
- widened state normalization to accept canonical `ConsoleLaunchSelection`
  payloads directly while preserving historical `ConsoleRoute` display records.

Verified this slice:

```bash
rg -n -F '?route=' -- roboclaws/operator_console tests/unit/operator_console
git diff --check -- \
  roboclaws/operator_console/server.py \
  roboclaws/operator_console/state.py \
  roboclaws/operator_console/static/app.js \
  tests/unit/operator_console/test_operator_console.py \
  tests/unit/operator_console/test_static_assets.py \
  docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md
uv run ruff check \
  roboclaws/operator_console/server.py \
  roboclaws/operator_console/state.py \
  tests/unit/operator_console/test_operator_console.py \
  tests/unit/operator_console/test_static_assets.py
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
```

Observed proof:

- legacy `?route=` remains only in the explicit negative reload test and static
  asset guard;
- `GET /api/runs/<id>?route=codex-mujoco-cleanup` now leaves a route-less run
  route-less instead of using a legacy wrapper;
- operator-console unit tests pass with the canonical `selection_id` reload
  query.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 3 private-dispatch terminology audit where lower
  implementation ids remain private and do not point users at legacy public
  commands.

### 2026-06-11 Runtime Metric Map Guidance And Active MCP Cleanup

Status remains `CONTINUE`.

Implemented Candidate 7's active-surface slice:

- removed `fixture_hints` from the active household cleanup MCP tool
  registration, handler table, public tool names, and current MCP profile
  metadata;
- updated household prompts, raw-FPV guidance, skill instructions, setup text,
  and deterministic MCP smoke flow to start from `metric_map`,
  `runtime_metric_map`, and `resolve_target_query`;
- added/kept regression coverage that active MCP rejects `fixture_hints` while
  internal contract/report readers may still understand historical
  `fixture_hints` artifacts;
- updated the cleanup checker so a clean active agent run no longer requires a
  `fixture_hints` MCP request.

Verified this slice:

```bash
rg -n -F -e 'fixture_hints' -e 'metric_map' -e 'resolve_target_query' -- \
  skills roboclaws/agents/prompts roboclaws/household docs/human tests
git diff --check -- \
  roboclaws/agents/prompts/household_cleanup.py \
  roboclaws/household/raw_fpv_guidance.py \
  roboclaws/household/realworld_contract.py \
  roboclaws/household/realworld_mcp_semantic_tools.py \
  roboclaws/household/realworld_mcp_server.py \
  roboclaws/mcp/profiles.py \
  scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py \
  scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  skills/molmo-realworld-cleanup/SKILL.md \
  skills/molmo-realworld-cleanup/skill.json \
  docs/human/mcp-skills-and-semantic-profiles.md \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/unit/agents/test_live_runtime.py \
  tests/unit/operator_console \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py
```

Observed proof:

- the active household MCP server rejects `fixture_hints` and no longer records
  `fixture_hints:request` in deterministic smoke output;
- active prompts and the cleanup skill instruct agents to use `metric_map`,
  runtime map anchors, and `resolve_target_query` instead of a
  fixture-hints-first flow;
- remaining `fixture_hints` references in the proof grep are historical report
  fixtures, Agibot/map-context compatibility paths, internal contract helpers,
  or explicit active-MCP rejection assertions.

Remaining before this plan can be marked done:

- finish or explicitly split the broader AI2-THOR/direct-VLM retirement diff;
- finish Candidate 1 and Candidate 3 saturation around public map-mode and
  legacy task-route terminology;
- finish Candidate 8 operator-console legacy route wrapper cleanup or prove it
  already collapsed to read-only history only.
