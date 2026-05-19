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

**Model-Declared Observation**:
A public observed handle created from an agent's own interpretation of camera evidence.
_Avoid_: Simulator detection, private target, local note

**Camera Inference Producer**:
The agent, model, detector, or perception service that interprets camera evidence into Model-Declared Observations.
_Avoid_: Scorer, simulator oracle, execution backend

**Active Camera Observation**:
A public camera observation made after the agent deliberately changes a bounded camera orientation.
_Avoid_: Report-only view, private evaluator camera, teleport view

**Policy Observation Camera**:
The robot camera whose images are exposed to the agent as the primary runtime
observation input.
_Avoid_: Report-only camera artifact, all-camera debug bundle, private evaluator view

**Environment Primitive**:
A backend-specific implementation of a physical or simulated robot action.
_Avoid_: Agent-facing task, universal capability

**Execution Backend**:
The actual simulated, mock, or physical environment where primitives run, such
as mock-only proof, AI2-THOR, MolmoSpaces, Unitree G1, RBY1M, AGIbot G2, or a
future robot.
_Avoid_: Semantic capability, task prompt

**Navigation + Perception Pilot**:
A first physical-robot deployment milestone that proves public navigation goals
and robot-local observations without claiming autonomous physical manipulation.
_Avoid_: Full cleanup deployment, physical cleanup proof

**Simulator/Hardware Contract Parity**:
The expectation that simulator and physical-robot profiles share the same
public capability shape while differing only in declared backend provenance and
known blocked capabilities.
_Avoid_: Identical implementation, pretending simulation is hardware proof

**Navigation Map Artifact**:
A backend-appropriate public map source used to ground cleanup navigation and
static scene semantics.
_Avoid_: Agent prompt map, private target map, raw SLAM state

**Nav2 Map Artifact**:
A ROS 2/Nav2-shaped Navigation Map Artifact used when the backend is Nav2 or a
simulator deliberately validating against Nav2-style costmap semantics.
_Avoid_: Universal physical robot map, hidden object map, report-only drawing

**Agibot GDK Map Context**:
An Agibot G2 map selection plus public semantic overlay used to ground GDK PNC
goals without treating the robot as a Nav2 backend.
_Avoid_: Nav2 Map Artifact, ROS2 map import, private target map

**Operator-Recorded Waypoint**:
A public semantic navigation point recorded by an operator on a robot-owned map.
_Avoid_: Auto-generated waypoint, planner-discovered pose, hidden evaluator point

**PNC-Verified Waypoint**:
An Operator-Recorded Waypoint whose reachability has been checked through the
robot's Agibot GDK PNC navigation surface.
_Avoid_: Authored-only waypoint, assumed reachable point, Nav2-verified waypoint

**Operator Localization Gate**:
An operator preparation condition that confirms the robot is on the intended
map and localized well enough before an Agibot agent run starts.
_Avoid_: Agent-facing relocalization tool, autonomous map switching, navigation retry

**Operator Run Enablement Gate**:
A run-level operator preparation condition that confirms a real robot may enter
an autonomous agent-controlled run within the allowed tool boundary.
_Avoid_: Per-action human approval, manipulation enablement, agent-facing command

**Human Takeover Stop**:
A fail-stop handoff where the robot stops after a navigation or local-motion
failure and waits for an operator instead of attempting autonomous recovery.
_Avoid_: Automatic fallback waypoint, exploration retry, hidden retargeting

**Waypoint-Resolved Visual Candidate**:
A Model-Declared Observation whose navigation target has been resolved to a
public verified waypoint rather than an arbitrary image-space or free-space pose.
_Avoid_: Visual-servo target, unverified object pose, free-space candidate

**Bounded Local Nudge**:
A tightly capped local motion near a verified navigation point, used for minor
viewpoint or alignment correction while making its limited safety model explicit.
_Avoid_: Exploration, arbitrary nearby navigation, obstacle-avoiding route plan

**Toward-Object Nudge**:
A backend-internal Bounded Local Nudge aimed slightly toward a currently visible
object after waypoint-resolved navigation.
_Avoid_: Object-level navigation, visual servoing, grasp positioning, exploration

**Object Approach Substep**:
A backend-specific final approach inside an existing object-navigation
capability after coarse navigation has already reached a nearby public pose.
_Avoid_: Public tool, standalone navigation goal, manipulation readiness

**Metric Map Projection**:
An agent-facing JSON view derived from a Navigation Map Artifact and public
semantic annotations.
_Avoid_: Raw occupancy map, private scene graph, independent map source, backend metadata

**Cleanup Map Semantics**:
Public room, fixture, affordance, waypoint, and frame annotations that make a
Navigation Map Artifact usable for cleanup planning.
_Avoid_: Private target truth, movable-object manifest, raw occupancy grid

**Static Fixture Footprint**:
The occupied navigation footprint of a fixed receptacle or furniture object in
a cleanup map.
_Avoid_: Movable object, manipulation target point, private target location

**Cleanup Map Exporter**:
A process that turns public static scene geometry and cleanup semantics into a
Navigation Map Artifact.
_Avoid_: Runtime scorer, private manifest reader, agent planner

**Map Bundle Snapshot**:
An immutable copy of the Navigation Map Artifact used by a single cleanup run.
_Avoid_: Newly generated report map, mutable asset map, private evaluation artifact

**Map Contract Harness**:
A deterministic pre-agent gate that validates a Navigation Map Artifact can
support cleanup navigation semantics.
_Avoid_: Live agent run, cleanup scorer, map generator

**Sim Costmap Route Validation**:
A simulator-side check that uses a Nav2-shaped static costmap to judge waypoint
reachability without claiming ROS 2/Nav2 execution.
_Avoid_: Full Nav2 sim, semantic teleport, physical navigation proof

**Agibot GDK PNC**:
A physical Agibot G2 navigation surface backed by Agibot's GDK
planning-and-control APIs rather than a ROS 2/Nav2 action.
_Avoid_: Nav2 action, ROS2 forwarding, generic G2 navigation

**Backend-Replaceable Navigation**:
An agent-facing navigation capability whose public goal shape stays stable while
the execution backend and primitive provenance vary by robot or simulator.
_Avoid_: Backend-specific tool name, hidden retargeting, direct driver command

**Robot Profile**:
A named robot configuration for navigation and perception parameters such as
footprint, inflation radius, frames, camera pose, and goal tolerances.
_Avoid_: Environment map, scene id, embodiment proof

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

**Local Coding-Agent Route**:
An operator-run Codex or Claude Code path that launches the local CLI/runtime and
receives provider API configuration from the repo-local `.env`. On the work
network, this is the only supported Codex or Claude Code route. On a non-work
network, OpenClaw routes may also run.
_Avoid_: Hosted CI proof, repository secret contract, official provider gate

**CI Coding-Agent Boundary**:
The rule that hosted CI may run deterministic checks plus supported Claude Code
and OpenClaw routes, but must not launch Codex, run Codex provider smoke, or
publish Codex acceptance artifacts.
_Avoid_: Codex acceptance artifact, official Codex CI route, hosted model proof

**Contract Profile**:
A public capability boundary with explicit policy inputs, tool names, evidence
boundaries, and allowed backend scope.
_Avoid_: Universal robot API, hidden evaluator, concrete backend implementation

**Backend Variant**:
The concrete execution path behind a shared Contract Profile, such as Nav2
actions or Agibot GDK PNC.
_Avoid_: New public profile, agent-facing tool namespace, hidden provenance

**Backend Variant Set**:
The declared set of Backend Variants allowed under one Contract Profile.
_Avoid_: Tool list, robot profile, runtime auto-detection

**Navigation Backend Label**:
A coarse label for the execution or validation stack responsible for a
navigation result.
_Avoid_: Concrete primitive, evidence status, agent-facing tool name

**Navigation Primitive Provenance**:
A fine-grained label for the concrete navigation primitive or evidence used by
a navigation result or substep.
_Avoid_: Backend family only, agent-facing tool name, hidden evidence level

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
- A **Model-Declared Observation** must be traceable to public camera evidence
  and may become the handle used by manipulation **Capability Tools**.
- A **Camera Inference Producer** may be the main cleanup agent, a specialist
  model, a detector, or a robot perception service.
- An **Active Camera Observation** is public perception evidence and may support
  a **Model-Declared Observation**.
- Agibot G2 should use `head_color` as the default **Policy Observation
  Camera** for runtime agent `observe()`; other available cameras may be
  retained as report/debug artifacts.
- Agibot G2 `adjust_camera` should remain `blocked_capability` in the first
  Navigation + Perception Pilot; head/body camera motion control is a later
  capability.
- A **Contract Profile** is named by both environment and task domain when both
  matter, such as `ai2thor_navigation_v1`, `molmospaces_cleanup_v1`, or
  `real_robot_cleanup_v1`.
- A **Contract Profile** declares the **Capability Families** it supports.
- A **Contract Profile** may bind to a concrete backend, a backend family, or a
  **Backend Variant Set** when the public tool shape and safety policy stay
  stable.
- The `real_robot_cleanup_v1` **Contract Profile** may support multiple real
  robot backend variants when the public tool shape and safety policy remain
  the same.
- The `real_robot_cleanup_v1` **Contract Profile** should describe the shared
  physical cleanup pilot boundary, not a single Nav2-only backend.
- The `real_robot_cleanup_v1` profile metadata should use
  `backend=physical_robot` and declare a **Backend Variant Set** including
  `nav2_ros2` and `agibot_gdk`, rather than hard-coding `ros2_nav2`.
- Real robot execution differences should be represented as **Backend
  Variants** with explicit **Navigation Backend Labels** and
  **Navigation Primitive Provenance**.
- Canonical `navigation_backend` values should name the coarse execution or
  validation stack, such as `nav2_static_costmap`, `nav2_ros2`, or
  `agibot_gdk`.
- Canonical navigation `primitive_provenance` values should name the concrete
  primitive or evidence type, such as `nav2_static_costmap_validation`,
  `nav2_ros2_navigate_to_pose_action`, `agibot_gdk_normal_navi`, or
  `agibot_gdk_relative_move`.
- Failed or blocked navigation should keep `navigation_backend` set to the
  intended execution or validation stack when known, while
  `primitive_provenance=blocked_capability` records that no successful
  navigation primitive was proven.
- The agent-facing tool name already supplies the semantic role, so backend and
  provenance labels should not repeat `waypoint`, `object`, or `receptacle`
  unless a future single response contains multiple navigation roles.
- An **MCP Entrypoint** may be generic while the exposed **Contract Profile**
  remains backend-specific.
- A **Semantic Capability** may be backed by different **Environment
  Primitives** in AI2-THOR, MuJoCo, or a real robot.
- An **Environment Primitive** runs in one **Execution Backend**.
- A **Navigation + Perception Pilot** may use the same **Task Prompt** and
  **Contract Profile** shape as cleanup while proving only navigation and
  observation capabilities.
- **Simulator/Hardware Contract Parity** lets a simulator run exercise the same
  **Capability Tools** as hardware while reports still distinguish
  **Execution Backends** and blocked capabilities.
- A **Navigation Map Artifact** may be generated from MolmoSpaces scene geometry
  or provided by a physical robot map workflow, but it must preserve the same
  public contract shape.
- A **Nav2 Map Artifact** is one kind of **Navigation Map Artifact**.
- An **Agibot GDK Map Context** is one kind of **Navigation Map Artifact**.
- A **Metric Map Projection** is generated from a **Navigation Map Artifact** for
  agent planning; it should not be maintained as an independent map source.
- For Agibot G2, a **Metric Map Projection** should come from an **Agibot GDK
  Map Context** plus **Cleanup Map Semantics**, not from a required **Nav2 Map
  Artifact**.
- Agibot G2 **Metric Map Projection** should remain backend-agnostic agent
  planning input: rooms, fixtures, public waypoints, and reachability or blocked
  status, not backend variant metadata.
- Agibot G2 map source type, map id/name, current-map evidence, **Backend
  Variant Set**, and PNC details are operator/report or tool-result evidence,
  not agent-facing **Metric Map Projection** content.
- Agibot G2 **Cleanup Map Semantics** should use **Operator-Recorded
  Waypoints** unless a reliable robot map export and waypoint-generation path
  has been proven.
- **Operator-Recorded Waypoints** are prepared before a cleanup agent run; they
  are not created or edited by the agent as a cleanup **Capability Tool**.
- One **Agibot GDK Map Context** may contain multiple **Operator-Recorded
  Waypoints** for different rooms, fixtures, and observation poses.
- A **PNC-Verified Waypoint** is stronger evidence than an
  **Operator-Recorded Waypoint**; recording a waypoint does not prove it is
  currently reachable.
- PNC verification is an operator preparation action, not an agent-facing
  cleanup **Capability Tool**.
- Agibot G2 PNC waypoint verification evidence should use
  `navigation_backend=agibot_gdk`,
  `primitive_provenance=agibot_gdk_normal_navi`, and normalized
  `reachability_status` values `verified`, `blocked`, or `timeout`; schema or
  script names may still mention PNC when describing the verification method.
- A real Agibot G2 **Navigation + Perception Pilot** should require every public
  inspection waypoint to have PNC verification evidence before claiming hardware
  pilot readiness.
- Agibot G2 should require an **Operator Localization Gate** before an agent run
  attempts navigation; the operator owns map selection, G02 Pad relocalization,
  and localization readiness.
- Agibot G2 should require an **Operator Run Enablement Gate** before an
  autonomous agent-controlled run starts; after the gate, the agent may call the
  allowed navigation tools without per-action human approval.
- The **Operator Run Enablement Gate** does not enable manipulation: Agibot G2
  `pick`, `place`, `place_inside`, `open_receptacle`, and `close_receptacle`
  remain `blocked_capability` in the first pilot.
- Agibot G2 runtime may record the current map and localization evidence for
  reports, but it should not treat map selection or relocalization as an
  agent-facing **Capability Tool**.
- If the **Operator Localization Gate** is missing or inconsistent with the
  selected **Agibot GDK Map Context**, Agibot G2 `navigate_to_*` capabilities
  should return `blocked_capability` instead of attempting autonomous map
  switching or relocalization.
- In the first Agibot G2 pilot, failed `navigate_to_*` execution or failed
  **Object Approach Substep** should enter **Human Takeover Stop** instead of
  trying fallback waypoints, unverified goals, map switching, relocalization, or
  additional local nudges.
- Agibot G2 agent-facing navigation should default to **PNC-Verified
  Waypoints**; unverified waypoints may appear in reports but should be blocked
  as runtime navigation goals unless an operator deliberately enables a
  development override.
- Agibot G2 should not expose **Bounded Local Nudge** as a separate
  agent-facing **Capability Tool** in the first pilot; bounded nudges may be
  backend-internal substeps of existing navigation tools.
- Agibot G2 **Bounded Local Nudge** should report distinct
  `agibot_gdk_relative_move` provenance and a safety model of simple obstacle
  stop without obstacle avoidance.
- Agibot G2 **Bounded Local Nudge** and **Toward-Object Nudge** evidence should
  appear as navigation substeps; they should not overwrite the top-level
  `primitive_provenance` of `navigate_to_object` or
  `navigate_to_visual_candidate`.
- Agibot G2 top-level object navigation should report
  `navigation_backend=agibot_gdk` and `primitive_provenance=agibot_gdk_normal_navi`
  when the waypoint navigation succeeds, with any `agibot_gdk_relative_move`
  approach recorded separately as an **Object Approach Substep**.
- Agibot G2 `relative_move` outside **Bounded Local Nudge** constraints and
  chassis velocity control remain operator/debug primitives, not first-pilot
  agent-facing cleanup navigation capabilities.
- Agibot G2 may support visual candidate declaration and inspection from public
  `head_color` evidence, but first-pilot visual-candidate navigation should
  remain `blocked_capability` unless the target resolves to a **PNC-Verified
  Waypoint**.
- Agibot G2 `navigate_to_visual_candidate` should use
  **Waypoint-Resolved Visual Candidate** semantics: the visual candidate may
  choose or justify a public waypoint, but it must not create an arbitrary
  robot-local navigation goal.
- After Agibot G2 reaches the waypoint for a **Waypoint-Resolved Visual
  Candidate**, a **Bounded Local Nudge** may be used internally as an
  **Object Approach Substep** when enabled, but the agent-facing call remains
  `navigate_to_visual_candidate` or `navigate_to_object`.
- A **Toward-Object Nudge** may be used after Agibot G2 reaches a
  **PNC-Verified Waypoint** and the target object remains visible in public
  `head_color` evidence; it should replace the simulator-style near-object
  approach step, not claim precise object navigation or manipulation readiness.
- Agibot G2 **Toward-Object Nudge** should remain small, explicitly bounded, and
  backed by the same simple-stop-without-avoidance safety model as other
  **Bounded Local Nudge** actions.
- A cleanup-capable **Navigation Map Artifact** must include **Cleanup Map
  Semantics**; a raw occupancy map alone is insufficient for cleanup planning.
- A **Static Fixture Footprint** should be occupied or otherwise declared
  blocked in a **Navigation Map Artifact**, while its preferred inspection or
  manipulation waypoint should be a nearby free pose.
- A **Cleanup Map Exporter** may use public simulator room and fixture metadata
  plus authored overrides; raw simulator XML parsing is an optional later
  enrichment, not the first source of truth.
- A cleanup run should consume a prebuilt **Navigation Map Artifact** and copy a
  **Map Bundle Snapshot** into its report artifacts.
- A cleanup run should fail fast when its required prebuilt **Navigation Map
  Artifact** is missing; map generation is a preparation step, not an implicit
  runtime side effect.
- Supported simulator demo **Nav2 Map Artifacts** may be committed for
  deterministic harness use, while physical robot map artifacts may remain
  operator-provided local inputs.
- A **Map Contract Harness** should validate a **Navigation Map Artifact**
  before a live agent attempts a cleanup run.
- A **Map Contract Harness** is a deterministic checker, not an agent-driven
  cleanup run.
- Live agent cleanup runs should require the **Map Contract Harness** to pass;
  mocked synthetic tests may use explicit lightweight fixtures.
- Map-layer acceptance should be deterministic before live-agent proof: a valid
  **Navigation Map Artifact**, **Metric Map Projection**, and
  backend-appropriate route validation such as **Sim Costmap Route Validation**
  should pass before any **Local Coding-Agent Route** or OpenClaw run.
- Local work-network runs support only Codex and Claude Code through the
  **Local Coding-Agent Route**, using API base/key and provider/model settings
  from the repo-local `.env`; OpenClaw is not supported on the work network.
- Local non-work-network runs support the same `.env`-configured Codex and
  Claude Code routes, plus OpenClaw.
- Hosted CI does not support Codex at all. It should not launch Codex, run
  Codex provider smoke, or block a pipeline on a Codex acceptance artifact.
- Hosted CI may run supported Claude Code and OpenClaw routes. Claude Code test
  models must stay within the provider/model configuration represented by the
  repo-local `.env`; do not add arbitrary CI-only Claude model assumptions.
- **Sim Costmap Route Validation** may consume a **Nav2 Map Artifact** in
  simulation, while physical Nav2 execution consumes a **Nav2 Map Artifact**
  through a Nav2 action backend.
- **Agibot GDK PNC** should consume an **Agibot GDK Map Context**, not a
  **Nav2 Map Artifact**, unless an explicit Nav2 export/import path has been
  proven.
- **Agibot GDK PNC** may back the same cleanup navigation **Semantic
  Capability** as a Nav2 action backend, but it must report distinct provenance
  such as `agibot_gdk_normal_navi` rather than
  `nav2_ros2_navigate_to_pose_action`.
- `navigate_to_waypoint`, `navigate_to_room`, and `navigate_to_receptacle`
  should be **Backend-Replaceable Navigation** capabilities when their public
  semantics stay stable across simulator, Nav2, and Agibot GDK PNC backends.
- Agibot G2 should implement existing `navigate_to_waypoint` and
  `navigate_to_receptacle` semantics by resolving public goals to
  **PNC-Verified Waypoints** and executing **Agibot GDK PNC**, not by exposing
  Agibot-specific agent-facing navigation tool names.
- Agibot G2 `navigate_to_receptacle` should remain fixture-to-preferred-waypoint
  navigation; if the fixture's preferred waypoint is not a **PNC-Verified
  Waypoint**, the capability should return `blocked_capability`.
- In a **Navigation + Perception Pilot**, `navigate_to_receptacle` may mean
  navigation to a fixture's preferred public waypoint for inspection, even when
  no object is held; physical placement readiness must be reported separately.
- A **Bounded Local Nudge** may be recorded as an explicit
  **Object Approach Substep** inside **Backend-Replaceable Navigation**, but it
  should not appear as a standalone agent API or replace waypoint/receptacle
  navigation as the primary route mechanism.
- A **Robot Profile** is combined with a **Navigation Map Artifact** to derive
  robot-specific planning and safety parameters without rewriting the
  environment map.
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
- A robot-specific **Contract Profile** should be created only when the
  agent-facing tool shape or safety policy differs, not merely because the
  **Execution Backend** differs.
- Agibot G2 should remain a **Backend Variant** under
  `real_robot_cleanup_v1`; do not introduce `agibot_g2_cleanup_v1` unless the
  public agent-facing tool shape or safety policy diverges.
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
- "real world robot integration" was used ambiguously for physical navigation,
  physical observation, and full physical cleanup. Resolved: the first milestone
  is a **Navigation + Perception Pilot**; physical manipulation remains a
  separate proof target.
- "Nav2 map consumption" was used ambiguously for agent-visible planning input,
  simulator route validation, and full ROS 2/Nav2 execution. Resolved: in
  MolmoSpaces simulation, use **Sim Costmap Route Validation**; reserve full
  Nav2 execution claims for a physical or explicit ROS 2 backend.
- "Agibot G2 navigation" was used as if it automatically implied ROS 2/Nav2
  execution. Resolved: use **Agibot GDK PNC** for GDK-backed navigation and
  reserve `nav2_ros2_navigate_to_pose_action` for actual ROS 2/Nav2 action
  execution.
- "metric map" was used ambiguously as both source data and agent projection.
  Resolved: use **Navigation Map Artifact** for the static source of truth and
  **Metric Map Projection** for the JSON view exposed to agents.
- "metric_map comes from Nav2 maps" was used as if it applied to all physical
  robots. Resolved: **Nav2 Map Artifact** is valid for Nav2-backed robots, while
  Agibot G2 should use **Agibot GDK Map Context** unless a real Nav2 map bridge
  exists.
- "Agibot metric_map visibility" was used ambiguously for agent planning input
  and operator/report evidence. Resolved: keep **Metric Map Projection**
  backend-agnostic for the agent; expose public semantic waypoints and
  reachability status there, while keeping backend variants, raw GDK map data,
  current-map evidence, and PNC internals in operator/report or tool-result
  evidence.
- "generate Agibot waypoints from the map" was used without an available map
  export/free-space source. Resolved: use **Operator-Recorded Waypoints** for
  the first Agibot G2 integration.
- "recorded Agibot waypoint" was used as if it meant reachable. Resolved:
  require **PNC-Verified Waypoint** evidence before claiming Agibot hardware
  pilot readiness.
- "Agibot relocalization" was used ambiguously for operator preparation and
  robot-agent capability. Resolved: use **Operator Localization Gate** for
  operator-owned map selection, G02 Pad relocalization, and localization
  readiness before the agent run starts.
- "human approval for Agibot motion" was used ambiguously for run-level safety
  enablement and per-action approval. Resolved: use **Operator Run Enablement
  Gate** before the autonomous run starts; do not put a human approval loop
  between normal agent navigation actions.
- "Agibot navigation recovery" was used ambiguously for fallback planning and
  operator intervention. Resolved: in the first pilot, use **Human Takeover
  Stop** after navigation or local-motion failure.
- "nearby Agibot movement" was used ambiguously for safe local adjustment,
  arbitrary non-waypoint navigation, and low-level velocity control. Resolved:
  use **Bounded Local Nudge** only as a tightly capped internal substep near a
  **PNC-Verified Waypoint**; it is not obstacle-avoiding navigation or a public
  agent-facing API.
- "Agibot navigation tools" was used as if a new robot required new
  agent-facing tool names. Resolved: keep navigation as
  **Backend-Replaceable Navigation** where possible; Agibot changes backend
  provenance and waypoint verification requirements, not the public
  `navigate_to_*` semantics.
- "`real_robot_cleanup_v1` backend" was used as if the profile itself meant
  ROS 2/Nav2. Resolved: the profile is the shared physical cleanup pilot
  boundary; Nav2 and Agibot are **Backend Variants** distinguished by reported
  backend and provenance.
- "`real_robot_cleanup_v1` metadata" was used as if `backend=ros2_nav2` were
  still correct. Resolved: use `backend=physical_robot` plus a **Backend Variant
  Set** such as `nav2_ros2` and `agibot_gdk`.
- "`agibot_g2_cleanup_v1`" was considered as a robot-specific profile.
  Resolved: keep Agibot G2 as a **Backend Variant** under
  `real_robot_cleanup_v1` while the public tool shape and safety policy match.
- Navigation backend/provenance labels were used as backend-only tokens such as
  `sim_costmap_planner`, `nav2_action`, or `agibot_gdk_pnc`. Resolved: split
  coarse **Navigation Backend Labels** from fine-grained **Navigation Primitive
  Provenance**; use backend labels such as `nav2_static_costmap`, `nav2_ros2`,
  and `agibot_gdk`, and provenance labels such as
  `nav2_static_costmap_validation`, `nav2_ros2_navigate_to_pose_action`,
  `agibot_gdk_normal_navi`, and `agibot_gdk_relative_move`.
- "visual candidate navigation" was used ambiguously for object-relative
  navigation, visual servoing, and waypoint selection. Resolved: in the first
  Agibot pilot, use **Waypoint-Resolved Visual Candidate** semantics and block
  unresolved candidates.
- "nudge toward the object" was used ambiguously for showing approach intent and
  for precise object-level navigation. Resolved: use **Toward-Object Nudge** as
  a bounded post-waypoint **Object Approach Substep** inside existing
  `navigate_to_object` or `navigate_to_visual_candidate` semantics; do not treat
  it as a standalone API, grasp-positioning capability, or exploration
  capability.
- "relative_move provenance" was used ambiguously as either a top-level
  navigation result or an internal approach step. Resolved: keep
  `agibot_gdk_relative_move` in substep evidence and preserve the top-level
  navigation provenance for the main `navigate_to_*` call.
- "PNC waypoint verification labels" were used as if the method name
  `agibot_gdk_pnc` should also be the backend and primitive provenance.
  Resolved: keep PNC in verification schema/script names when useful, but record
  `navigation_backend=agibot_gdk`,
  `primitive_provenance=agibot_gdk_normal_navi`, and normalized
  `reachability_status` values.
