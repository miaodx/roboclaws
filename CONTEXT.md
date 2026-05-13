# Roboclaws Context

Roboclaws is a robot-agent demo context where user instructions are separated
from the robot abilities exposed to agents and from runnable demo packaging.

## Language

**Task Prompt**:
A user instruction describing desired robot work in open-ended language.
_Avoid_: Task API, recipe, benchmark name

**Capability Tool**:
A composable robot ability exposed to an agent for perception, navigation, or manipulation.
_Avoid_: Task, demo, scenario

**Environment Primitive**:
A backend-specific implementation of a physical or simulated robot action.
_Avoid_: Agent-facing task, universal capability

**Semantic Capability**:
A backend-neutral robot ability exposed to an agent with stable meaning across environments.
_Avoid_: Environment primitive, task shortcut

**Semantic Service**:
A reusable algorithmic layer that supports capabilities, such as localization,
navigation, semantic mapping, or memory retrieval.
_Avoid_: MCP task, one-off helper

**Task Shortcut**:
A convenience operation that composes semantic services and capabilities for a
common user goal.
_Avoid_: Primitive, irreducible capability

**Accelerator**:
A demo, debug, smoke, or proof helper that speeds evidence generation but is not
part of the canonical agent-facing contract.
_Avoid_: Capability tool, semantic capability

**Demo Recipe**:
A runnable operator command that packages one scenario, driver, report mode, and evidence path.
_Avoid_: Robot ability, task prompt

**Contract Profile**:
A backend-specific public capability surface with explicit policy inputs, tool
names, and evidence boundaries.
_Avoid_: Universal robot API, hidden evaluator

**MCP Entrypoint**:
The MCP server process or router that exposes one selected contract profile to an agent.
_Avoid_: Universal tool set

**Capability Family**:
A stable category of semantic capability, such as perception, localization,
mapping, navigation, manipulation, or memory.
_Avoid_: Backend profile, task recipe

## Relationships

- A **Task Prompt** is attempted by an agent using one or more
  **Capability Tools**.
- A **Contract Profile** defines which **Capability Tools** are available and
  what information they may expose.
- A **Contract Profile** is named by both environment and task domain when both
  matter, such as `ai2thor_navigation_v1` or `molmospaces_cleanup_v1`.
- A **Contract Profile** declares the **Capability Families** it supports.
- An **MCP Entrypoint** may be generic while the exposed **Contract Profile**
  remains backend-specific.
- A **Semantic Capability** may be backed by different **Environment
  Primitives** in AI2-THOR, MuJoCo, or a real robot.
- A **Semantic Service** may compose **Environment Primitives** and support
  multiple **Semantic Capabilities**.
- A **Task Shortcut** must be explainable as a composition of
  **Semantic Services** and **Semantic Capabilities**.
- A **Task Shortcut** may be exposed to agents only when it records or preserves
  its decomposition; otherwise it is an **Accelerator**.
- An **Accelerator** may remain useful for demos and local evidence, but it must
  not be treated as proof that a canonical robot capability exists.
- Agent-facing MCP contracts should expose **Semantic Capabilities** and
  selected **Semantic Services**, not raw **Environment Primitives**.
- Agents own open-ended task planning; **Semantic Services** own bounded
  subproblems such as route planning, object association, map lookup, grasp
  feasibility, or memory retrieval.
- A whole user task such as room cleanup should remain a **Task Prompt**, not
  become a single opaque **Capability Tool**.
- A **Demo Recipe** may seed a **Task Prompt**, select a **Contract Profile**,
  and collect evidence, but it is not itself a robot ability.
- Different **Contract Profiles** may exist for different backends while
  preserving the same open-ended **Task Prompt** model.
- Roboclaws should move toward one generic **MCP Entrypoint** or router that
  loads profile-specific semantic tools, not one premature universal MCP tool
  set implemented by every environment.

## Example Dialogue

> **Dev:** "Should `clean the room` become a new MCP tool?"
> **Domain expert:** "No. `clean the room` is a **Task Prompt**; the agent
> should solve it with **Capability Tools** such as observe, navigate, pick,
> and place."

> **Dev:** "Should `goto` be a core robot primitive?"
> **Domain expert:** "No. `goto` is a **Task Shortcut** unless its
> implementation is decomposed into localization, navigation, and motion
> **Semantic Services** backed by environment-specific primitives."

## Flagged Ambiguities

- "task" was used for both runnable `just task::run` commands and open-ended
  robot work. Resolved: use **Demo Recipe** for runnable packaging and
  **Task Prompt** for robot work.
- "ability" was used for both low-level tools and named task flows. Resolved:
  use **Capability Tool** for composable robot abilities.
- "atomic capability" was used across backend actions, agent-facing abilities,
  and composed helpers. Resolved: use **Environment Primitive**,
  **Semantic Capability**, and **Task Shortcut** for those distinct levels.
- Current AI2-THOR `scene_objects` and teleport-like `goto` are
  **Accelerators** unless redesigned as decomposed semantic services.
