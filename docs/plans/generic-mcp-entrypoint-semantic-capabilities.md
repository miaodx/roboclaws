# Generic MCP Entrypoint And Semantic Capabilities

**Status:** Proposed source plan
**Created:** 2026-05-13
**Source:** open-ended robot task architecture discussion and `CONTEXT.md`
vocabulary alignment
**Workflow:** Pre-GSD plan. Ingest into `.planning/` before implementation.

## Problem

Roboclaws currently has useful embodied demos, but the architecture is drifting
toward named tasks and backend-specific shortcuts instead of the original goal:
give the robot an open-ended task prompt and let an agent solve it with a small,
composable set of robot abilities.

The current surfaces are not wrong, but they mix abstraction levels:

- AI2-THOR navigation exposes `observe`, `move`, `scene_objects`, `goto`, and
  `done`.
- The photo task depends on `scene_objects` and `goto`, which are effective
  accelerators but not real robot capabilities.
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
- Shortcuts are either decomposed task shortcuts with traceable substeps or
  explicitly labeled accelerators outside the canonical contract.

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
- `scene_objects` and teleport-like `goto` are accelerators unless redesigned
  as decomposed semantic services.
- Deterministic cleanup policies and proof-bundle selection are baseline or
  evidence accelerators, not the target open-ended agent capability.

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

### Layer 4: Task Shortcuts And Accelerators

Convenience operations must be classified:

- **Canonical:** safe semantic capability in an open-ended contract.
- **Composed:** shortcut allowed when it records a decomposition trace.
- **Accelerator:** demo/debug/smoke/proof helper, excluded from canonical
  agent-facing contracts.

Initial classification:

- `observe`: Canonical. Implementations vary by profile.
- `move`: Profile-specific canonical tool or environment primitive. Appropriate
  for low-level navigation profiles, but not the only real-robot interface.
- `scene_objects`: Accelerator. Useful AI2-THOR inventory shortcut; not a real
  robot perception surface.
- Current AI2-THOR `goto`: Accelerator. Teleport-like; not route-planning-backed
  today.
- Future `navigate_to`: Canonical or composed. Should expose
  localization/navigation provenance.
- `pick` / `place`: Canonical. Must report manipulation provenance.
- Deterministic cleanup policy: Accelerator/baseline. Useful for reports and
  regressions, not target autonomy.
- Proof-bundle runner/selection: Private evidence accelerator. Supports proof
  claims; not public agent input.

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
- shortcut classification rules;
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
5. Mark existing accelerators in docs and profile metadata.
6. Add tests that prove canonical profiles do not expose private scoring truth
   or simulator-only accelerators by default.
7. Update agent-facing skills so prompts describe task prompts, semantic
   capabilities, and accelerator boundaries consistently.

## Non-Goals

- Do not build one universal MCP tool set that every environment must implement.
- Do not remove existing AI2-THOR or MolmoSpaces servers before the router is
  proven.
- Do not claim real robot readiness from simulator-only shortcuts.
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
  and accelerator exclusions.
- AI2-THOR `scene_objects` and current `goto` are labeled as accelerators or
  excluded from canonical profile metadata.
- Molmo cleanup profile preserves ADR-0003 public/private boundaries.
- Tests fail if canonical profiles expose private evaluator data or accelerator
  tools unintentionally.
- Existing demo recipes continue to run through their current commands.

## Verification Plan

- Unit tests for profile declaration parsing and validation.
- Contract tests for AI2-THOR and MolmoSpaces profile metadata.
- MCP registration tests for the generic entrypoint/router using a mock profile.
- Leak tests proving Molmo private scoring truth is absent from public profile
  declarations.
- Shortcut classification tests proving accelerators are opt-in or excluded
  from canonical agent-facing contracts.
- Focused docs tests or grep checks to keep `task prompt`, `capability tool`,
  `demo recipe`, and `accelerator` language consistent.
- Existing relevant MCP and cleanup contract tests through the repo-local
  pytest wrapper.

## ADR Follow-Up

Create an ADR only after the research spike and profile prototype answer the
hard implementation questions. The ADR should record whether this plan
supersedes, narrows, or extends ADR-0004. The likely decision shape is:

"Use one generic MCP entrypoint/router with profile-specific semantic tools,
while keeping backend-specific contract profiles and public/private boundaries."

## Risks

- A generic router could become a thin wrapper around unrelated tools unless
  profile metadata and tests enforce the capability model.
- A universal-looking surface could accidentally make simulator accelerators
  look like real robot capabilities.
- Too much abstraction could slow the thin-demo repo down. Keep the first phase
  metadata-first and preserve existing runnable demos.
- If semantic services become too powerful, they may hide open-ended planning
  inside tools and weaken the agent autonomy story.

## GSD Handoff

Preferred handoff:

```text
gsd-plan-phase <phase> --prd docs/plans/generic-mcp-entrypoint-semantic-capabilities.md
```

The phase should start with the research spike, then implement the smallest
profile metadata/router prototype that proves the abstraction without rewriting
both existing MCP servers.
