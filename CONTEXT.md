# Roboclaws Domain Context

Roboclaws is a robotics demo context where simulated robots perceive, navigate,
and manipulate household scenes while producing reviewable artifacts.

## Language

**Mess Generator**:
A pre-run process that creates the disorder the robot will later try to clean up.
_Avoid_: Misplacer, placer setup

**Cleanup Agent**:
The robot or policy that perceives the messy scene and decides how to restore it.
_Avoid_: Placer

**Scorer**:
A private evaluator that compares the final scene state against acceptable cleanup outcomes.
_Avoid_: Planner, oracle planner

**Private Scoring Truth**:
The hidden object-to-acceptable-destination rules used only by the Scorer.
_Avoid_: Public target map, planner hints

**Room-Level Fixture Hint**:
A public hint that names a large fixed receptacle or fixture and the room where it belongs, without giving an exact pose.
_Avoid_: Oracle fixture map

**Exact Fixture Position**:
A public fixture pose used as an easier fallback when room-level hints make cleanup too unreliable.
_Avoid_: Default landmark truth

**Cleanup Sweep**:
A bounded inspection-and-cleanup attempt where the Cleanup Agent searches for plausible misplaced objects without knowing the target list or target count.
_Avoid_: Fixed target run

**Tidy-Plausible Outcome**:
A final object placement that a reasonable household cleanup could accept, even when more than one destination is valid.
_Avoid_: Single correct target

**Scoring Policy**:
The Scorer's chosen method for judging a final scene, such as deterministic rules or a future model-assisted rubric.
_Avoid_: Hard-coded oracle

**Advisory LLM Scorer**:
A model-assisted review signal that can explain ambiguous cleanup quality but does not decide pass/fail.
_Avoid_: Authoritative judge

**Visible Object Detection**:
A public perception result listing small movable objects visible from the robot's current viewpoint.
_Avoid_: Global movable-object inventory

**Raw FPV Inference**:
A harder future perception mode where the Cleanup Agent must infer movable objects directly from camera pixels without explicit detections.
_Avoid_: v1 perception contract

**Raw FPV Observation**:
A public camera observation from the robot's first-person view, recorded without structured movable-object detections, categories, or support estimates.
_Avoid_: hidden object list in image form

**Metric Map**:
A public map of rooms, walls, doors, driveable ways, and robot pose.
_Avoid_: Semantic object oracle

**Agent-Built Semantic Map**:
The Cleanup Agent's working memory of objects and likely destinations learned from its own observations.
_Avoid_: Prebuilt movable-object map

**Generated Mess Set**:
The hidden set of movable objects displaced by the Mess Generator for one cleanup run.
_Avoid_: Five curated targets

**Disturbance Penalty**:
A soft scoring penalty for making an initially tidy object less tidy-plausible.
_Avoid_: False-positive failure

**Map-Guided Semantic Navigation**:
A movement primitive where the Cleanup Agent chooses a room or waypoint from the Metric Map and the simulator updates the robot pose without proving collision-free motion planning.
_Avoid_: Planner-backed navigation

**Visible Objects**:
The robot-local movable-object detections available from the current observation context.
_Avoid_: `scene_objects` for global movable-object dumps

**Public Fixture ID**:
A stable identifier for a large fixed receptacle or fixture that the Cleanup Agent may know globally.
_Avoid_: Hidden receptacle id

**Inferred Destination**:
A cleanup destination chosen by the Cleanup Agent from object category, fixture hints, task intent, and observations.
_Avoid_: Public destination rule

**Deterministic Sweep Baseline**:
A non-model cleanup policy used to prove the mess, perception, navigation, and scoring contract before evaluating coding-agent or OpenClaw behavior.
_Avoid_: Production policy

**Sweep Coverage**:
The rooms or inspection waypoints observed by the Cleanup Agent during a Cleanup Sweep.
_Avoid_: Target-count completion

**Observed Object Handle**:
A stable object identifier exposed to the Cleanup Agent only after the object appears in robot-local perception.
_Avoid_: Pre-run object id

**Support Estimate**:
A robot-local perception estimate of what fixture or surface an observed object is on or near.
_Avoid_: Ground-truth object location

**Fixture Affordance**:
A public action capability of a large fixed fixture, such as `open`, `place`, or `place_inside`.
_Avoid_: Hidden target rule

**Inspection Waypoint**:
A public Metric Map pose where the Cleanup Agent can observe part of a room during a Cleanup Sweep.
_Avoid_: Hidden object viewpoint

**Agent View**:
The exact public information and perception data available to the Cleanup Agent during the run.
_Avoid_: Full report context

**Private Evaluation**:
The post-run report section that explains scoring using hidden mess and acceptable-destination data.
_Avoid_: Agent input

**Mess Restoration Rate**:
The fraction of the Generated Mess Set ending in tidy-plausible locations.
_Avoid_: Restored count only

**Sweep Coverage Rate**:
The fraction of public Inspection Waypoints observed during a Cleanup Sweep.
_Avoid_: Claimed confidence

**MolmoSpaces Real-World-Style Cleanup Harness**:
The next cleanup harness that hides the Generated Mess Set, uses public map/perception inputs, and scores tidy-plausible outcomes.
_Avoid_: Real robot cleanup

**MolmoSpaces Current-Contract Agent Bridge**:
A transitional harness that exposes the existing curated Molmo cleanup contract to coding-agent and OpenClaw policies before the stricter real-world-style contract is implemented.
_Avoid_: Real-world-style cleanup harness

**Molmo Cleanup MCP Server**:
A Molmo-specific FastMCP server that exposes cleanup tools by wrapping the Molmo cleanup contract.
_Avoid_: AI2-THOR navigation MCP extension

**Agent-Driven Cleanup Run**:
A cleanup run where an external coding agent or OpenClaw policy chooses the cleanup tool sequence.
_Avoid_: Heuristic replay

**Molmo Cleanup Skill**:
The external-agent instruction file that teaches a coding agent or OpenClaw policy how to use Molmo cleanup MCP tools.
_Avoid_: Heuristic prompt

**Agent Dogfood Loop**:
An iteration cycle where a real coding agent attempts the task and the MCP tool descriptions plus skill instructions are refined from observed failures.
_Avoid_: One-pass prompt writing

**Clean Agent Cleanup Run**:
An Agent-Driven Cleanup Run that succeeds without stale references, premature termination, skipped semantic completion checks, private-truth use, or manual intervention.
_Avoid_: Accidental success

**Cleanup Artifact Report**:
The shared HTML review artifact for MolmoSpaces cleanup demos, backed by one report renderer and one semantic timeline model.
_Avoid_: Per-demo report clone

**Semantic Cleanup Subphase**:
A report-facing label for one step in the object cleanup loop: `nav`, `pick`, `nav`, optional `open`, then `place`.
_Avoid_: Raw tool log as visual flow

**Planner-Backed Manipulation Proof**:
Evidence that a MolmoSpaces robot manipulation planner policy actually executed
robot actions and changed robot state, separate from semantic state edits.
_Avoid_: planner class import, `api_semantic` success

**Headless Planner Renderer Adapter**:
A probe-local workaround that makes MolmoSpaces planner execution use a
headless EGL renderer device without editing the upstream MolmoSpaces checkout.
_Avoid_: general renderer abstraction

## Relationships

- A **Mess Generator** creates a messy scene before the **Cleanup Agent** starts.
- A **Cleanup Agent** must not receive the **Private Scoring Truth**.
- A **Cleanup Agent** must not receive the hidden misplaced-object list or target count.
- A **Scorer** may use the **Private Scoring Truth** after the run ends.
- A **Scorer** judges **Tidy-Plausible Outcomes**, not only single correct destinations.
- A **Scoring Policy** should be replaceable without changing what the **Cleanup Agent** is allowed to know.
- A deterministic **Scoring Policy** is authoritative for v1; an **Advisory LLM Scorer** may be reported but must not decide pass/fail yet.
- An **Advisory LLM Scorer** should be a post-run artifact, not Cleanup Agent input.
- A **Cleanup Agent** may receive public map, landmark, and perception data.
- A **Cleanup Agent** may receive a **Metric Map** before or during the run.
- A **Cleanup Agent** must build any small-object **Agent-Built Semantic Map** from local observations.
- **Map-Guided Semantic Navigation** is acceptable for v1 when the goal is decision and search realism.
- A **Visible Object Detection** may be returned from robot-local perception in v1.
- A **Visible Object Detection** must not become a global list of all movable objects in the scene.
- A **Visible Object Detection** may include an **Observed Object Handle**, category, display name, current room, current surface or nearby fixture, confidence, and image bounding box.
- A **Support Estimate** should include relation, fixture or surface id when available, confidence, and perception source.
- A **Visible Object Detection** must not include `is_misplaced`, target receptacles, or acceptable destination rules.
- **Visible Objects** are the preferred v1 tool-contract concept for small movable objects.
- An **Inferred Destination** belongs to the **Cleanup Agent**, while acceptable destination sets belong to the **Scorer**.
- **Raw FPV Inference** is a future extension, not the first real-world-style cleanup contract.
- A **Room-Level Fixture Hint** is the default public landmark aid for the **Cleanup Agent**.
- A **Public Fixture ID** may be globally visible when paired with a **Room-Level Fixture Hint**.
- A **Room-Level Fixture Hint** may include fixture id, category, room label, and **Fixture Affordances**.
- An **Exact Fixture Position** is a fallback aid, not the default cleanup contract.
- An **Exact Fixture Position** should be enabled only through an explicit easier harness mode.
- A **Cleanup Sweep** ends when the **Cleanup Agent** decides no more plausible cleanup candidates remain or the step budget is exhausted.
- A good **Cleanup Sweep** requires enough **Sweep Coverage** to inspect all reachable rooms or required waypoints.
- A **Metric Map** should expose roughly 2-4 **Inspection Waypoints** per room in v1.
- A **Generated Mess Set** is hidden from the **Cleanup Agent** and should contain roughly 10-20 objects in v1.
- A **Scorer** evaluates the **Generated Mess Set** as a set, not only the first few selected objects.
- A **Scorer** may apply a **Disturbance Penalty** when the **Cleanup Agent** makes initially tidy objects worse.
- V1 pass/fail should combine **Mess Restoration Rate**, **Sweep Coverage Rate**, and **Disturbance Penalty**.
- A **Deterministic Sweep Baseline** should run before model-driven policies on the same public contract.
- A **Deterministic Sweep Baseline** must obey the same public information boundary as any model-driven **Cleanup Agent**.
- A report may show **Private Evaluation** only after the run, separated from the **Agent View**.
- A **Cleanup Artifact Report** should reuse the same report renderer across current-contract, ADR-0003, direct-agent, and OpenClaw dogfood runs.
- A **Cleanup Artifact Report** may omit Robot View Timeline only when no robot views were recorded.
- A **Cleanup Artifact Report** should display **Semantic Cleanup Subphases** as `nav -> pick -> nav -> open? -> place`, while raw trace artifacts keep full tool names.
- Real visual OpenClaw cleanup evidence should include Robot View Timeline with FPV, chase, map, and verification images from the MolmoSpaces/RBY1M backend.
- Clean OpenClaw cleanup evidence should enforce the semantic loop as executable MCP contract behavior, not prompt-only advice.
- Advisory scoring/model checks should render in the shared **Cleanup Artifact Report** without changing deterministic scoring fields.
- Raw FPV-only perception should be an explicit evidence mode on the ADR-0003 contract, not a replacement for the default visible-detection cleanup gate.
- A **Raw FPV Observation** may include waypoint, room, observation id, and image artifact references, but not structured movable-object detections or private scoring truth.
- **Planner-Backed Manipulation Proof** must require planner policy execution evidence, nonzero robot-state movement, and no `api_semantic` fallback.
- `api_semantic` cleanup artifacts may be useful cleanup evidence, but must not satisfy **Planner-Backed Manipulation Proof**.
- Planner runtime blockers should be reported as dependency/runtime diagnostics, not inferred from sparse shell failures.
- A **Headless Planner Renderer Adapter** may help reach planner execution in local probes, but it is not itself **Planner-Backed Manipulation Proof**.

## Example Dialogue

> **Dev:** "Can we give the Cleanup Agent the list of misplaced objects so it can finish faster?"
> **Domain expert:** "No. The Mess Generator can know that list, and the Scorer can use it later, but the Cleanup Agent must discover cleanup candidates from public scene information and robot perception."

## Flagged Ambiguities

- "Placer" was used to mean the cleanup-side robot, but the repo also has a `place` manipulation primitive. Resolved: use **Cleanup Agent** for the robot/policy.
- "Oracle" can mean setup truth, target hints, or scoring rules. Resolved: use **Private Scoring Truth** for hidden evaluator data, and keep it out of Cleanup Agent inputs.
- Large fixture hints can be room-level or exact-pose. Resolved: use **Room-Level Fixture Hint** by default; allow **Exact Fixture Position** only as a reliability fallback.
- The next cleanup scenario should hide both the misplaced-object list and the target count from the Cleanup Agent.
- Cleanup scoring should prefer **Tidy-Plausible Outcomes** and leave room for future model-assisted **Scoring Policies**.
- LLM scoring is allowed as advisory review evidence, but deterministic scoring remains authoritative for the first real-world-style cleanup harness.
- v1 Cleanup Agent perception may include robot-local **Visible Object Detections**; raw camera-only object inference is deliberately deferred.
- v1 may provide a **Metric Map** up front, but must not provide a prebuilt global semantic map of small movable objects.
- v1 should use a larger randomized **Generated Mess Set** of roughly 10-20 objects instead of the current five curated cleanup targets.
- v1 scoring should include a soft **Disturbance Penalty** for harmful false-positive cleanup moves.
- v1 should prioritize cleanup decision and search realism before planner-backed navigation or manipulation.
- The next cleanup harness should retire or restrict global movable-object `scene_objects` in favor of robot-local **Visible Objects**.
- v1 may expose global **Public Fixture IDs**, while small movable-object IDs should be discovered through local observation.
- v1 should not expose a public object-category-to-destination table to the Cleanup Agent.
- v1 should prove the randomized mess, perception contract, navigation contract, and scoring contract with a **Deterministic Sweep Baseline** before evaluating coding-agent or OpenClaw policy behavior.
- v1 should judge premature `done` calls against **Sweep Coverage**, not against a hidden target count.
- The next cleanup harness should first ship the real-world-style public/private contract, Mess Generator, Scorer, local perception, map-guided sweep, and deterministic baseline before model-policy work.
- **MolmoSpaces Real-World-Style Cleanup Harness** is the canonical name for the next cleanup phase.
- **MolmoSpaces Current-Contract Agent Bridge** may keep current-contract shortcuts only when reports label them explicitly.
- A **Molmo Cleanup MCP Server** should reuse MCP binding patterns from the AI2-THOR server without subclassing or extending the AI2-THOR navigation server.
- **MolmoSpaces Current-Contract Agent Bridge** should prove direct coding-agent MCP first, then OpenClaw Gateway against the same **Molmo Cleanup MCP Server**.
- An **Agent-Driven Cleanup Run** must let the external agent choose the cleanup sequence; deterministic public heuristics are baselines only.
- A **Molmo Cleanup Skill** should be developed together with the **Molmo Cleanup MCP Server**.
- An **Agent Dogfood Loop** should harden the **Molmo Cleanup Skill** and MCP tool descriptions before OpenClaw evaluation.
- A **Clean Agent Cleanup Run** may stop the **Agent Dogfood Loop** early.
- v1 should expose stable small-object IDs only as **Observed Object Handles** after local perception has seen the object.
- v1 should expose object support/location as **Support Estimates**, not perfect ground-truth object locations.
- v1 fixture hints should expose room-level fixture identity and **Fixture Affordances**, but no exact pose unless fallback mode is enabled.
- v1 **Sweep Coverage** should be measured against public **Inspection Waypoints**, not hidden object coverage.
- The **Deterministic Sweep Baseline** may use common-sense category heuristics, but must not use the **Generated Mess Set** or **Private Scoring Truth**.
- v1 reports should separate the **Agent View** from **Private Evaluation** so debugging artifacts do not imply leaked run-time knowledge.
- Default v1 success threshold: **Mess Restoration Rate** at least 70%, **Sweep Coverage Rate** at least 90%, disturbance count no more than 2, and no critical provenance or tool failure.
- V1 should record fixture hint mode explicitly, with `room_only` as default and `exact_fixtures` as an operator-selected easier mode.
- The first v1 harness gate should use one fixed MolmoSpaces scene with multiple mess seeds before expanding to multiple scenes.
- Preferred recipe names: `harness::molmo-realworld-cleanup` and `verify::molmo-realworld-cleanup`.
- **MolmoSpaces Current-Contract Agent Bridge** is a transitional MCP/OpenClaw integration phase and must not be described as satisfying ADR-0003.
- The current-contract bridge should use a new **Molmo Cleanup MCP Server**, not add Molmo tools to the existing AI2-THOR navigation MCP server.
- The current-contract bridge should include both direct coding-agent and OpenClaw paths, sequenced direct MCP first and OpenClaw second.
- The current-contract bridge should distinguish **Agent-Driven Cleanup Runs** from deterministic heuristic baselines in reports and `run_result.json`.
- The current-contract bridge should expect first-pass MCP/skill instructions to be weak and include coding-agent dogfood iterations to improve them.
- The current-contract bridge should run up to five direct coding-agent dogfood attempts, with early stop allowed after a clean successful run.
- A **Clean Agent Cleanup Run** for the current-contract bridge requires 5/5 restored targets, `cleanup_status=success`, expected semantic substeps, fridge `open_receptacle` before `place_inside`, no stale-reference errors, no premature `done`, no private-truth policy path, complete artifacts, and no manual intervention beyond launching the agent.
- The current-contract bridge should use Codex for the primary dogfood loop and Claude Code for a post-hardening compatibility smoke.
- OpenClaw acceptance for the current-contract bridge should require MCP tool-use viability and a useful trace; full 5/5 cleanup success is a stretch goal.
- Report visual parity is a shared-underlay requirement. If a synthetic run lacks robot images, that is an evidence-mode difference, not a reason to create a second report implementation.
- Phase 19 closed the real MolmoSpaces/RBY1M visual Gateway artifact gap for OpenClaw. Phase 20 closed the contract-level clean-policy gap by enforcing the public semantic loop; live Gateway can still be rerun against the stricter contract as evidence. Phase 21 closed the advisory scoring/model-check follow-up with non-authoritative report artifacts. Phase 22 closed the raw FPV-only perception evidence slice. Phase 23 closed the planner-backed manipulation provenance/proof gate. Phase 24 closed planner runtime diagnostics for strict-proof blockers. Phase 25 targets a headless renderer adapter for strict Franka planner proof; actual planner-backed cleanup execution remains separate until a probe passes the strict proof checker.
