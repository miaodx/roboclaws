# Roboclaws Context

Roboclaws is a robot-agent demo context where user instructions are separated
from the robot abilities exposed to agents and from runnable demo packaging.

## Language

**Task Prompt**:
A user instruction describing desired robot work in open-ended language.
_Avoid_: Task API, recipe, benchmark name

**Open-Ended Goal**:
A high-level user intent that may be delegated to an Agent Skill or
decomposed by the agent into lower-level capabilities.
_Avoid_: Open question, MCP query, single tool

**Agent Skill**:
A reusable package of model operating knowledge, scripts, heuristics, examples,
and checks that attempts goals by calling available tools.
_Avoid_: Robot capability claim, MCP contract, backend primitive

**Capability Tool**:
A composable robot ability exposed to an agent for perception, navigation, or manipulation.
_Avoid_: Task, demo, scenario

**Environment Primitive**:
A backend-specific implementation of a physical or simulated robot action.
_Avoid_: Agent-facing task, universal capability

**Execution Backend**:
The actual simulated, mock, or physical environment where primitives run, such
as mock-only proof, AI2-THOR, MolmoSpaces, Unitree G1, RBY1M, AGIbot G2, or a
future robot.
_Avoid_: Semantic capability, task prompt

**Semantic Capability**:
A backend-neutral robot ability exposed to an agent with stable meaning across environments.
_Avoid_: Environment primitive, opaque composite action

**Atomic Semantic Capability**:
A small composable Semantic Capability such as observe, move, turn, pick,
place, open, or close.
_Avoid_: Environment primitive, opaque composite action

**Composed Semantic Capability**:
A higher-level Semantic Capability or Semantic Service built from atomic
capabilities, such as localization, navigation, search, inspect, or transport.
_Avoid_: Whole user task, opaque composite action

**Semantic Service**:
A reusable algorithmic layer that supports capabilities, such as localization,
navigation, semantic mapping, or memory retrieval.
_Avoid_: MCP task, one-off helper

**Composite Action**:
A convenience operation that composes semantic services and capabilities for a
common user goal.
_Avoid_: Primitive, irreducible capability

**Privileged Tool**:
A demo, debug, smoke, or proof helper that speeds evidence generation but is not
part of the canonical agent-facing contract.
_Avoid_: Capability tool, semantic capability

**Skill Library Lifecycle**:
The process where agent skills are discovered, used, created from successful
task traces, refactored, merged, and pruned over time.
_Avoid_: Robot capability layer, one-off script folder

**Skill-First, MCP-Bounded Architecture**:
The design principle that reusable behavior should live in Agent Skills by
default, while MCP profiles define the public robot capability boundary and
execution backends implement environment-specific primitives.
_Avoid_: Everything is an MCP tool, premature universal robot API

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

- The canonical abstraction ladder is: **Open-Ended Goal** ->
  **Agent Skill** -> **Composite Action** or **Composed Semantic Capability**
  -> **Atomic Semantic Capability** -> **Environment Primitive** ->
  **Execution Backend**.
- A **Task Prompt** is attempted by an agent using one or more
  **Capability Tools**.
- A **Task Prompt** may express an **Open-Ended Goal** directly or select,
  create, or refine an **Agent Skill**.
- A **Contract Profile** defines which **Capability Tools** are available and
  what information they may expose.
- A **Contract Profile** is named by both environment and task domain when both
  matter, such as `ai2thor_navigation_v1` or `molmospaces_cleanup_v1`.
- A **Contract Profile** declares the **Capability Families** it supports.
- An **MCP Entrypoint** may be generic while the exposed **Contract Profile**
  remains backend-specific.
- A **Semantic Capability** may be backed by different **Environment
  Primitives** in AI2-THOR, MuJoCo, or a real robot.
- An **Environment Primitive** runs in one **Execution Backend**.
- A **Composed Semantic Capability** is built from **Atomic Semantic
  Capabilities**, Semantic Services, or both.
- A **Semantic Service** may compose **Environment Primitives** and support
  multiple **Semantic Capabilities**.
- A **Composite Action** must be explainable as a composition of
  **Semantic Services** and **Semantic Capabilities**.
- A **Composite Action** may be exposed to agents only when it records or preserves
  its decomposition; otherwise it is a **Privileged Tool**.
- A **Composite Action** is descriptive by default, not a first-class artifact:
  the maintained package should usually be an **Agent Skill** with scripts,
  examples, checks, and lifecycle metadata.
- A **Privileged Tool** may remain useful for demos and local evidence, but it must
  not be treated as proof that a canonical robot capability exists.
- Agent-facing MCP contracts should expose **Semantic Capabilities** and
  selected **Semantic Services**, not raw **Environment Primitives**.
- Agents own open-ended goal planning; **Agent Skills** may be delegated to when
  useful, and **Semantic Services** own bounded subproblems such as route
  planning, object association, map lookup, grasp feasibility, or memory
  retrieval.
- A whole user task such as room cleanup should remain a **Task Prompt**, not
  become a single opaque **Capability Tool**.
- A **Demo Recipe** may seed a **Task Prompt**, select a **Contract Profile**,
  and collect evidence, but it is not itself a robot ability.
- Different **Contract Profiles** may exist for different backends while
  preserving the same open-ended **Task Prompt** model.
- Roboclaws should move toward one generic **MCP Entrypoint** or router that
  loads profile-specific semantic tools, not one premature universal MCP tool
  set implemented by every environment.
- The **Skill Library Lifecycle** operates above the robot capability ladder:
  agent skills may call tools, services, or scripts, but they are maintained as
  reusable agent behavior rather than canonical robot capability claims.
- The **Skill Library Lifecycle** loop is: receive an **Open-Ended Goal**,
  search/select an existing **Agent Skill**, solve with lower-level tools when
  no good skill exists, record trace/report/evaluation evidence, extract or
  improve reusable skill behavior, then periodically refactor, merge, prune, and
  re-evaluate the skill library.
- In a **Skill-First, MCP-Bounded Architecture**, an **Agent Skill** is the
  default home for reusable behavior such as `capture_object_photo`; the MCP
  profile should expose lower-level stable public capabilities unless the
  behavior has become a clear, broadly reusable capability with preserved
  substeps and evidence.
- Roboclaws should resist adding MCP tools by default. Promote behavior from an
  **Agent Skill** or script into an MCP tool only when multiple skills need it,
  the inputs and outputs are stable for one contract profile, it has traceable
  substeps or a clear atomic meaning, it uses only public allowed information,
  and it belongs in the robot capability boundary rather than agent strategy.

## Example Dialogue

> **Dev:** "Should `clean the room` become a new MCP tool?"
> **Domain expert:** "No. `clean the room` is a **Task Prompt**; the agent
> should solve it with **Capability Tools** such as observe, navigate, pick,
> and place."

> **Dev:** "Should `goto` be a core robot primitive?"
> **Domain expert:** "No. `goto` is a **Composite Action** unless its
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
  **Semantic Capability**, and **Composite Action** for those distinct levels.
- Current AI2-THOR `scene_objects` and teleport-like `goto` are
  **Privileged Tools** unless redesigned as decomposed semantic services.
