# Roboclaws Context

This file is the durable vocabulary and boundary map for Roboclaws. It should
stay short. Put implementation plans in `docs/plans/`, current status in
`STATUS.md`, detailed human architecture in `ARCHITECTURE.md` and
`docs/human/**`, and run evidence in `docs/status/active/`, retrospectives, or
`output/`.

## Maintenance Contract

Maintain this as a compact context primer, not a planning log. Keep it under
about 350 lines and 18KB; if it approaches 400 lines or 25KB, reduce or split.
Add only durable vocabulary, boundaries, task/skill/profile layering, safety
gates, or real-robot proof claims; never progress notes, command logs, run
results, benchmark detail, or historical transcripts. Prefer merging terms over
adding near-duplicates, keep detailed material in `docs/human/**`,
`docs/plans/**`, `docs/status/active/**`, or `docs/adr/**`, and rerun a
saturation audit after glossary updates.

## Current Architecture Vocabulary

**Task Prompt**:
A user instruction describing desired robot work in open-ended language.
_Avoid_: task API, recipe, benchmark name

**Runnable Surface And Intent**:
A public run-catalog selection such as `surface=household-world
intent=map-build`, `surface=household-world intent=cleanup`, or
`surface=ai2thor-world intent=navigate`. It owns command parameters, report
shape, and acceptance gates.
_Avoid_: Agent Skill, Capability Profile, backend script, hidden evaluator

**Launch World / Scene**:
The operator-facing room, map, site, or digital-twin scene where a runnable
surface and intent execute, such as a MolmoSpaces room, B1 Map 12, an Agibot
map, or a Gaussian scene.
_Avoid_: backend runtime, task intent, agent engine, provider profile

**Launch Backend**:
The runtime used to execute or render a Launch World / Scene, such as MuJoCo,
Isaac Lab, Agibot GDK, or a future independent Gaussian runtime. Gaussian
content that currently runs through Isaac should be modeled as a world/scene
source with `backend=isaaclab`, not as a separate Gaussian backend.
_Avoid_: task intent, world id, provider profile

**Agent Engine**:
The operator-facing control engine that drives the run, such as Codex CLI,
Claude Code, OpenAI Agents SDK, or a direct deterministic runner.
_Avoid_: model provider, evidence lane, backend variant

**Provider Profile**:
The model/provider route used by an Agent Engine, such as `codex-env`, `mify`,
`kimi-anthropic`, or `mimo-anthropic`. It applies to live model-backed engines;
deterministic direct runners do not require one.
_Avoid_: agent engine, task intent, evidence lane

**Internal Runner Class**:
The derived execution category behind a launch, such as `live-agent`,
`deterministic`, `smoke`, `gateway`, or `script`. It is catalog/runtime
metadata, not an operator-facing public choice. Smoke is an evidence or runner
mode, not an Agent Engine.
_Avoid_: public task name, provider profile, capability profile, UI selector

**Agent Skill**:
A reusable package of model operating knowledge, scripts, heuristics, examples,
and checks that attempts goals by calling available tools.
_Avoid_: robot capability claim, MCP contract, backend primitive

**Agent Validation Matrix**:
An agent-facing verification skill that selects and optionally executes the
relevant deterministic, product, live-agent, Agent SDK, perception, simulator,
or hardware gates for a plan or diff. It records why gates were selected,
skipped, run, or blocked. It is not an MCP capability, task skill, or fixed
benchmark grid.
_Avoid_: manual checklist, hidden evaluator, one-size-fits-all harness

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
`molmospaces_subprocess`, `api_semantic_synthetic`, `agibot_g2`, `ros2_nav2`,
or the backend-specific primitives behind them.
_Avoid_: new public task, new profile name, agent-facing tool namespace

## Household World And Cleanup Vocabulary

**Scenario Setup**:
A private pre-run world initialization choice that prepares the selected world
before a task starts. Public launch routes expose `scenario_setup=baseline` or a
relocation setup; reports may record setup provenance, but Agent View must not.
_Avoid_: task intent, cleanup scenario, agent-facing context

**Relocation Policy**:
A Scenario Setup mode that moves eligible loose or cleanup-related objects before
the run starts. The policy, object IDs, before/after locations, and relocation
count stay private/report-side.
_Avoid_: public mess generator, cleanup worklist, private scoring truth

**Navigation Map Artifact**:
A reusable static source of navigation geometry and public semantic annotations.
Rich variants may include rooms, fixtures, inspection waypoints, and driveable
links; minimal variants may contain only occupancy/free-space geometry, current
pose, frame metadata, and safety bounds.
_Avoid_: runtime observation memory, private scene graph, raw hidden truth

**Minimal Navigation Map Artifact**:
An intentionally sparse Navigation Map Artifact aligned with raw robot maps:
occupancy/free-space geometry plus localization and safety context, without
preauthored room, fixture, or object semantics. It is the preferred real-robot
starting point; rich authored bundles are dev/test or explicit aids.
_Avoid_: complete semantic map, arbitrary coordinate freedom, private scene graph

**Metric Map Projection**:
The agent-facing JSON view derived from a Navigation Map Artifact. For minimal
maps, it may expose sparse navigation geometry and generated exploration
candidates instead of authored rooms, fixtures, or inspection waypoints.
_Avoid_: raw occupancy map, independent map source, private backend metadata

**Runtime Metric Map**:
The current-run Metric Map Projection after public runtime evidence is added:
observed object handles, loaded priors, generated waypoint/area evidence, room
or fixture candidates, public semantic anchors, and map update candidates.
_Avoid_: source map artifact, hidden mutable global map, private target truth

**Public Semantic Anchor**:
A public-evidence-backed fixed or semi-static place the robot can reason about:
room area, surface, receptacle, fixture, or observation waypoint, with stable id,
label/category, pose or waypoint link, affordances, provenance, and confidence.
Semantic-map-build may create these anchors from observations over a minimal
source map; cleanup may use fixture/receptacle anchors as destination hints.
_Avoid_: small movable object, private acceptable destination, unreviewed source-map mutation

**Target Candidate**:
A public result for an open-ended target query such as "find the fridge" or
"find the speaker." It wraps a Public Semantic Anchor, observed prior, or
current observation match with query match evidence, confidence,
source_observation_id when available, nearest public waypoint or generated
inspection candidate, and Target Actionability Status.
_Avoid_: raw fixture id guess, private object inventory, agent-created coordinate

**Target Actionability Status**:
The public state that tells an agent or skill what can safely happen next for a
Target Candidate: `query_unmatched`, `visible_only`, `anchor_unbound`,
`unreachable`, `needs_observe`, or `actionable`. Checkers and reports should use
these states instead of collapsing target-search outcomes into generic missing
observations.
_Avoid_: report-only wording, hidden reachability decision, private target truth

**Map-Build Intent**:
A first-class household-world intent that navigates and observes to produce a
Runtime Metric Map snapshot for later robot tasks. It selects a map-building
skill, requires household world capabilities, and disables manipulation. In the
minimal-map mainline, it turns sparse maps into cleanup-usable public evidence.
_Avoid_: cleanup profile, private target discovery, source-map mutation, MCP tool

**Cleanup Intent**:
A first-class household-world intent that consumes household world evidence and
combines it with manipulation capability requirements to tidy movable objects.
It may use current fixture/receptacle anchors as destination hints; older
movable-object priors need current-run confirmation before pick/place.
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
_Avoid_: static fixture, current-run confirmed handle, private relocation truth

**RAW-FPV Semantic Context**:
Public Runtime Metric Map or semantic-map prior context supplied to a
`camera-raw-fpv` cleanup run to guide search priorities, likely categories, or
where to observe next. It does not create executable observed-object handles;
cleanup eligibility still requires current-frame raw-FPV confirmation from the
acting model.
_Avoid_: assisted lane, current-frame detector candidates, prior-as-action

**Map Update Candidate**:
A public-evidence-backed proposed update to static map semantics, usually for a
large fixture or semi-static object. It may be useful in the current Runtime
Metric Map before a later review workflow writes source-map semantics.
_Avoid_: automatic source-map mutation, small movable cleanup object

**Generated Exploration Candidate**:
A planner-generated safe navigation or observation candidate derived from public
free space, safety bounds, and pose. First project candidates as generated
waypoints for `navigate_to_waypoint`; add a tool only if later evidence shows
waypoint projection is unclear. Physical execution still needs robot gates.
_Avoid_: agent-created arbitrary coordinate goal, hidden route plan

**Generated Target Inspection Candidate**:
A runtime generated waypoint or standoff pose proposed to inspect or bind a
Target Candidate. It must be produced or verified by the server/backend/operator
navigation layer before becoming executable through public waypoint navigation.
_Avoid_: agent-invented coordinates, unverified standoff pose, hidden route plan

**Semantic Sweep Mode**:
An internal no-cleanup-action execution mode behind `intent=map-build`. It uses
the same online Runtime Metric Map update path while disabling manipulation.
_Avoid_: separate map architecture, private target discovery, cleanup execution

**Cleanup Worklist**:
A public, run-local list derived from current observations and priors. It
tracks cleanup candidates and actionability state.
_Avoid_: private target list, static map semantics, evaluator manifest

**Done Readiness Gate**:
A contract/runtime policy that decides whether a `done` call may finalize a
run. It may block completion with public recovery blockers derived from Agent
View, public tool traces, public worklists, and run acceptance configuration,
but it must not expose private generated mess sets, acceptable destinations,
hidden target lists, private manifests, or scorer truth.
_Avoid_: skill scratchpad authority, private target-count leak, new cleanup task tool

## Perception And Grounding Vocabulary

**Model-Declared Observation**:
A public observed handle created from camera evidence by the main agent or a
camera inference producer.
_Avoid_: simulator oracle, private target, ungrounded local note

**Reviewable Image Locality**:
Structured image-local evidence attached to a current observation, such as a
bbox, point, or normalized coarse region, that lets reviewers and contracts bind
a model-declared cleanup candidate to the raw FPV frame. JSON structure remains
required; detector-grade bbox precision is not assumed for raw-FPV model output.
_Avoid_: freeform prose only, stale prior location, private target match

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

**Candidate Cleanup Destination**:
A public destination hint for a detected object. It may guide cleanup but is not
private acceptable-destination truth.
_Avoid_: private evaluator answer, final scoring target

## Real Robot Vocabulary

**Real-Robot Deployment Target**:
A physical-robot acceptance target for a Runnable Surface And Intent. It reuses
the same public intent/profile/tool layers as simulation while backend variants
report physical provenance, safety gates, operator map context, and blocked
capabilities.
_Avoid_: simulator-only proof, robot-only task fork, hidden manual intervention

**Navigation + Perception Pilot**:
An early physical-robot deployment milestone that proves public navigation goals
and robot-local observations without claiming physical manipulation.
_Avoid_: full cleanup deployment, physical manipulation proof

**G2 Map-Build Pilot**:
The first Agibot G2 hardware target for household world work: a Codex-driven
agent loop over verified waypoint navigation, `head_color` observations, visual
grounding, and Runtime Metric Map output. Cleanup actions and physical
manipulation remain disabled or blocked.
_Avoid_: cleanup execution, object navigation, physical pick/place proof

**Simulator/Hardware Contract Parity**:
The expectation that simulator and physical runs share public
surface/intent/profile/tool shape while reports distinguish backend variant,
provenance, and blocked capabilities.
_Avoid_: simulator proof as hardware proof, robot-specific tool namespace

**Operator-Recorded Waypoint**:
A named robot pose prepared by an operator before a run.
_Avoid_: agent-created map edit, arbitrary coordinate goal

**PNC-Verified Waypoint**:
A public waypoint or generated exploration candidate with current reachability
evidence from the robot navigation stack.
_Avoid_: merely recorded coordinates, private route plan

**Operator Localization Gate**:
The operator-owned preparation gate for map selection, relocalization, and
localization readiness before robot navigation.
_Avoid_: agent-facing relocalization tool, automatic map switch

**Operator Run Enablement Gate**:
The run-level safety gate before autonomous agent navigation starts. After this
gate, Codex controls task-level tool choice over the approved capability surface
while the robot stack and human operator provide safety stops. It does not
enable manipulation.
_Avoid_: per-action approval loop, manipulation permission, human task planning

**Human Takeover Stop**:
A terminal or paused safety state after physical navigation/local-motion
failure, robot obstacle-stop, or human emergency stop in an early pilot.
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
    -> Runnable Surface And Intent
    -> Agent Skill
    -> Capability Profile requirements
    -> MCP Capability Tools
    -> Backend Variant
  ```

- Runnable Surfaces And Intents own command parameters, reports, and acceptance
  gates; Agent Skills own strategy, recovery, scripts, examples, and
  trace-preserving composition; Capability Profiles are reusable environments
  required by skills.
- MCP tools expose bounded robot capabilities, not whole user tasks such as
  `cleanup_room()`. `surface=household-world intent=map-build` creates world
  evidence; `surface=household-world intent=cleanup` consumes household world
  evidence and does not own mapping.
- `household_world_v1` should exclude manipulation tools such as `pick`,
  `place`, `open_receptacle`, and `close_receptacle`.
- Small movable cleanup objects belong in runtime observations/worklists, not
  static map semantics.
- Minimal-map simulator runs should not receive richer public semantics than
  the equivalent physical robot map path would provide.
- Generated exploration candidates may seed map-build sweeps, but they
  are not source-map semantics and are not direct permission for arbitrary robot
  motion.
- Runtime observations and map update candidates must not silently mutate the
  source Navigation Map Artifact. Observed Object Priors need current-run
  confirmation before becoming actionable cleanup handles.
- Open-ended target search should return Target Candidates and public anchor or
  waypoint ids, not raw fixture ids. A stale raw fixture-id guess should recover
  through public target-query resolution, search, or observation.
- Target search may create Generated Target Inspection Candidates only through
  backend/operator-verified public waypoint or standoff generation. Agents must
  not invent map coordinates.
- Private relocation/generated mess sets, acceptable destinations, hidden target lists,
  private manifests, and scorer truth must not enter public profile metadata,
  Agent View, skill prompts, or MCP responses.
- `done` may return public readiness blockers and required next tools, but those
  blockers must be derived from public traces/worklists and must not disclose
  private target membership, hidden acceptable destinations, or private scorer
  truth.
- Physical robot runs should reuse the same public surface/intent/profile/tool
  shape as simulation and differ by backend variant, provenance, safety gates,
  and blocked-capability status.
- First physical pilots should prove navigation and observation before claiming
  manipulation readiness.
- The first Agibot G2 map-build pilot should accept only waypoint-level
  navigation, robot-local observation, bounded camera control when proven,
  visual-candidate declaration, and `done`; object/receptacle navigation and
  manipulation remain blocked until a later gate.
- For G2 readiness, `camera-labels` with real Grounding DINO-style external
  visual grounding is the primary perception lane, while `camera-raw` is a
  comparison or fallback lane. `world-labels` and `visual_grounding=sim` are
  simulator/control evidence, not G2 readiness evidence.
- A G2 Runtime Metric Map snapshot may seed a later online run only as
  Observed Object Priors; current G2 camera evidence must confirm priors before
  they become actionable.

## Resolved Ambiguities

- **Surface/intent/skill/profile**: use Runnable Surface And Intent for public
  run contracts, Agent Skill for reusable strategy, and Capability Profile for
  reusable environments.
  Compose profiles by requirement; do not copy one into a task-specific bundle.
- **Metric map source vs runtime map**: Navigation Map Artifact is the source;
  Metric Map Projection is the public static view; Runtime Metric Map is the
  current-run enriched view.
- **Rich vs minimal maps**: rich map bundles may contain authored public
  semantics; minimal map artifacts intentionally start near raw occupancy maps
  so online/offline map-build can enrich them through public evidence.
  The real-robot mainline starts from minimal maps, not rich authored semantics.
- **Map build vs cleanup**: `intent=map-build` creates world evidence;
  `intent=cleanup` consumes it. Simulator or dry-run evidence is useful, but it
  is not physical execution proof.
- **Anchors vs priors**: fixture/receptacle Public Semantic Anchors in a
  current Runtime Metric Map can guide cleanup destinations; older movable
  priors must be confirmed by current camera evidence before manipulation.
- **Target search vs navigation target**: semantic labels, visual matches, and
  Target Candidates are not executable navigation targets until they resolve to
  a public anchor, observed handle, or backend-verified waypoint/standoff with
  actionable status.
- **Search reuse in cleanup**: cleanup may reuse target search for discovering
  receptacles, surfaces, fixtures, and inspection areas, but movable-object
  manipulation still requires a current Observed Object Handle.
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
- **G2 first run vs cleanup**: the first G2 run is a map-build/navigation +
  perception pilot. It may produce runtime-map evidence for later cleanup, but
  it does not authorize object navigation or manipulation.

## Pointers

- Architecture/current focus: `ARCHITECTURE.md`, `STATUS.md`
- Skill/profile design: `docs/human/mcp-skills-and-semantic-profiles.md`
- Map/perception plans: `docs/plans/auto-semantic-map-build.md`,
  `docs/plans/molmospaces-http-visual-grounding-service.md`
- Agibot/physical details: `docs/plans/agibot-g2-cleanup-support-pilot.md`,
  `docs/plans/molmospaces-agibot-contract-rehearsal.md`,
  `docs/status/active/real-robot-nav2-cleanup-pilot.md`
