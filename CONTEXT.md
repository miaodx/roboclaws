# Roboclaws Context

This file is the durable vocabulary and boundary map for Roboclaws. It should
stay short. Put implementation plans in `docs/plans/`, current status in
`STATUS.md`, detailed human architecture in `ARCHITECTURE.md` and
`docs/human/**`, and run evidence in `docs/status/active/`, retrospectives, or
`output/`.

## Maintenance Contract

Future agents should maintain this file as a compact context primer, not as a
planning log.

- Target size: keep this file under about 350 lines and 18KB. If it approaches
  400 lines or 25KB, reduce or split before adding more.
- Add content only when it changes durable vocabulary, public/private
  boundaries, task/skill/profile layering, safety gates, or real-robot proof
  claims.
- Do not add progress notes, run results, implementation plans, command logs,
  benchmark details, or historical discussion transcripts.
- Prefer rewriting or merging an existing term over appending a near-duplicate.
- Keep each term to one definition and one `_Avoid_` line unless a boundary
  truly requires more.
- Move detailed topic material to the right owner doc and link it from
  **Pointers**: `docs/human/**` for human design, `docs/plans/**` for plans,
  `docs/status/active/**` for active evidence, and `docs/adr/**` for durable
  decisions.
- When a grilling session resolves terminology, update this file immediately,
  then rerun a saturation audit before asking more questions.
- Read this file selectively when possible: search for the relevant term or
  section instead of loading it as a general progress history.

## Current Architecture Vocabulary

**Task Prompt**:
A user instruction describing desired robot work in open-ended language.
_Avoid_: task API, recipe, benchmark name

**Runnable Task**:
A public run-catalog entry such as `semantic-map-build`, `household-cleanup`,
`ai2thor-nav`, or `photo-chairs`, usually invoked through `just task::run`.
It owns command name, parameters, report shape, and acceptance gates.
_Avoid_: Agent Skill, Capability Profile, backend script, hidden evaluator

**Agent Skill**:
A reusable package of model operating knowledge, scripts, heuristics, examples,
and checks that attempts goals by calling available tools.
_Avoid_: robot capability claim, MCP contract, backend primitive

**Trace-Preserving Skill Routine**:
A reusable skill routine that composes lower-level public tools while recording
substeps, evidence, status, and recovery context.
_Avoid_: prompt-only trick, hidden task automation, promoted MCP capability

**Capability Profile**:
A reusable public capability environment: tool names, capability families,
provenance expectations, blocked capabilities, privileged-tool metadata, and
private-data exclusions. Skills require profiles; profiles should not be copied
into task-specific supersets.
_Avoid_: task recipe, universal robot API, concrete backend implementation

**Capability Tool**:
A composable public robot ability exposed through MCP, such as observe,
navigate, pick, place, or done.
_Avoid_: whole task, demo recipe, environment primitive

**Backend Variant**:
The concrete implementation path behind a shared task/profile shape, such as
`molmospaces_subprocess`, `api_semantic_synthetic`, `agibot_g2`, or
`ros2_nav2`.
_Avoid_: new public task, new profile name, agent-facing tool namespace

**Environment Primitive**:
A backend-specific low-level action, simulator call, robot SDK call, planner
call, or mock operation.
_Avoid_: agent-facing capability, public task, universal tool

**Execution Backend**:
The actual environment where primitives run: mock, AI2-THOR, MolmoSpaces,
Nav2/ROS2, Agibot G2, RBY1M, or a future robot.
_Avoid_: capability profile, skill, task prompt

## Household World And Cleanup Vocabulary

**Navigation Map Artifact**:
A reusable static source of navigation geometry and public semantic annotations.
It may be generated from simulator geometry or provided by a physical robot map
workflow.
_Avoid_: runtime observation memory, private scene graph, raw hidden truth

**Metric Map Projection**:
The agent-facing JSON view derived from a Navigation Map Artifact.
_Avoid_: raw occupancy map, independent map source, private backend metadata

**Runtime Metric Map**:
The current-run Metric Map Projection after public runtime evidence is added:
observed object handles, loaded priors, and map update candidates.
_Avoid_: source map artifact, hidden mutable global map, private target truth

**Semantic Map Build Task**:
A first-class Runnable Task that navigates and observes to produce a Runtime
Metric Map snapshot for later robot tasks. It selects a map-building skill,
requires household world capabilities, and disables manipulation.
_Avoid_: cleanup profile, private target discovery, source-map mutation, MCP tool

**Household Cleanup Task**:
A first-class Runnable Task that consumes household world evidence and combines
it with manipulation capability requirements to tidy movable objects.
_Avoid_: source-map builder, semantic-map owner, capability profile

**Household World Capability Profile**:
The reusable world-understanding profile. It includes map projection, fixture
semantics, bounded room/waypoint navigation, observations, camera adjustment,
visual candidate declarations, priors, and map update candidates.
_Avoid_: cleanup-only profile, manipulation profile, task recipe

**Skill Capability Requirements**:
The profiles, modules, required tools, optional tools, blocked capabilities,
scripts, and evidence gates an Agent Skill declares.
_Avoid_: backend variant name, implementation detail, hidden evaluator

**Observed Object Prior**:
A movable object observation loaded from an earlier runtime-map snapshot into a
later run. It is planning evidence and should be confirmed before action.
_Avoid_: static fixture, current-run confirmed handle, private generated mess

**Map Update Candidate**:
A public-evidence-backed proposed update to static map semantics, usually for a
large fixture or semi-static object.
_Avoid_: automatic source-map mutation, small movable cleanup object

**Semantic Sweep Mode**:
An internal no-cleanup-action execution mode behind `semantic-map-build`. It
uses the same online Runtime Metric Map update path while disabling
manipulation.
_Avoid_: separate map architecture, private target discovery, cleanup execution

**Cleanup Worklist**:
A public, run-local list derived from current observations and priors. It
tracks cleanup candidates and actionability state.
_Avoid_: private target list, static map semantics, evaluator manifest

## Perception And Grounding Vocabulary

**Model-Declared Observation**:
A public observed handle created from camera evidence by the main agent or a
camera inference producer.
_Avoid_: simulator oracle, private target, ungrounded local note

**Camera Inference Producer**:
A model, detector, visual-grounding service, or main agent path that proposes
public observations from camera evidence.
_Avoid_: capability tool, cleanup policy, private evaluator

**External Visual Grounding Service**:
A replaceable service boundary for camera-derived candidates. It may use a fake
producer, detector, refiner, or real VLM stack without changing the cleanup MCP
contract.
_Avoid_: cleanup runtime dependency, hidden fallback, private scorer

**Visual Grounding Failure Evidence**:
Visible producer failure evidence containing status, reason, timeout, and
latency. Failures should not fabricate simulator fallback labels.
_Avoid_: silent fallback, fake success, hidden retry

**Visual Grounding Evaluation Corpus**:
A perception-only benchmark set built from fixed camera frames, public context,
and private labels synchronized to the same scene state. For MolmoSpaces, it
should sample multiple scene indices rather than only replay one stored room.
_Avoid_: single-run artifact scrape, cleanup score, agent-facing dataset

**Private BBox Ground Truth**:
Hidden object-localization labels produced from simulator segmentation or manual
annotation for benchmark scoring. These labels may include object id, category,
visible pixels, and bounding boxes, but must not enter service requests, MCP
responses, or Agent View.
_Avoid_: public camera hint, detector output, synthetic placeholder bbox

**Candidate Cleanup Destination**:
A public destination hint for a detected object. It may guide cleanup but is not
private acceptable-destination truth.
_Avoid_: private evaluator answer, final scoring target

## Real Robot Vocabulary

**Real-Robot Deployment Target**:
A physical-robot acceptance target for a Runnable Task. It reuses the same
public task/profile/tool layers as simulation while backend variants report
physical provenance, safety gates, operator map context, and blocked
capabilities.
_Avoid_: simulator-only proof, robot-only task fork, hidden manual intervention

**Navigation + Perception Pilot**:
An early physical-robot deployment milestone that proves public navigation goals
and robot-local observations without claiming physical manipulation.
_Avoid_: full cleanup deployment, physical manipulation proof

**Simulator/Hardware Contract Parity**:
The expectation that simulator and physical runs share public task/profile/tool
shape while reports distinguish backend variant, provenance, and blocked
capabilities.
_Avoid_: simulator proof as hardware proof, robot-specific tool namespace

**Operator-Recorded Waypoint**:
A named robot pose prepared by an operator before a run.
_Avoid_: agent-created map edit, arbitrary coordinate goal

**PNC-Verified Waypoint**:
An operator-recorded waypoint with current reachability evidence from the robot
navigation stack.
_Avoid_: merely recorded waypoint, private route plan

**Operator Localization Gate**:
The operator-owned preparation gate for map selection, relocalization, and
localization readiness before robot navigation.
_Avoid_: agent-facing relocalization tool, automatic map switch

**Operator Run Enablement Gate**:
The run-level safety gate before autonomous agent navigation starts. It does
not enable manipulation.
_Avoid_: per-action approval loop, manipulation permission

**Human Takeover Stop**:
A terminal or paused safety state after physical navigation/local-motion failure
in an early pilot.
_Avoid_: hidden fallback, unverified exploration, silent retry

**Backend-Replaceable Navigation**:
A navigation capability whose public semantics remain stable while the backend
may be simulator, Nav2, Agibot GDK PNC, or another robot stack.
_Avoid_: backend-specific public tool names

## Placement And Manipulation Vocabulary

**Direct Support Placement**:
A placement result where the moved object is actually supported by the target
surface or receptacle.
_Avoid_: semantic-only assignment, nearest-receptacle label

**Nonblocking Placement Degradation**:
A reportable fallback where the run continues even though direct support was
not proven.
_Avoid_: claiming success, hiding placement weakness

**Blocked Capability**:
A structured response showing that a requested public capability is known but
not executable in the selected backend or safety state.
_Avoid_: pretending success, omitting unavailable tools from evidence

## Invariants

- Keep the public layers distinct:

  ```text
  Open-ended goal
    -> Runnable Task
    -> Agent Skill
    -> Capability Profile requirements
    -> MCP Capability Tools
    -> Backend Variant
  ```

- Runnable Tasks own command names, parameters, reports, and acceptance gates.
- Agent Skills own prompt strategy, loops, scripts, examples, recovery, and
  trace-preserving composition.
- Capability Profiles are reusable environments required by skills. Compose
  profiles by requirement; do not copy one profile into another task-specific
  profile.
- MCP tools expose bounded robot capabilities, not whole user tasks such as
  `cleanup_room()`.
- `semantic-map-build` is a Runnable Task, not a profile or MCP tool.
- `household-cleanup` is a Runnable Task and a consumer of household world
  evidence, not the owner of the semantic-map abstraction.
- `household_world_v1` should exclude manipulation tools such as `pick`,
  `place`, `open_receptacle`, and `close_receptacle`.
- Small movable cleanup objects belong in runtime observations/worklists, not
  static map semantics.
- Runtime observations and map update candidates must not silently mutate the
  source Navigation Map Artifact.
- Observed Object Priors should be confirmed in the current run before they
  become actionable cleanup handles.
- Private generated mess sets, acceptable destinations, hidden target lists,
  private manifests, and scorer truth must not enter public profile metadata,
  Agent View, skill prompts, or MCP responses.
- Physical robot runs should reuse the same public task/profile/tool shape as
  simulation and differ by backend variant, provenance, safety gates, and
  blocked-capability status.
- First physical pilots should prove navigation and observation before claiming
  manipulation readiness.

## Resolved Ambiguities

- **Task vs skill**: use Runnable Task for public run surfaces; use Agent Skill
  for reusable strategy.
- **Profile vs task**: profiles describe reusable capability environments, not
  task identity.
- **Composition vs copy**: tasks and skills require multiple profiles/modules;
  profiles should not duplicate another profile's tools just to form a bundle.
- **Metric map source vs runtime map**: Navigation Map Artifact is the source;
  Metric Map Projection is the public static view; Runtime Metric Map is the
  current-run enriched view.
- **Semantic map build vs cleanup**: semantic-map-build creates world evidence;
  cleanup consumes it.
- **Simulator vs hardware proof**: simulator or dry-run evidence is useful, but
  it is not physical execution proof.
- **Nav2 vs Agibot**: Nav2 and Agibot are backend variants/provenance choices
  when public tool shape remains stable.
- **Recorded vs verified waypoint**: an operator-recorded waypoint is not
  hardware readiness until current reachability evidence exists.
- **Run enablement vs per-action approval**: early robot runs need a run-level
  enablement gate; normal allowed navigation actions should not require hidden
  per-action approval loops.
- **Destination hint vs private target**: public destination hints may guide
  cleanup, but private acceptable-destination truth remains evaluator-only.
- **Placement success**: semantic assignment is not direct physical support.
  Report degraded placement separately.

## Pointers

- Human architecture: `ARCHITECTURE.md`
- Skill/profile design: `docs/human/mcp-skills-and-semantic-profiles.md`
- Current focus: `STATUS.md`
- Auto semantic map build plan: `docs/plans/auto-semantic-map-build.md`
- Visual grounding plan/status: `docs/plans/molmospaces-http-visual-grounding-service.md`,
  `docs/status/active/molmospaces-http-visual-grounding-service.md`
- Agibot and physical robot details: `docs/plans/agibot-g2-cleanup-support-pilot.md`,
  `docs/plans/molmospaces-agibot-contract-rehearsal.md`,
  `docs/status/active/real-robot-nav2-cleanup-pilot.md`
