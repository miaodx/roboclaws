# Roboclaws Domain Context

This file defines stable domain language. It is not project status. For current
focus, next action, and active source links, read [`STATUS.md`](../../STATUS.md).

Keep this file short. Historical phase vocabulary and shipped implementation
details belong in `.planning/`, `docs/adr/`, and `docs/retrospectives/`.

## Core Language

**Scenario Setup**:
A private pre-run world initialization choice that prepares the room before a
task starts. It can be `baseline` or a relocation setup, and it is independent
of task intent and evaluation policy.
_Avoid_: task intent, cleanup scenario, Agent View context

**Relocation Policy**:
A Scenario Setup mode that moves eligible loose or cleanup-related objects before
the run starts. The Cleanup Agent is not told the policy, object IDs, or
before/after locations.
_Avoid_: public mess generator, cleanup worklist, private scoring truth

**Relocation Count**:
The operator-facing number of objects that a relocation setup may move.
_Avoid_: generated mess count, public target count

**Cleanup Agent**:
The robot or policy that perceives the messy scene and decides how to restore it.
_Avoid_: Placer

**Scorer**:
A private evaluator that compares the final scene state against acceptable
cleanup outcomes.
_Avoid_: Planner, oracle planner

**Private Scoring Truth**:
Hidden object-to-acceptable-destination rules used only by the Scorer.
_Avoid_: Public target map, planner hints

**Generated Mess Set**:
The hidden private/scorer-side set of movable objects displaced by relocation
for one cleanup evaluation run.
_Avoid_: Five curated targets

**Tidy-Plausible Outcome**:
A final object placement that a reasonable household cleanup could accept, even
when more than one destination is valid.
_Avoid_: Single correct target

**Disturbance Penalty**:
A soft scoring penalty for making an initially tidy object less tidy-plausible.
_Avoid_: False-positive failure

**Metric Map**:
A public map of rooms, walls, doors, driveable ways, and robot pose.
_Avoid_: Semantic object oracle

**Prebuilt Robot Map Bundle**:
A static operator-prepared map package containing navigation geometry, frame
metadata, fixture semantics, and inspection waypoints.
_Avoid_: Live SLAM result, hidden target map

**Runtime Metric Map**:
A public run artifact that enriches the Metric Map with observed-object priors,
public semantic anchors, map-update candidates, and provenance without mutating
the source navigation map.
_Avoid_: Private target map, source map rewrite

**Actionable Semantic Map Snapshot**:
The canonical downstream semantic-map artifact. Online
`surface=household-world intent=map-build` Runtime Metric Map output and
offline Agibot `navigation_memory.json` conversion both produce this shape:
source map reference, runtime map payload, public anchors, materialized
inspection waypoints, materialized fixture or receptacle candidates,
actionability status, and evidence.
_Avoid_: Agibot-only cleanup input, private scoring artifact

**Public Semantic Anchor**:
A public semantic place, fixture, room area, landmark, or observed prior with
provenance and actionability status. Static fixtures and receptacles may become
tool-consumable targets; movable-object priors remain `needs_confirm` until
current-run evidence observes them again.
_Avoid_: global object inventory, scorer target

**Inspection Waypoint**:
A public Metric Map pose where the Cleanup Agent can observe part of a room
during a cleanup sweep.
_Avoid_: Hidden object viewpoint

**Room-Level Fixture Hint**:
A public hint that names a large fixed receptacle or fixture and the room where
it belongs, without giving an exact pose.
_Avoid_: Oracle fixture map

**Observed Object Handle**:
A stable object identifier exposed to the Cleanup Agent only after the object
appears in robot-local perception.
_Avoid_: Pre-run object id

**Support Estimate**:
A robot-local perception estimate of what fixture or surface an observed object
is on or near.
_Avoid_: Ground-truth object location

**Agent View**:
The exact public information and perception data available to the Cleanup Agent
during the run.
_Avoid_: Full report context

**Private Evaluation**:
The post-run report section that explains scoring using hidden mess and
acceptable-destination data.
_Avoid_: Agent input

**Cleanup Artifact Report**:
The shared HTML review artifact for MolmoSpaces cleanup demos, backed by one
report renderer and one semantic timeline model.
_Avoid_: Per-demo report clone

**Semantic Cleanup Subphase**:
A report-facing label for one step in the object cleanup loop:
`nav`, `pick`, `nav`, optional `open`, then `place`.
_Avoid_: Raw tool log as visual flow

**Planner-Backed Manipulation Proof**:
Evidence that a MolmoSpaces robot manipulation planner policy actually executed
robot actions and changed robot state, separate from semantic state edits.
_Avoid_: planner class import, `api_semantic` success

**Planner-Backed Cleanup Primitive Gate**:
A per-cleanup-subphase evidence gate that checks whether the cleanup loop's own
`nav`, `pick`, `nav`, `open`, or `place` steps are planner-backed.
_Avoid_: report-only proof attachment

**RBY1M CuRobo Runtime Gate**:
Evidence that the target RBY1M/CuRobo runtime is ready for strict cleanup
primitive proof.
_Avoid_: standalone Franka proof as target cleanup readiness

**Planner Proof Request Manifest**:
Private cleanup artifact metadata that turns completed semantic substeps into
exact bound planner probe requests for local proof-bundle generation.
_Avoid_: Agent View planner aliases

**Planner Proof Bundle Runner Report**:
The visual report produced by the local proof-bundle runner to show probe
commands, proof artifacts, blockers, and optional cleanup rerun commands.
_Avoid_: treating command evidence as proof success

**Grasp-Feasibility Blocker**:
A proof-result classification for exact-scene requests that clear robot
placement but fail through post-placement grasp/candidate rejection.
_Avoid_: generic task-feasibility blocker

**Grasp Cache Evidence**:
Evidence about rigid grasp-cache availability, validity, generation, and
installation for exact planner objects.
_Avoid_: assuming object assets imply usable cached grasps

## Relationships

- **Scenario Setup** prepares the room before the **Cleanup Agent** starts.
- A **Cleanup Agent** must not receive the **Private Scoring Truth**, hidden
  relocated-object list, or target count.
- A **Scorer** may use the **Private Scoring Truth** only after the run ends.
- A **Cleanup Agent** may receive public map, fixture, and robot-local
  perception data.
- A **Prebuilt Robot Map Bundle** may back the public **Metric Map** and
  fixture semantics before runtime observations begin.
- A **Runtime Metric Map** may be wrapped as an **Actionable Semantic Map
  Snapshot** for downstream cleanup or open household tasks.
- Offline Agibot `navigation_memory.json` conversion produces an
  **Actionable Semantic Map Snapshot** at the map-artifact boundary; cleanup
  should consume the canonical snapshot, not a special Agibot-only branch.
- Small movable objects should be discovered through **Observed Object
  Handles**, not pre-run global object IDs.
- Prior movable objects in an **Actionable Semantic Map Snapshot** are
  non-actionable until current-run evidence confirms them.
- Reports must separate **Agent View** from **Private Evaluation**.
- `api_semantic` cleanup artifacts can be useful evidence, but they must not
  satisfy **Planner-Backed Manipulation Proof**.
- The cleanup visual rhythm is `nav -> pick -> nav -> open? -> place`.
- **Planner-Backed Cleanup Primitive Gate** remains blocked until cleanup
  subphases have exact planner-backed primitive evidence.
