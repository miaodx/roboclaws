<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0514-autoplan-restore-20260514-210504.md -->

# Generic MCP Entrypoint And Semantic Capabilities

**Status:** Reviewed source plan
**Created:** 2026-05-13
**Autoplan review:** Approved 2026-05-14; decisions reconciled in this file.
**Source:** open-ended robot task architecture discussion and `CONTEXT.md`
vocabulary alignment
**Workflow:** Pre-GSD plan. Ingest into `.planning/` before implementation.

## Problem

Roboclaws currently has useful embodied demos, but the architecture is drifting
toward named tasks and backend-specific privileged helpers instead of the original goal:
give the robot an open-ended task prompt and let an agent solve it with a small,
composable set of robot abilities.

The current surfaces are not wrong, but they mix abstraction levels:

- AI2-THOR navigation exposes `observe`, `move`, `scene_objects`, `goto`, and
  `done`.
- The photo task depends on `scene_objects` and `goto`, which are effective
  privileged AI2-THOR helpers but not real robot capabilities.
- MolmoSpaces cleanup exposes a stricter ADR-0003 public contract with metric
  map, fixture hints, observed handles, pick/place tools, private scoring
  separation, and planner-proof evidence.
- `just task::run ...` is a demo recipe facade, but the word "task" can be
  confused with the user's open-ended robot work.

The desired shape is cleaner: task prompts remain open-ended, agents plan, MCP
exposes semantic capabilities and bounded semantic services, and each
environment backs those capabilities with its own primitives.

## Goal

Design a generic MCP entrypoint/router that loads backend-specific contract
profiles while preserving a shared semantic capability model.

The target model:

- One generic MCP entrypoint or router can expose one selected contract profile
  to an agent.
- Contract profiles remain backend/domain-specific, such as
  `ai2thor_navigation_v1`, `molmospaces_cleanup_v1`, and future
  `real_robot_cleanup_v1`.
- Profiles declare supported capability families:
  perception, localization, mapping, navigation, manipulation, and memory.
- Agent-facing tools live at the semantic capability or selected semantic
  service layer.
- Environment primitives remain behind adapters.
- Reusable task behavior lives in agent skills. Composite actions are described
  by their traceable substeps, while privileged tools stay outside the
  canonical contract.

## Decisions Resolved

- A user instruction such as "clean the room" is a **Task Prompt**, not a
  single MCP tool.
- MCP should expose **Semantic Capabilities** and selected **Semantic Services**,
  not raw **Environment Primitives**.
- Open-ended task planning belongs to the agent. Services solve bounded
  subproblems such as localization, route planning, semantic map query, object
  association, grasp feasibility, and memory retrieval.
- Roboclaws should move toward one generic **MCP Entrypoint**, not one premature
  universal MCP tool set.
- Contract profiles should combine environment and task domain when both matter:
  `ai2thor_navigation_v1`, `molmospaces_cleanup_v1`, and later
  `real_robot_cleanup_v1`.
- `scene_objects` and teleport-like `goto` are privileged tools unless
  redesigned as decomposed semantic services.
- Deterministic cleanup policies and proof-bundle selection are baselines or
  private evidence helpers, not the target open-ended agent capability.

## Proposed Architecture

### Layer 1: Environment Primitives

Backend-specific implementations of robot or simulator operations:

- AI2-THOR controller actions and simulator metadata.
- MuJoCo/MolmoSpaces state transitions, robot views, and planner probes.
- Future real robot ROS/Nav2/actions, perception nodes, and manipulation
  backends.

These should not be the default public MCP boundary.

### Layer 2: Semantic Capabilities

Agent-facing robot abilities with stable meaning across profiles where
possible:

- `perception.observe`
- `localization.get_pose`
- `mapping.query`
- `navigation.navigate_to`
- `manipulation.inspect`
- `manipulation.pick`
- `manipulation.place`
- `memory.retrieve`
- `episode.done`

Each profile may implement only a subset. Every response should carry honest
provenance such as `api_semantic`, `sim_planner`, `nav2_action`,
`planner_backed`, or `blocked_capability`.

### Layer 3: Semantic Services

Bounded reusable algorithms that can support capabilities:

- localization;
- route planning;
- semantic map lookup;
- object-handle association;
- grasp feasibility;
- memory retrieval;
- recovery suggestions.

Semantic services may be exposed directly when they are useful for planning,
but they should not hide a whole user task behind an opaque tool.

### Layer 4: Agent Skills, Composite Actions, And Privileged Tools

Convenience operations must be classified:

- **Canonical:** safe semantic capability in an open-ended contract.
- **Composed:** higher-level behavior allowed when it records or preserves a
  decomposition trace.
- **Privileged tool:** demo/debug/smoke/proof helper, excluded from canonical
  agent-facing contracts.

Initial classification:

- `observe`: Canonical. Implementations vary by profile.
- `move`: Profile-specific canonical tool or environment primitive. Appropriate
  for low-level navigation profiles, but not the only real-robot interface.
- `scene_objects`: Privileged tool. Useful AI2-THOR inventory helper; not a
  real robot perception surface.
- Current AI2-THOR `goto`: Privileged tool. Teleport-like; not
  route-planning-backed today.
- Future `navigate_to`: Canonical or composed. Should expose
  localization/navigation provenance.
- `pick` / `place`: Canonical. Must report manipulation provenance.
- Deterministic cleanup policy: baseline skill/script behavior. Useful for
  reports and regressions, not target autonomy.
- Proof-bundle runner/selection: private evidence helper. Supports proof claims;
  not public agent input.

## Research Spike

Before implementation, run a focused research/design spike that compares this
model against:

- ROS 2/Nav2 navigation action and map concepts;
- common robot policy interfaces for open-ended task execution;
- Habitat/PARTNR-style embodied task abstractions;
- MolmoSpaces/RBY1M/CuRobo proof boundaries already used in this repo;
- MCP tool registration and profile-routing patterns.

Research output should be implementation-ready:

- recommended profile declaration schema;
- recommended tool naming and namespacing pattern;
- required provenance fields;
- privileged-tool classification rules;
- risks where real robot conventions conflict with simulator convenience.

Use primary sources or local docs for external claims. Do not turn this into a
large literature survey; the output should directly shape the Roboclaws API.

## Implementation Sketch

1. Add a profile declaration model, likely under `roboclaws/mcp/` or a new
   neutral capability module.
2. Define capability family names, canonical semantic tool descriptors, and
   provenance vocabulary in one place.
3. Add adapters that describe the existing AI2-THOR and MolmoSpaces contracts
   without merging their server implementations immediately.
4. Add a generic MCP entrypoint/router that loads a selected contract profile
   and registers that profile's tools.
5. Mark existing privileged tools in docs and profile metadata.
6. Add tests that prove canonical profiles do not expose private scoring truth
   or simulator-only privileged tools by default.
7. Update agent-facing skills so prompts describe task prompts, semantic
   capabilities, and privileged-tool boundaries consistently.

## Non-Goals

- Do not build one universal MCP tool set that every environment must implement.
- Do not remove existing AI2-THOR or MolmoSpaces servers before the router is
  proven.
- Do not claim real robot readiness from simulator-only privileged helpers.
- Do not expose Molmo private scoring truth, generated mess sets, acceptable
  destination sets, or hidden target lists.
- Do not implement live ROS/Nav2 or manipulation backends in this phase.
- Do not make `cleanup_room()` or similar whole-task MCP tools the default
  open-ended agent contract.

## Acceptance Criteria

- The repo has a documented semantic capability model aligned with
  `CONTEXT.md`.
- Existing AI2-THOR and MolmoSpaces contracts can be represented as contract
  profiles.
- The generic MCP entrypoint/router can load at least one profile in tests.
- Profiles declare capability families, public tools, provenance expectations,
  and privileged-tool exclusions.
- AI2-THOR `scene_objects` and current `goto` are labeled as privileged tools
  and excluded from canonical profile metadata.
- Molmo cleanup profile preserves ADR-0003 public/private boundaries.
- Tests fail if canonical profiles expose private evaluator data or privileged
  tools unintentionally.
- Existing demo recipes continue to run through their current commands.

## Verification Plan

- Unit tests for profile declaration parsing and validation.
- Contract tests for AI2-THOR and MolmoSpaces profile metadata.
- MCP registration tests for the generic entrypoint/router using a mock profile.
- Leak tests proving Molmo private scoring truth is absent from public profile
  declarations.
- Privileged-tool classification tests proving privileged tools are opt-in or
  excluded from canonical agent-facing contracts.
- Focused docs tests or grep checks to keep `task prompt`, `capability tool`,
  `demo recipe`, and `privileged tool` language consistent.
- Existing relevant MCP and cleanup contract tests through the repo-local
  pytest wrapper.

## Autoplan Review Decisions

Review mode: `autoplan` via `intuitive-flow`, single-reviewer degradation.
Codex CLI authenticated but its read-only sandbox could not inspect local files
on this host, and no Claude subagent tool was available, so outside voices were
recorded as unavailable instead of being faked.

Final gate: approved as a soft continuation. The review did not change the
target user, public privacy posture, paid-service dependency, data model, or
phase split. It tightened the plan around already stated acceptance criteria:
metadata-first profiles, a generic router prototype, privileged-tool
exclusions, and fail-closed privacy tests.

### CEO Review

Premises accepted:

- The problem is real: `CONTEXT.md` now separates Open-Ended Goal, Agent Skill,
  Composite Action, Semantic Capability, Privileged Tool, Demo Recipe, Contract
  Profile, MCP Entrypoint, and Capability Family.
- The right wedge is profile metadata plus one router prototype, not a
  universal robot API.
- Existing contracts are useful leverage: AI2-THOR navigation already exposes
  `observe`, `observe_archived`, `move`, `scene_objects`, `goto`, and `done`,
  while MolmoSpaces ADR-0003 exposes metric maps, fixture hints, observed
  handles, navigation, manipulation, and private evaluator separation.

Strategic risks and decisions:

- Keep this as one coherent GSD phase. A separate ROS/Nav2 or real-robot phase
  would change execution ownership and validation requirements.
- Do not make the research spike open ended. It must answer implementation
  questions for profile schema, namespacing, provenance, privileged-tool policy,
  and leak tests.
- Treat "generic MCP entrypoint" as a router that loads one selected contract
  profile. Do not market it as a universal robot control surface.

### Engineering Review

What already exists:

- `roboclaws/mcp/server.py` is the AI2-THOR MCP surface and dispatcher.
- `roboclaws/molmo_cleanup/realworld_mcp_server.py` is the ADR-0003 cleanup MCP
  surface and explicitly rejects `scene_objects`.
- `roboclaws/molmo_cleanup/realworld_contract.py` owns public tool names,
  public/private field exclusions, perception modes, provenance values, and
  agent-view payload generation.
- `roboclaws/molmo_cleanup/profiles.py` already proves the repo has a small
  metadata registry pattern for public cleanup profiles.
- Contract tests already cover AI2-THOR MCP behavior, Molmo public/private
  cleanup boundaries, profile expansion, and report/private-evaluation
  separation.

Recommended implementation shape:

```text
contract profile metadata
  -> backend adapter describes existing tools
  -> generic MCP entrypoint selects exactly one profile
  -> FastMCP registration exposes only profile-public tools
  -> trace/report metadata records capability family + provenance + privileged-tool status
```

The first implementation should define a small typed profile declaration with:

- `profile_id`, `version`, `backend`, and `domain`.
- `capability_families`.
- public tool descriptors with name, family, stability, provenance
  expectations, and whether they are canonical, composed, or privileged.
- `privacy_exclusions` / forbidden field names for serialized public profile
  output.
- optional privileged-tool descriptors that are excluded unless explicitly
  loaded for debug or demo paths.

Error and rescue registry:

| Failure | Required behavior | Test |
| --- | --- | --- |
| Unknown profile id | fail before MCP server registration with actionable message | unit |
| Malformed profile metadata | validation error naming missing field | unit |
| Privileged tool appears in canonical profile | validation/test failure | unit/contract |
| Molmo private field appears in public profile | fail closed using forbidden-key checks | contract |
| Router registers stale tool not in profile | MCP registration test fails | contract |
| Existing demo command bypasses current server accidentally | existing MCP/demo contract tests stay green | contract |

Failure modes registry:

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Thin router becomes a naming wrapper around unrelated tools | high | typed profile schema plus contract tests for both current surfaces |
| `goto` / `scene_objects` look like real robot capabilities | high | privileged-tool classification and canonical-profile exclusion tests |
| Molmo private scoring truth leaks through profile metadata | high | reuse ADR-0003 forbidden-key checks on serialized profiles |
| Research spike becomes a literature survey | medium | require implementation-ready schema and test recommendations only |
| Existing demos break during router introduction | medium | adapter-first implementation, no removal of current servers in this phase |

### Test Review

Test artifact:
`/home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0514-test-plan-generic-mcp-entrypoint-20260514-2112.md`.

Required test diagram:

| Path | Coverage |
| --- | --- |
| Profile declaration parsing/validation | unit |
| AI2-THOR profile metadata and privileged-tool exclusions | contract |
| MolmoSpaces cleanup profile metadata and ADR-0003 exclusions | contract |
| Generic router loads a mock profile and registers only declared tools | contract |
| Privileged-tool opt-in path records explicit privileged-tool provenance | unit/contract |
| Existing AI2-THOR and Molmo MCP tests remain green | regression |

### DX Review

Developer persona: repo maintainer adding or reviewing a new robot contract
profile.

DX decisions:

- Add copy-paste examples for selecting a profile in the generic entrypoint,
  but keep existing `just task::run ...` demo recipes unchanged.
- Make invalid profile and privileged-tool-use errors name the requested profile,
  the allowed profile ids, and the reason the tool is excluded.
- Keep profile names backend/domain-specific, such as `ai2thor_navigation_v1`
  and `molmospaces_cleanup_v1`, so future real robot work does not inherit
  simulator privileged helpers by implication.

TTHW target for maintainers: under 5 minutes to read the profile schema, add a
mock profile, and run the router registration test.

### NOT In Scope

- Real ROS/Nav2, live robot, Docker Gateway, GPU, or VLM validation.
- Removing the current AI2-THOR or MolmoSpaces MCP servers.
- A universal tool set every environment must implement.
- Whole-task MCP tools such as `cleanup_room()`.
- Reclassifying `scene_objects` or current teleport-like `goto` as canonical
  real-robot capabilities without a decomposed service implementation.

### Decision Audit Trail

| Decision | Classification | Outcome | Rationale |
| --- | --- | --- | --- |
| Run `autoplan` before GSD handoff | mechanical | accepted | Plan had no reconciled autoplan evidence. |
| Skip UI/design review | mechanical | accepted | Plan changes MCP contracts and docs, not UI screens/components. |
| Include DX review | mechanical | accepted | MCP entrypoint/profile work is developer-facing. |
| Degrade outside voices | blocker workaround | accepted | Codex sandbox could not inspect local files; no subagent tool was exposed. |
| Keep one phase | soft continuation | accepted | Work is one coherent metadata/router prototype with one acceptance surface. |
| Strengthen fail-closed tests | soft continuation | accepted | This preserves stated privacy and privileged-tool boundaries. |

## ADR Follow-Up

Create an ADR only after the research spike and profile prototype answer the
hard implementation questions. The ADR should record whether this plan
supersedes, narrows, or extends ADR-0004. The likely decision shape is:

"Use one generic MCP entrypoint/router with profile-specific semantic tools,
while keeping backend-specific contract profiles and public/private boundaries."

## Risks

- A generic router could become a thin wrapper around unrelated tools unless
  profile metadata and tests enforce the capability model.
- A universal-looking surface could accidentally make simulator privileged tools
  look like real robot capabilities.
- Too much abstraction could slow the thin-demo repo down. Keep the first phase
  metadata-first and preserve existing runnable demos.
- If semantic services become too powerful, they may hide open-ended planning
  inside tools and weaken the agent autonomy story.

## GSD Handoff

Reviewed handoff state:

- `.planning/` already exists.
- No existing roadmap phase was identified for this exact profile/router scope.
- This plan appears to add roadmap scope, so the likely next step is a GSD
  ingest/merge through a manifest that lists this file as `PRD`, then a single
  `gsd-plan-phase <created-or-updated-phase> --prd ...` execution plan.
- Do not manually copy this file into `.planning/phases/*/CONTEXT.md`.

Preferred command after the GSD phase decision:

```text
gsd-plan-phase <phase> --prd docs/retrospectives/plans/generic-mcp-entrypoint-semantic-capabilities.md
```

The phase should start with the bounded research spike, then implement the
smallest profile metadata/router prototype that proves the abstraction without
rewriting both existing MCP servers.

## GSTACK REVIEW REPORT

| Review | Command | Scope | Runs | Status | Findings |
| --- | --- | --- | --- | --- | --- |
| CEO Review | `/plan-ceo-review` | Strategy and scope | 1 | clean | selective expansion; no unresolved challenges |
| Eng Review | `/plan-eng-review` | Architecture and tests | 1 | clean | schema/router/test risks reconciled into this plan |
| Design Review | `/plan-design-review` | UI/design | 0 | skipped | no UI scope detected |
| DX Review | `/plan-devex-review` | Developer experience | 1 | clean | score 7/10 -> 8/10 target, TTHW target under 5 minutes |
| Outside Voices | `autoplan-voices` | CEO, eng, DX | 0 | unavailable | Codex local read-only sandbox failed; no subagent tool exposed |
