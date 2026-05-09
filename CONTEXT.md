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

**Report Visual Core**:
The stable first-pass review sequence inside a Cleanup Artifact Report: Before/After, Object Moves, Semantic Cleanup Subphases, Robot View Timeline, and Score.
_Avoid_: Evidence panel order as report architecture

**Report Visual Core Contract**:
The package-level validation contract that current-contract and ADR-0003
checkers use to enforce one Cleanup Artifact Report section order and one
semantic subphase display vocabulary.
_Avoid_: Per-checker report string smoke test

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

**Attached Planner Proof**:
A strict standalone planner-backed manipulation proof rendered alongside a
cleanup artifact, without changing the cleanup loop's own primitive provenance.
_Avoid_: planner-backed cleanup

**Planner-Backed Cleanup Primitive Gate**:
A per-cleanup-subphase evidence gate that checks whether the cleanup loop's own
`nav, pick, nav, open?, place` steps are planner-backed, separate from attached
standalone proof.
_Avoid_: report-only proof attachment

**RBY1M CuRobo Warmup Readiness**:
Staged evidence that the target RBY1M/CuRobo runtime reached or failed each dependency/JIT warmup stage before execute-mode proof.
_Avoid_: timeout-only readiness inference

**CuRobo Extension Cache Evidence**:
Recorded Torch extension cache state for known CuRobo CUDA extensions, including configured cache directory, compiled `.so` presence, lock files, and timestamps.
_Avoid_: hidden global cache side effects

**Warp Compatibility Evidence**:
Recorded Warp API shape and any probe-local compatibility adapter applied before RBY1M/CuRobo planner execution.
_Avoid_: invisible dependency shim

**CUDA Memory Headroom Evidence**:
Recorded CUDA/PyTorch memory availability, allocation, reservation, allocator configuration, and worker-stage memory snapshots for RBY1M/CuRobo planner execution.
_Avoid_: traceback-only OOM diagnosis

**CuRobo Memory Profile Evidence**:
Recorded probe-local CuRobo policy and planner memory-related overrides, including requested profile, effective batch/seed/attempt/timestep settings, and whether collision avoidance remains enabled.
_Avoid_: hidden planner tuning

**Shared Semantic Cleanup Loop**:
The package-level execution path for the object cleanup sequence `nav, pick, nav, open?, place`, reused by MolmoSpaces cleanup demos before planner-backed primitives are attached.
_Avoid_: per-demo hand-rolled cleanup loop

**Planner Cleanup Bridge Readiness**:
Evidence that joins attached target planner proof with per-subphase cleanup primitive provenance, showing whether planner-backed cleanup replacement is actually ready.
_Avoid_: standalone proof implies cleanup execution

**Planner Proof Request Manifest**:
Private cleanup artifact metadata that turns completed ADR-0003 semantic
substeps into exact bound planner probe requests for local proof-bundle
generation.
_Avoid_: Agent View planner aliases

**Planner Proof Request Report View**:
The private report section that summarizes proof requests, ready/blocked
status, semantic tools, and planner aliases after cleanup has finished.
_Avoid_: treating proof requests as Cleanup Agent input

**Planner Proof Bundle Runner Report**:
The visual `report.html` produced by the local proof-bundle runner to show
exact probe commands, expected proof artifacts, and optional cleanup rerun
commands.
_Avoid_: treating command evidence as proof success

**Planner Proof Bundle Runner Checker**:
The artifact gate that validates local proof-bundle runner manifests and
reports before or after real proof generation.
_Avoid_: replacing strict per-proof validation

**Planner-Backed Cleanup Primitive Executor**:
The strict execution seam behind the shared semantic cleanup loop. It can mark a cleanup subphase as `planner_backed` only after per-call planner execution evidence exists for that exact `nav`, `pick`, `nav`, `open`, or `place` step.
_Avoid_: relabeled semantic state sync

**Planner Primitive Target Binding**:
The rule that planner primitive evidence must match the semantic cleanup object, and target-side evidence must match the target receptacle, before a subphase is strict-ready.
_Avoid_: generic tool-level proof

**Probe-Backed Cleanup Primitive Executor**:
The adapter that can convert a strict target RBY1M/CuRobo planner proof attachment into cleanup primitive executor evidence only when that proof carries matching cleanup primitive binding.
_Avoid_: standalone target proof as primitive proof

**Planner Probe Cleanup Binding**:
The planner-probe artifact fields that record the sampled upstream pickup/place task and promote cleanup primitive binding only when a requested cleanup object and target exactly match.
_Avoid_: unverified handle mapping

**Observed Handle Planner Binding**:
Private runtime evidence that maps an ADR-0003 Observed Object Handle plus public target fixture to planner-facing pickup/place names, while keeping cleanup primitive binding keyed by the observed handle.
_Avoid_: exposing planner aliases in Agent View

**Bounded Planner Cleanup Executor**:
An opt-in cleanup harness path that uses a probe-backed planner executor only for cleanup subphases whose observed handle and target match the attached planner proof binding.
_Avoid_: full cleanup replacement claim

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
- A **Cleanup Artifact Report** should keep the **Report Visual Core** in a stable order even when new ADR-0003 evidence panels are added.
- A **Cleanup Artifact Report** may omit Robot View Timeline only when no robot views were recorded.
- A **Cleanup Artifact Report** should display **Semantic Cleanup Subphases** as `nav -> pick -> nav -> open? -> place`, while raw trace artifacts keep full tool names.
- A **Shared Semantic Cleanup Loop** should be the default object-level execution path for MolmoSpaces cleanup demos, with contract-specific perception and scoring layered around it.
- Real visual OpenClaw cleanup evidence should include Robot View Timeline with FPV, chase, map, and verification images from the MolmoSpaces/RBY1M backend.
- Clean OpenClaw cleanup evidence should enforce the semantic loop as executable MCP contract behavior, not prompt-only advice.
- Advisory scoring/model checks should render in the shared **Cleanup Artifact Report** without changing deterministic scoring fields.
- Raw FPV-only perception should be an explicit evidence mode on the ADR-0003 contract, not a replacement for the default visible-detection cleanup gate.
- A **Raw FPV Observation** may include waypoint, room, observation id, and image artifact references, but not structured movable-object detections or private scoring truth.
- A **Camera Model Policy** may derive observed object handles from public raw FPV observations, but every candidate must carry explicit model provenance and must not include target receptacles, `is_misplaced`, generated-mess truth, or private scorer labels.
- **Planner-Backed Manipulation Proof** must require planner policy execution evidence, nonzero robot-state movement, and no `api_semantic` fallback.
- `api_semantic` cleanup artifacts may be useful cleanup evidence, but must not satisfy **Planner-Backed Manipulation Proof**.
- Planner runtime blockers should be reported as dependency/runtime diagnostics, not inferred from sparse shell failures.
- A **Headless Planner Renderer Adapter** may help reach planner execution in local probes, but it is not itself **Planner-Backed Manipulation Proof**.
- An **Attached Planner Proof** may make planner capability visible in a cleanup report, but cleanup object moves remain `api_semantic` unless the cleanup loop actually calls planner-backed primitives.
- A **Planner-Backed Cleanup Primitive Gate** should reject `api_semantic` cleanup subphases as strict planner-backed cleanup execution, while allowing explicit blocked-capability evidence until real primitives exist.
- An **RBY1M CuRobo Runtime Gate** should reject standalone Franka planner proof as target cleanup runtime readiness, while allowing explicit blocked-capability evidence when CuRobo is missing.
- **RBY1M CuRobo Warmup Readiness** should record worker stages before treating a timeout as actionable evidence.
- **CuRobo Extension Cache Evidence** should be recorded before retrying target RBY1M/CuRobo imports when global Torch extension cache state may be stale.
- **CUDA Memory Headroom Evidence** should be recorded before tuning RBY1M/CuRobo planner memory settings or treating a target execute-mode OOM as a generic failure.
- **Warp Compatibility Evidence** should be visible before a shimmed target planner probe can be used as readiness evidence.
- **CuRobo Memory Profile Evidence** should be visible before a tuned RBY1M/CuRobo planner probe is used to assess target runtime readiness.
- A **Shared Semantic Cleanup Loop** should be in place before replacing cleanup primitives, so planner-backed `nav`, `pick`, `open`, and `place` implementations have one integration point.
- **Planner Cleanup Bridge Readiness** should require both target RBY1M/CuRobo proof and planner-backed cleanup subphases; if either side is missing, the bridge remains blocked capability.
- A **Planner-Backed Cleanup Primitive Executor** should be the only path that changes cleanup subphase provenance from `api_semantic` to `planner_backed`.
- **Planner Primitive Target Binding** should be enforced before wiring a real object-specific RBY1M/CuRobo cleanup executor.
- A **Probe-Backed Cleanup Primitive Executor** should reject generic standalone planner proof unless it names the cleanup object, target, and tool it executed.
- **Planner Probe Cleanup Binding** should be emitted before the probe-backed executor is used for ADR-0003 cleanup subphases.
- **Observed Handle Planner Binding** should keep public cleanup IDs and planner sampled-task aliases separate before real ADR-0003 cleanup subphases use probe-backed executor evidence.
- A **Bounded Planner Cleanup Executor** should be proven before claiming full multi-object planner-backed cleanup replacement.
- A **Planner Proof Request Manifest** should be generated after cleanup from semantic substeps and private bindings, not by exposing planner aliases to the Cleanup Agent.
- A **Planner Proof Request Report View** should render private request evidence in `report.html` when the manifest exists, while Agent View remains planner-alias-free.
- A **Planner Proof Bundle Runner Report** should accompany dry-run and executed local proof-bundle manifests so command handoffs are reviewable.
- A **Planner Proof Bundle Runner Checker** should validate manifest/report consistency before local proof-bundle execution is treated as ready to run.
- MCP smoke demos should call the **Shared Semantic Cleanup Loop** instead of
  hand-rolling `nav`, `pick`, `nav`, optional `open`, and `place` sequences, so
  report visual parity depends on one cleanup-loop module.

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
- Phase 19 closed the real MolmoSpaces/RBY1M visual Gateway artifact gap for OpenClaw. Phase 20 closed the contract-level clean-policy gap by enforcing the public semantic loop; live Gateway can still be rerun against the stricter contract as evidence. Phase 21 closed the advisory scoring/model-check follow-up with non-authoritative report artifacts. Phase 22 closed the raw FPV-only perception evidence slice. Phase 23 closed the planner-backed manipulation provenance/proof gate. Phase 24 closed planner runtime diagnostics for strict-proof blockers. Phase 25 closed the headless renderer adapter and produced a passing strict Franka planner proof. Phase 26 closed the attached-proof report gap by rendering that strict proof inside ADR-0003 cleanup reports without relabeling cleanup-loop primitives. Phase 27 closed the per-subphase cleanup primitive gate. Phase 28 closed the RBY1M/CuRobo runtime gate; actual RBY1M planner execution remained blocked by CuRobo JIT/config-import timeout before execution. Phase 29 closed the camera-only model-policy cleanup follow-up with shared-underlay synthetic and real MolmoSpaces/RBY1M visual artifacts. Phase 30 closed the report visual-core consolidation so future evidence panels cannot create another visual implementation. Phase 31 closed staged RBY1M/CuRobo warmup-readiness evidence. Phase 32 closed isolated CuRobo extension-cache evidence. Phase 33 closed visible probe-local Warp compatibility. Phase 34 captured CUDA memory headroom for the target execute-mode OOM. Phase 35 closed visible low-memory RBY1M/CuRobo profile retry evidence and produced strict standalone target planner-backed proof. Phase 36 closed the duplicated cleanup-loop architecture by routing current-contract and ADR-0003 demos through one shared semantic cleanup driver. Phase 37 closed explicit planner cleanup bridge-readiness evidence: target runtime readiness is true with the Phase 35 proof attached, but bridge status remains blocked until cleanup subphases stop using `api_semantic`. Phase 38 closed the strict planner-backed cleanup primitive executor seam. Phase 39 closed object/target binding for planner primitive evidence. Phase 40 closed the probe-backed executor adapter that keeps generic target proof blocked unless a proof carries matching cleanup primitive binding. Phase 41 closed sampled-task binding at the real probe source and promotes cleanup primitive binding only on exact request/sample match. Phase 42 closed private observed-handle to planner-alias binding so the remaining executor path can use ADR-0003 handles without losing exact upstream task matching. Phase 43 closed bounded opt-in executor wiring so matching proof can drive one observed-handle cleanup attempt through planner-backed subphase evidence without claiming full multi-object replacement. Phase 44 closed proof-bundle coverage so full cleanup artifacts can require one matching proof per cleaned object before the bridge reports ready. Phase 45 closed report visual-core drift by enforcing one shared report contract and one semantic timeline mapping. Phase 46 closed the proof-generation handoff by emitting private request manifests and a dry-run local bundle runner. Phase 47 closed the proof-request report view so that handoff is visible in shared cleanup reports. Phase 48 closed the visual report for local proof-bundle runner output. Phase 49 closed the checker for that runner manifest/report pair.
