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

**Task Sampler Robot Placement Profile**:
A probe-local set of placement-search overrides used to test whether an
upstream MolmoSpaces sampled task is blocked by robot base-placement strictness.
It must be rendered as mitigation evidence, not treated as cleanup success or
planner-backed readiness.
_Avoid_: Hidden sampler patch, proof success flag

**Placement Scene Diagnostics**:
Probe-local report evidence that summarizes public map free space around the
actual upstream robot-placement target, including valid free-point counts,
nearest free-point distance, and radius-band counts.
_Avoid_: hidden planner fix, success proof

**Wide Placement Profile**:
A probe-local robot-placement mitigation profile that extends placement search
to `[0.0, 2.0]m` and raises the effective upstream `place_robot_near` budget to
100 tries. It is evidence for task-feasibility diagnosis, not cleanup success.
_Avoid_: production placement policy, readiness proof

**Post-Placement Candidate Rejections**:
Probe-local report evidence for task-sampler rejection after robot placement
succeeds, including grasp-failure counts and candidate-removal calls.
_Avoid_: robot placement failure, planner execution failure

**Grasp-Feasibility Blocker**:
A proof-result classification for exact-scene requests that clear robot
placement but fail through post-placement grasp/candidate rejection.
_Avoid_: generic task-feasibility blocker

**Grasp-Feasibility Selection Memory**:
Proof-request selection evidence that carries a prior grasp-feasibility blocker
kind/detail into excluded requests, fallback provenance, filtered fallback
pairs, and runner report blocker views.
_Avoid_: hidden retry heuristic, cleanup readiness proof

**Cleanup-Pair Proof Memory**:
Proof-request selection memory matched by public cleanup `object_id` plus
`target_receptacle_id` when a regenerated proof request has a different
request ID.
_Avoid_: planner-alias-only memory, hidden object identity

**Standalone Prior Proof Result Ingest**:
The proof-bundle runner behavior that loads standalone planner-probe
`run_result.json` artifacts into the shared **Planner Proof Result Summary**
interface before proof request selection.
_Avoid_: manual synthetic prior summary wrapper, treating standalone probes as proof-bundle manifests

**Prior Proof Evidence View**:
The proof-bundle runner report section that renders normalized prior proof
results, including diagnostic rows, proof report links, and planner-view image
artifacts when present.
_Avoid_: selection-only prior evidence, hidden prior visual artifacts

**Nested Prior Proof Evidence Carry-Forward**:
The proof-bundle runner behavior that re-ingests a prior proof-bundle
manifest's own `prior_proof_result_summary` together with its current
`proof_result_summary`, so prior evidence survives across multiple runner
generations.
_Avoid_: single-hop prior memory, dropping nested blocker evidence

**Planner-Object Proof Memory**:
Proof-request selection memory keyed by internal planner object alias plus
public target receptacle, used when public `observed_*` handles or request IDs
change across broader cleanup artifacts.
_Avoid_: global request ID memory, observed-handle-only proof memory

**Selected Proof Candidate Execution**:
Local-dev execution of the currently selected exact-scene proof request after
prior infeasible requests are filtered.
_Avoid_: treating selected as feasible before execution

**Broader Selected Proof Execution**:
Local-dev execution of selected exact-scene proof requests from a broader
cleanup artifact, after known internal blocked pairs are filtered, to record
strict proof, cleanup binding, and visual evidence before a cleanup rerun.
_Avoid_: treating selection as proof, treating one passing proof as full cleanup readiness

**Broader Bound Proof Cleanup Rerun**:
Final cleanup rerun that consumes an already passing broader bound proof and
verifies the matching cleanup object uses planner-backed primitive evidence
while unmatched objects remain honest `api_semantic` work.
_Avoid_: re-executing proof bundles, full bridge-ready claim from one bound object

**Prior Covered Proof Memory**:
Proof-request selection memory that excludes prior results that are already
`planner_backed` and have promoted cleanup binding, so broader proof execution
expands coverage instead of retrying solved cleanup object/target pairs.
_Avoid_: rerunning passing bound proofs

**Planner Failure Diagnostic Views**:
The shared report visual surface for exact-scene planner probes that fail
during task sampling before normal initial/final planner views exist. Future
runs should prefer captured post-placement camera artifacts through
`image_artifacts`; older diagnostic-only artifacts may render inline
task-sampler visual summaries instead of an empty no-view state.
_Avoid_: second report renderer, table-only blocked proof

**Post-Placement Rejection Views**:
The shared report visual surface for grasp-feasibility blockers after robot
placement succeeds, showing grasp failures, candidate removals, threshold
removals, and candidate-count movement from task-sampler diagnostics.
_Avoid_: table-only grasp-feasibility blocker, per-report rejection chart

**Grasp-Feasibility Blocker Matrix**:
The proof-bundle selection report view that summarizes grasp-infeasible
object-target pairs as cards before the detailed blocker table, preserving the
source request, match kind, and blocker summary.
_Avoid_: table-only selection blocker review

**Grasp-Feasibility Signature Matrix**:
The proof-bundle result report view that groups repeated executed
grasp-feasibility failures by their blocker pattern, such as identical grasp
failure and candidate-removal counts across multiple proof requests.
_Avoid_: treating grouped blockers as proof success

**Candidate Removal Effectiveness**:
Task-sampler diagnostic evidence that separates a grasp-threshold removal call
from an actual candidate-pool mutation, including candidate-name presence
before/after removal and effective-removal counts.
_Avoid_: assuming candidate-removal calls mean the object was removed

**Exact Pickup Candidate Binding**:
Probe-local exact-scene sampler evidence that binds the upstream pickup
candidate pool to the requested planner object immediately before pickup
selection, recording before/after candidate counts, requested-name presence,
and whether the requested candidate had to be injected.
_Avoid_: reset-time candidate patch, unrelated candidate retry loop

**Valid Cleanup Scene Binding**:
Exact-scene proof evidence that the requested cleanup scene XML exists and was
applied before task-sampler or alias blockers are interpreted.
_Avoid_: default-scene fallback, stale scene path proof

**Exact Pickup Retry Budget**:
Probe-local exact sampler evidence that repeats the requested pickup candidate
enough times for upstream grasp-failure threshold semantics to run, without
reintroducing unrelated candidate objects.
_Avoid_: one-attempt exact candidate collapse, unrelated retry pool

**Grasp Collision Diagnostics**:
Probe-local evidence from upstream grasp loading and collision masking: cached
grasp count, collision-checked pose count, non-colliding count, and hook
exceptions for the exact requested object.
_Avoid_: opaque grasp-failure counts with no loader/collision-mask detail

**Missing Grasp Cache Signature**:
Proof-result summary evidence that keeps `grasp_feasibility` as the top-level
blocker while classifying missing cached grasp files as a distinct subkind with
failed asset UIDs.
_Avoid_: grouping missing cache with zero non-colliding grasp checks

**Grasp Cache Routing Decision**:
Proof-bundle runner evidence that routes missing cached grasp assets to cache
mitigation before exact retry while keeping source rotation state visible for
separate unproven requests.
_Avoid_: treating source rotation as if it mitigated a known missing cache asset

**Grasp Cache Availability Preflight**:
Proof-bundle runner evidence that probes the exact rigid grasp-cache files used
by MolmoSpaces' object loader and distinguishes present object assets from
missing loader-compatible grasp caches.
_Avoid_: assuming an object asset cache implies cached rigid grasps exist

**Runtime Assets Grasp Cache Preflight**:
Grasp-cache availability evidence bound to the MolmoSpaces runtime `ASSETS_DIR`
derived from the planner scene XML, including symlink-resolved cache targets.
_Avoid_: displaying data-cache roots as if they were the loader root

**Grasp Cache Validity Preflight**:
Rigid grasp-cache evidence that parses candidate files and treats a loader file
as ready only when it contains at least one transform.
_Avoid_: treating empty NPZ/JSON files as a successful cache install

**Grasp Filter Diagnostics**:
Bounded local evidence that preserves MolmoSpaces rigid grasp intermediates and
reruns perturbation-filter variants before cache installation.
_Avoid_: relying on an empty filtered NPZ as the only failure signal

**Grasp Initial Contact Diagnostics**:
Bounded local evidence that sweeps rigid-grasp open-settle and approach-pose
parameters against preserved generated candidates, recording initial object
contacts, initial displacement, final gripper contacts, and nonzero success
counts before any loader cache installation.
_Avoid_: treating zero filtered transforms as an opaque perturbation failure

**Post-Execution Fallback Exhaustion**:
Proof-request selection evidence showing that, after executed proof results are
used as prior memory, a source pool has no selected requests and no generated
fallback requests left.
_Avoid_: rerunning an exhausted source pool

**Proof-Bundle Local Runtime Preflight**:
The proof-bundle runner evidence that checks the configured MolmoSpaces Python
runtime before real `--execute-probes` commands, rendering missing import or
missing executable blockers instead of failing before `report.html` exists.
_Avoid_: local-dev crash before manifest, treating runtime setup as proof failure

**Canonical MolmoSpaces Runtime Import**:
The runtime preflight import name for upstream MolmoSpaces Python packages:
`molmo_spaces`, not the colloquial project label `molmospaces`.
_Avoid_: false blocked preflight from wrong package name

**Seeded Source Rotation Evidence**:
Local-dev evidence that a new MolmoSpaces generated-mess seed can produce a
different exact-scene proof request pool while prior proof memory filters
already covered or known-blocked requests before execution.
_Avoid_: claiming selected dry-run commands as planner-backed proof

**Seed 10 Selected Proof Execution**:
Local-dev execution evidence for selected seed 10 proof commands. It can add
planner-backed cleanup coverage only if a proof both passes and promotes cleanup
binding; otherwise it is blocker evidence.
_Avoid_: treating selected commands or executed blockers as cleanup success

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

**Cleanup Report Artifact Adapter**:
A small adapter whose interface starts from an existing cleanup `run_result.json`
and rehydrates scenario, trace, snapshots, private manifest, and robot-view
steps before delegating to the shared Cleanup Artifact Report underlay. When an
older ADR-0003 artifact has no `scenario.json`, the adapter uses only a minimal
public scenario shell from `run_result.json` and does not fabricate objects or
private targets.
_Avoid_: second report renderer, manual stale HTML repair

**Report Visual Core**:
The stable first-pass review sequence inside a Cleanup Artifact Report: Before/After, Object Moves, Semantic Cleanup Subphases, Robot View Timeline, and Score.
_Avoid_: Evidence panel order as report architecture

**Focused Robot View Timeline**:
The Robot View Timeline view inside the Report Visual Core after raw FPV scan
captures are kept in Raw FPV Observations instead of mixed into the first-pass
cleanup action review.
_Avoid_: perception scan log as primary cleanup timeline

**Report Visual Core Contract**:
The package-level validation contract that current-contract and ADR-0003
checkers use to enforce one Cleanup Artifact Report section order and one
semantic subphase display vocabulary.
_Avoid_: Per-checker report string smoke test

**Report Style Scope**:
The rule that planner/proof diagnostic report styles are opt-in extras, while
Cleanup Artifact Reports keep the base visual underlay used by current-contract
and ADR-0003 cleanup demos.
_Avoid_: planner diagnostics changing cleanup report visuals

**Semantic Cleanup Subphase**:
A report-facing label for one step in the object cleanup loop: `nav`, `pick`, `nav`, optional `open`, then `place`.
_Avoid_: Raw tool log as visual flow

**Semantic Cleanup Vocabulary**:
The package-level source of truth for raw cleanup phases, canonical cleanup
phase sequences, report-facing subphase labels, loop variant strings, and
focused robot-view action prefixes.
_Avoid_: per-demo phase constants, checker-local visual vocabulary

**Grasp Cache Generation Preflight**:
Report-visible evidence for whether the upstream MolmoSpaces rigid grasp
generator is locally runnable for a missing-cache asset, including object XML,
loader cache target, Python prerequisites, Manifold executables, and proposed
generation command.
_Avoid_: failed invisible generation attempt, fake grasp cache

**Grasp Generation Setup Runner**:
The checked-in local-dev runner that installs rigid grasp-generation Python
prerequisites, initializes/builds Manifold, and reruns the same generation
preflight as its acceptance gate.
_Avoid_: one-off shell setup that cannot be reproduced by the next agent

**Grasp Cache Generation Runner**:
The checked-in local-dev runner that turns a ready generation preflight into an
upstream `run_rigid.py` attempt, validates the generated NPZ, installs only
non-empty cache files, and renders command/install blockers.
_Avoid_: copying unfiltered candidates or empty NPZ files into the loader cache

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

**Planner Proof Quality Evidence**:
Reusable proof-strength classification for attached planner proofs, separating
one-step robot motion, multi-step robot motion, and containment-level proof
from the lower-level `steps_executed` and `max_abs_qpos_delta` fields.
_Avoid_: implicit proof strength, report-only quality labels

**Planner Proof Quality Report Reuse**:
The rule that standalone planner-probe reports, proof-bundle runner reports,
and cleanup reports all render **Planner Proof Quality Evidence** through the
same quality tiers.
_Avoid_: separate proof-strength labels per report surface

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
commands and artifacts.
_Avoid_: treating command evidence as proof success

**Planner Proof Result Summary**:
The bundle-level manifest/report section that summarizes generated proof
outputs after execution: proof status, cleanup binding promotion,
task-feasibility classification, blockers, proof report paths, and any planner
view images.
_Avoid_: replacing strict per-proof validation

**Proof Request Feasibility Selection**:
The private runner step that consumes a prior **Planner Proof Result Summary**
and excludes proof requests already known to be exact-scene RBY1M
task-feasibility blocked.
_Avoid_: proving fallback feasibility

**Planner Proof Fallback Request**:
A private proof-bundle runner request generated from an excluded source request
by preserving cleanup-facing object/target IDs while varying planner-facing
object or target aliases from existing observed-handle binding metadata.
_Avoid_: treating alias fallback candidates as proven feasible proof

**Generated Fallback Proof Execution**:
Local-dev proof-bundle execution of generated fallback requests against the
target RBY1M/CuRobo path, used to determine whether alternate planner aliases
reach strict proof and cleanup primitive binding promotion.
_Avoid_: treating executed-but-blocked fallback outputs as cleanup readiness

**Fallback Timeout Stage Evidence**:
Bundle-level reporting of where generated fallback proof execution timed out,
including the last worker stage, compact worker stage sequence, and proof
stdout/stderr artifact paths.
_Avoid_: reporting only generic timeout when stage data exists

**Fallback Proof Warmup**:
An explicit proof-bundle runner step that runs a visible RBY1M/CuRobo
`config_import` probe before generated fallback proof commands, sharing the
same output-local Torch extension cache when no cache is provided.
_Avoid_: undocumented shell preflight

**Warmed Generated Fallback Proof Execution**:
Local-dev generated fallback proof execution after **Fallback Proof Warmup**,
used to distinguish warmup/JIT blockers from exact-scene task-sampling and
planner-alias validity blockers.
_Avoid_: treating warmup success as proof success

**Exact-Scene Fallback Alias Filter**:
The proof-bundle runner rule that keeps private alias metadata visible while
allowing only exact-scene runtime-style aliases to become generated fallback
proof command inputs.
_Avoid_: retrying upstream/display aliases that fail task sampling with `KeyError`

**Fallback Runtime Alias Discovery**:
The proof-bundle runner step that mines prior exact-scene `KeyError`
valid-name lists for same-family runtime aliases and turns them into bounded
generated fallback proof commands.
_Avoid_: treating discovered command candidates as planner-backed proof

**Discovered Runtime Fallback Proof Execution**:
Local-dev proof-bundle execution of runtime-sibling fallback commands generated
from **Fallback Runtime Alias Discovery**, used to separate alias-discovery
success from root-body validity and upstream task-feasibility blockers.
_Avoid_: treating valid-looking runtime aliases as viable cleanup primitives

**Fallback Failed Candidate Memory**:
The proof-bundle runner evidence that carries discovered aliases forward while
filtering prior non-root object aliases and prior task-feasibility-blocked
object/target alias pairs before generating new fallback commands.
_Avoid_: retrying known-bad generated fallback commands

**Filtered Fallback Proof Execution**:
Local-dev execution of generated fallback commands after **Fallback Failed
Candidate Memory** has removed known bad aliases and alias pairs.
_Avoid_: treating a filtered retry as proof success before strict outputs pass

**Fallback Filter Carry-Forward**:
The proof-bundle runner behavior that treats previously rendered filtered
fallback aliases and filtered fallback pairs as active filters in later
selection passes.
_Avoid_: using the latest manifest while forgetting earlier filtered evidence

**Pickup Root Variant Filter**:
The fallback-generation rule that rejects object-axis runtime aliases whose
variant segment is nonzero because they are known non-root pickup bodies.
_Avoid_: executing object-side sibling aliases that can be rejected by name

**Prior Proof Evidence Merge**:
The proof-bundle runner behavior that combines multiple prior proof-bundle
manifests into one private selection input, preserving discovered aliases,
filtered aliases, filtered pairs, and proof results together.
_Avoid_: choosing between alias discovery and failed-candidate memory

**Fallback Exhaustion Status**:
The proof-bundle runner report classification that says whether generated
fallback selection is `disabled`, `not_required`, `generated`, or `exhausted`.
_Avoid_: inferring exhausted candidate pools from empty command tables alone

**Fallback Exhaustion Blocker Summary**:
The proof-bundle runner report evidence that names why an exhausted generated
fallback pool has no remaining commands, such as pickup root-body alias gaps,
target task-feasibility-blocked pairs, or source requests with no remaining
candidate.
_Avoid_: making reviewers infer next work from low-level filtered tables alone

**Pickup Root Alias Normalization**:
The fallback-generation rule that maps nonzero-variant object runtime aliases
back to their variant-0 pickup root alias before deciding whether a root-body
alias source is still missing.
_Avoid_: treating every non-root runtime sibling as an unresolved alias-source gap

**Target Feasibility Proof Link**:
The filtered fallback pair evidence that points from a target-side
task-feasibility block to the exact prior proof report, run result, worker
stage, and blockers that established it.
_Avoid_: filtered pair rows that require manual archaeology through output dirs

**Target Feasibility Blocker Matrix**:
The proof-bundle runner report view that joins task-feasibility-blocked source
requests and task-feasibility-blocked generated fallback pairs into one
selection-owned blocker table.
_Avoid_: splitting the current target-side blocker across source and fallback
tables that reviewers must reconcile manually

**Task Sampler Exception Context**:
The planner-probe evidence preserved when exact cleanup task sampling fails
before policy execution, including exact task config, sampler adapter state,
requested cleanup binding, worker stage, and blockers.
_Avoid_: treating `HouseInvalidForTask` as a context-free sampler failure

**Task Sampler Failure Diagnostics**:
The probe-local evidence captured from upstream task-sampler hooks when
`HouseInvalidForTask` occurs, including robot-placement attempts, asset failure
reasons, candidate removals, and placement config.
_Avoid_: leaving robot-placement failures only in stderr logs

**Planner Proof Bundle Runner Checker**:
The artifact gate that validates local proof-bundle runner manifests and
reports before or after real proof generation.
_Avoid_: replacing strict per-proof validation

**Cleanup Rerun Artifact**:
The final cleanup `run_result.json` and `report.html` produced after a proof
bundle runner reruns cleanup with generated planner proof outputs.
_Avoid_: treating artifact existence as planner-backed cleanup success

**Planner Proof Bundle Execute Rerun Gate**:
The local-dev harness that runs bound planner proofs, reruns cleanup with their
outputs, and requires the final cleanup artifact to pass planner primitive and
bridge checks.
_Avoid_: CI-default proof execution gate

**Exact Cleanup Scene Proof Binding**:
The proof-bundle path where generated planner probes sample from the same real
MolmoSpaces scene XML and requested upstream object/target aliases as the
cleanup artifact.
_Avoid_: proving synthetic cleanup aliases with unrelated sampled tasks

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
- A **Cleanup Artifact Report** should keep **Report Style Scope** stable:
  planner/proof diagnostics may add opt-in styles to their own reports, but
  they must not change the cleanup report visual underlay.
- A **Cleanup Artifact Report** may omit Robot View Timeline only when no robot views were recorded.
- A **Cleanup Artifact Report** should display **Semantic Cleanup Subphases** as `nav -> pick -> nav -> open? -> place`, while raw trace artifacts keep full tool names.
- A **Cleanup Artifact Report** should keep object/target/surface/inside as
  secondary role detail, not as part of the primary **Semantic Cleanup
  Subphase** label.
- A **Cleanup Artifact Report** should keep raw FPV scan captures in Raw FPV
  Observations, not in the first-pass **Focused Robot View Timeline**, when the
  dedicated raw FPV panel exists.
- **Semantic Cleanup Vocabulary** should be imported by the shared loop,
  Cleanup Artifact Report, visual-core checks, and checkers instead of
  redefined per demo.
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
- An **Attached Planner Proof** should include **Planner Proof Quality
  Evidence**, so reports and checkers can distinguish `one_step_motion` from
  multi-step pick/place progress or full containment.
- **Planner Proof Quality Report Reuse** should keep individual proof reports,
  proof-bundle runner reports, and cleanup reports on the same proof-strength
  vocabulary before stricter proof gates are raised.
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
- **Exact Pickup Candidate Binding** should happen at the live upstream pickup
  selection point, not at reset-time, and should remain private proof evidence
  rendered by the shared report underlay.
- **Valid Cleanup Scene Binding** should be required before an exact-scene
  proof blocker is interpreted as alias validity or task feasibility evidence.
- **Exact Pickup Retry Budget** should preserve upstream grasp-threshold
  semantics while keeping the candidate pool exact.
- **Grasp Collision Diagnostics** should explain exact-object post-placement
  failures before any grasp-feasibility mitigation is chosen.
- **Missing Grasp Cache Signature** should keep missing asset data visible in
  proof-result summaries before source rotation or cache mitigation.
- **Grasp Cache Routing Decision** should make cache mitigation versus source
  rotation explicit before another runtime proof attempt.
- **Grasp Cache Availability Preflight** should record the droid,
  droid-objaverse, and RUM rigid loader paths for a missing grasp asset before
  generating or restoring cache data.
- **Runtime Assets Grasp Cache Preflight** should derive `ASSETS_DIR` from the
  planner scene XML and render symlink-resolved cache targets before a restore
  or generation command is chosen.
- **Grasp Cache Validity Preflight** should parse rigid loader files and require
  nonzero transforms before marking a missing-cache asset ready.
- **Grasp Cache Generation Preflight** should pass before running upstream
  rigid grasp generation or installing generated cache output.
- **Grasp Generation Setup Runner** should be used to make that preflight pass
  instead of applying ad hoc local environment fixes.
- **Grasp Cache Generation Runner** should install only a generated NPZ that
  passes the nonzero-transform validation used by the availability preflight.
- **Observed Handle Planner Binding** should keep public cleanup IDs and planner sampled-task aliases separate before real ADR-0003 cleanup subphases use probe-backed executor evidence.
- A **Bounded Planner Cleanup Executor** should be proven before claiming full multi-object planner-backed cleanup replacement.
- A **Planner Proof Request Manifest** should be generated after cleanup from semantic substeps and private bindings, not by exposing planner aliases to the Cleanup Agent.
- A **Planner Proof Request Report View** should render private request evidence in `report.html` when the manifest exists, while Agent View remains planner-alias-free.
- A **Planner Proof Bundle Runner Report** should accompany dry-run and executed local proof-bundle manifests so command handoffs are reviewable.
- A **Planner Proof Result Summary** should render executed proof outcomes,
  blockers, cleanup binding promotion, task-feasibility status, and available
  planner views in the proof-bundle runner report before fallback selection
  work consumes those outputs.
- **Proof Request Feasibility Selection** should skip prior
  task-feasibility-blocked proof requests when explicitly enabled, and should
  report `fallback_required` when no ready request remains.
- A **Planner Proof Fallback Request** should remain private runner evidence:
  it may vary planner aliases for a blocked source request, but it must keep the
  cleanup-facing observed handle, target receptacle, source receptacle, and
  semantic tools stable until real proof execution passes strict validation.
- **Generated Fallback Proof Execution** should require strict proof output and
  cleanup primitive binding promotion before it affects cleanup readiness;
  timeout or `not_reached` evidence keeps the planner cleanup bridge blocked.
- **Fallback Timeout Stage Evidence** should be rendered before another local
  generated-fallback retry is interpreted, so timeout blockers are tied to a
  worker stage rather than a generic wall-clock failure.
- A **Fallback Proof Warmup** should be visible in the **Planner Proof Bundle
  Runner Report** before generated fallback proof commands are retried after
  `rby1m_config_import` timeouts.
- **Warmed Generated Fallback Proof Execution** should still require strict
  proof outputs and cleanup primitive binding promotion before it can affect
  planner cleanup bridge readiness.
- **Discovered Runtime Fallback Proof Execution** should keep cleanup readiness
  blocked when generated runtime-sibling commands execute but fail with
  `HouseInvalidForTask` or non-root-body blockers before planner-backed proof,
  cleanup binding promotion, or planner views.
- **Fallback Failed Candidate Memory** should be visible in the **Planner Proof
  Bundle Runner Report** before another fallback execution, including filtered
  alias rows and filtered object/target pair rows.
- **Filtered Fallback Proof Execution** should still require planner-backed
  proof, cleanup binding promotion, and planner views before changing cleanup
  readiness.
- **Fallback Filter Carry-Forward** should preserve an exhausted fallback pool
  across manifests so the next slice works on root-body alias derivation instead
  of retrying filtered candidates.
- A **Pickup Root Variant Filter** should apply only to object/pickup aliases;
  target aliases need separate task-feasibility evidence.
- **Prior Proof Evidence Merge** should combine older alias-discovery evidence
  with newer failed-candidate memory before generating fallback proof commands.
- **Standalone Prior Proof Result Ingest** should normalize standalone planner
  probes to **Planner Proof Result Summary** before selection, so prior bundle
  manifests and standalone probes share one selection and report interface.
- A **Prior Proof Evidence View** should render normalized prior proof results
  in the runner report before new proof commands, so consumed blocker evidence
  keeps its report links and planner-view images.
- **Planner Proof Bundle Runner Report** proof-result image sources should use
  the same report-relative asset policy as standalone proof reports. Manifest
  fields may keep trace paths, but generated HTML should not require a second
  visual implementation or output-dir-prefixed `src` values.
- **Nested Prior Proof Evidence Carry-Forward** should merge nested prior proof
  summaries before selection so a later proof-bundle manifest can stand alone
  as the next prior input.
- **Planner-Object Proof Memory** should run after guarded request-ID and
  cleanup-pair matching so broader cleanup artifacts can select new requests
  without retrying known internal blocked object/target pairs.
- **Selected Proof Candidate Execution** should be checker-gated with required
  proof outputs before treating a selected exact-scene request as feasible or
  as a durable blocker.
- **Broader Selected Proof Execution** should follow **Planner-Object Proof
  Memory** and precede cleanup rerun; one passing bound proof can feed a rerun
  slice but does not prove all generated objects are planner-backed.
- **Broader Bound Proof Cleanup Rerun** should require the matching bound
  object to be strict planner-backed, require at least one unmatched object to
  remain `api_semantic`, and keep the global bridge blocked until every cleaned
  object has matching proof.
- **Prior Covered Proof Memory** should run alongside task-feasibility memory
  before broader proof execution, so already solved planner-backed cleanup
  bindings are visible as covered exclusions instead of selected again.
- **Fallback Exhaustion Status** should make no-command generated fallback
  states visible in the runner report and checker when all candidates are
  filtered or unavailable.
- A **Planner Proof Bundle Runner Checker** should validate manifest/report consistency before local proof-bundle execution is treated as ready to run.
- MCP smoke demos should call the **Shared Semantic Cleanup Loop** instead of
  hand-rolling `nav`, `pick`, `nav`, optional `open`, and `place` sequences, so
  report visual parity depends on one cleanup-loop module.
- A planner proof bundle runner harness should dry-run command generation and
  check the runner report before real local planner probes are executed.
- Cleanup reruns launched by a proof bundle runner should be named as
  **Cleanup Rerun Artifacts** in the runner manifest/report so the final Cleanup
  Artifact Report is not lost after probe execution.
- A **Planner Proof Bundle Execute Rerun Gate** should remain local-dev only and
  should not replace the cheaper dry-run proof-bundle runner gate. Its final
  strict cleanup check should fail until proof probes promote exact cleanup
  primitive binding.
- **Exact Cleanup Scene Proof Binding** should be required before proof-bundle
  execution is treated as cleanup primitive evidence. Synthetic cleanup aliases
  may prove report and command shape, but not exact planner-backed cleanup
  replacement.
- **Task Sampler Exception Context** should be rendered when upstream task
  sampling raises before policy execution, so target-feasibility blockers show
  whether the exact sampler adapter was applied before `HouseInvalidForTask`.
- **Task Sampler Failure Diagnostics** should be captured through probe-local
  wrappers around upstream sampler hooks, not by parsing stderr as the primary
  evidence source.

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
- Phase 19 closed the real MolmoSpaces/RBY1M visual Gateway artifact gap for OpenClaw. Phase 20 closed the contract-level clean-policy gap by enforcing the public semantic loop; live Gateway can still be rerun against the stricter contract as evidence. Phase 21 closed the advisory scoring/model-check follow-up with non-authoritative report artifacts. Phase 22 closed the raw FPV-only perception evidence slice. Phase 23 closed the planner-backed manipulation provenance/proof gate. Phase 24 closed planner runtime diagnostics for strict-proof blockers. Phase 25 closed the headless renderer adapter and produced a passing strict Franka planner proof. Phase 26 closed the attached-proof report gap by rendering that strict proof inside ADR-0003 cleanup reports without relabeling cleanup-loop primitives. Phase 27 closed the per-subphase cleanup primitive gate. Phase 28 closed the RBY1M/CuRobo runtime gate; actual RBY1M planner execution remained blocked by CuRobo JIT/config-import timeout before execution. Phase 29 closed the camera-only model-policy cleanup follow-up with shared-underlay synthetic and real MolmoSpaces/RBY1M visual artifacts. Phase 30 closed the report visual-core consolidation so future evidence panels cannot create another visual implementation. Phase 31 closed staged RBY1M/CuRobo warmup-readiness evidence. Phase 32 closed isolated CuRobo extension-cache evidence. Phase 33 closed visible probe-local Warp compatibility. Phase 34 captured CUDA memory headroom for the target execute-mode OOM. Phase 35 closed visible low-memory RBY1M/CuRobo profile retry evidence and produced strict standalone target planner-backed proof. Phase 36 closed the duplicated cleanup-loop architecture by routing current-contract and ADR-0003 demos through one shared semantic cleanup driver. Phase 37 closed explicit planner cleanup bridge-readiness evidence: target runtime readiness is true with the Phase 35 proof attached, but bridge status remains blocked until cleanup subphases stop using `api_semantic`. Phase 38 closed the strict planner-backed cleanup primitive executor seam. Phase 39 closed object/target binding for planner primitive evidence. Phase 40 closed the probe-backed executor adapter that keeps generic target proof blocked unless a proof carries matching cleanup primitive binding. Phase 41 closed sampled-task binding at the real probe source and promotes cleanup primitive binding only on exact request/sample match. Phase 42 closed private observed-handle to planner-alias binding so the remaining executor path can use ADR-0003 handles without losing exact upstream task matching. Phase 43 closed bounded opt-in executor wiring so matching proof can drive one observed-handle cleanup attempt through planner-backed subphase evidence without claiming full multi-object replacement. Phase 44 closed proof-bundle coverage so full cleanup artifacts can require one matching proof per cleaned object before the bridge reports ready. Phase 45 closed report visual-core drift by enforcing one shared report contract and one semantic timeline mapping. Phase 46 closed the proof-generation handoff by emitting private request manifests and a dry-run local bundle runner. Phase 47 closed the proof-request report view so that handoff is visible in shared cleanup reports. Phase 48 closed the visual report for local proof-bundle runner output. Phase 49 closed the checker for that runner manifest/report pair. Phase 50 closed the remaining MCP smoke-loop duplication by routing current-contract and ADR-0003 smoke demos through the Shared Semantic Cleanup Loop. Phase 51 closed the dry-run proof-bundle runner harness. Phase 52 closed cleanup rerun artifact tracking for executed proof-bundle flows. Phase 53 closed the named local-dev execute-rerun gate and exposed exact upstream sampled-task binding as the blocker: five proofs executed as `planner_backed`, but none matched the requested cleanup object/target aliases, so final cleanup stayed `api_semantic`. Phase 54 closed the random-proof mismatch by binding proof probes to the real cleanup scene XML and requested planner aliases; the next blocker is upstream RBY1M cleanup-scene task feasibility (`HouseInvalidForTask` / robot placement infeasibility). Phase 55 closed the proof-bundle result-reporting gap by rendering per-proof status, task-feasibility classification, cleanup binding promotion, blockers, proof report links, and planner views in the bundle report. Phase 56 closed the first fallback-selection seam by letting proof-bundle runs exclude prior task-feasibility-blocked requests and report when alternate request generation is required. Phase 57 closed private fallback request generation by turning excluded blocked requests into bounded alternate planner-alias proof commands while preserving cleanup-facing IDs and report/checker visibility.
- Phase 58 executed four generated fallback requests locally; the runner checker passed with required proof outputs, but every generated proof timed out at `rby1m_config_import` before task sampling, planner views, or cleanup binding promotion.
- Phase 59 closed the original semantic-label discussion by making shared Cleanup Artifact Reports use `nav`, `pick`, `nav`, optional `open`, and `place` as primary labels while keeping object/target/surface/inside as secondary role detail.
- Phase 60 closed the fallback timeout reporting gap by surfacing timeout counts, execution-attempted state, last worker stage, compact worker stage events, and stdout/stderr paths from generated proof outputs in the shared Planner Proof Result Summary and proof-bundle runner report.
- Phase 61 added a visible fallback proof warmup step to the proof-bundle runner so the next local generated-fallback retry can warm RBY1M/CuRobo `config_import` once, share an output-local Torch extension cache with proof commands, and render/check that warmup in the runner report.
- Phase 62 executed the warmed generated fallback proof bundle locally. The warmup got through `rby1m_config_import`, and all four generated proofs reached task sampling; they now fail with `KeyError` invalid planner alias names instead of timeout.
- Phase 63 closed the exact-scene fallback alias validity gap by filtering upstream/display aliases from generated fallback command inputs while rendering the skipped aliases in the runner manifest/report. The current local artifact now has no executable alternate fallback aliases, so the next blocker is runtime alias discovery rather than retrying display IDs.
- Phase 64 closed runtime alias discovery by mining Phase 62 `KeyError` valid-name lists for same-family exact-scene aliases. The dry-run generated four runtime-sibling fallback commands and rendered discovered aliases, filtered aliases, fallback rows, and commands in the proof-bundle runner report.
- Phase 65 executed those discovered runtime-sibling fallback commands locally
  with RBY1M/CuRobo warmup. The proofs no longer timed out and reached task
  sampling, but target-sibling aliases still blocked with `HouseInvalidForTask`
  and object-sibling aliases blocked as non-root bodies; no planner-backed proof,
  cleanup binding promotion, or planner views were produced.
- Phase 66 closed failed-candidate memory for generated fallbacks. The runner
  now carries prior discovered aliases forward, filters prior non-root object
  aliases, filters prior task-feasibility-blocked object/target pairs, renders
  `Filtered Fallback Pairs`, and dry-runs two remaining commands for the
  untried book runtime sibling.
- Phase 67 executed those two filtered fallback commands locally. Both reached
  task sampling without timeout, but the remaining book runtime sibling also
  failed as a non-root body; no proof became planner-backed, promoted cleanup
  binding, or produced planner views.
- Phase 68 closed fallback filter carry-forward. The runner now treats prior
  filtered aliases and pairs as active filters, so the Phase 67 manifest dry-run
  generates zero commands and marks both source requests unavailable until
  pickup root-body aliases are derived or validated.
- Phase 69 added the pickup root variant filter. Object-axis runtime siblings
  with nonzero variants are filtered as `not_pickup_root_body_alias`, so older
  KeyError evidence no longer generates the object-side non-root commands that
  Phases 65 and 67 proved invalid.
- Phase 70 closed prior proof evidence merge. The runner can now accept
  multiple prior proof-bundle manifests and merge runtime alias discovery with
  carried failed-candidate memory before selection, so Phase 62 KeyError
  evidence and Phase 68 filtered-pair evidence can be consumed together.
- Phase 71 surfaced fallback exhaustion status. Generated fallback selection now
  reports `disabled`, `not_required`, `generated`, or `exhausted`, and the
  proof-bundle runner report/checker make the exhausted no-command state
  explicit.
- Phase 72 summarized fallback exhaustion blockers, naming root-body alias gaps,
  target task-feasibility-blocked pairs, and no-candidate source requests in
  the runner report.
- Phase 73 normalized non-root pickup runtime aliases back to variant-0 root
  aliases, proving the current object-side aliases were already derivable.
- Phase 74 preserved target-feasibility proof links for filtered fallback pairs
  and prevented colliding generated request IDs from hiding distinct prior
  attempts.
- Phase 75 joined source request blockers and generated fallback-pair blockers
  into one Target Feasibility Blocker Matrix.
- Phase 76 preserved Task Sampler Exception Context so warmed local
  `HouseInvalidForTask` reports show the exact sampler adapter was applied
  before upstream task feasibility failed.
- Phase 77 captured Task Sampler Failure Diagnostics. The warmed local report
  shows the current exact book/shelf task fails through repeated robot
  placement attempts for `Book_23`, not missing alias or sampler-adapter
  context.
- Phase 78 added the Task Sampler Robot Placement Profile. The warmed local
  report proves the relaxed profile affects the actual upstream
  `place_robot_near` calls, but the exact `Book_23` request still fails after
  17 effective `max_tries=50` placement attempts.
- Phase 79 added Placement Scene Diagnostics. The warmed local report shows the
  exact `Book_23` request has low local free space: 2,231 valid free map points
  in the `[0.0, 1.2]m` annulus, a 0.012326 free-space fraction, no free points
  within 1.0m, and the nearest free point at 1.111824m.
- Phase 80 added the Wide Placement Profile. The warmed local report shows the
  exact `Book_23` request now clears robot placement with 17/17 successful
  `place_robot_near` calls at effective `max_tries=100`, but still ends in
  `HouseInvalidForTask` after downstream candidate removals.
- Phase 81 added Post-Placement Candidate Rejections. The warmed local report
  shows the exact `Book_23` request records 17 grasp-failure reports and 15
  candidate-removal calls after placement succeeds, so the remaining blocker is
  grasp/candidate feasibility rather than robot base placement.
- Phase 82 added Grasp-Feasibility Blocker classification. Proof-result
  summaries now classify the Phase 81 artifact as `grasp_feasibility` with
  `17 grasp failures; 15 candidate-removal calls`.
- Phase 83 added Grasp-Feasibility Selection Memory. Proof request selection now
  preserves that blocker kind/detail through excluded requests, generated
  fallback provenance, filtered fallback pairs, and runner report blocker views.
- Phase 84 added Cleanup-Pair Proof Memory. Prior proof results now match by
  `request_id` first, then by cleanup `object_id` plus `target_receptacle_id`,
  and runner reports show the `Prior match` kind.
- Phase 85 added Standalone Prior Proof Result Ingest. The runner can now load
  Phase 81-style standalone planner-probe `run_result.json` evidence, normalize
  it to proof-result summary, select by cleanup pair, render grasp blocker
  evidence, and check partial selection with an exhausted fallback pool.
- Phase 86 added Prior Proof Evidence View. Runner manifests now carry
  `prior_proof_result_summary`, and runner reports render consumed prior proof
  diagnostics, paths, and planner-view images before new proof commands.
- Phase 87 added Selected Proof Candidate Execution. The remaining selected
  `proof_002` bowl/sink request executed locally, passed runner checking with
  required outputs, and was classified as `grasp_feasibility` blocked with
  `17 grasp failures; 15 candidate-removal calls`.
- Phase 88 added Nested Prior Proof Evidence Carry-Forward. A Phase87
  proof-bundle manifest can now stand alone as prior input, preserving nested
  Phase81 evidence plus Phase87 proof results; the dry-run excluded both source
  requests, generated zero commands, and rendered both prior evidence rows.
- Phase 89 added Planner-Object Proof Memory. A broader 10-object MolmoSpaces
  cleanup artifact produced 10 ready proof requests and 176 robot-view images;
  the proof-bundle dry-run selected 8 new candidates while excluding the two
  known internal book/bowl blocked pairs by planner-object/public-target match.
- Phase 90 added Broader Selected Proof Execution. The executed runner bundle
  ran all 8 selected candidates with warmup and wide placement; `proof_008`
  became a strict planner-backed remote-control-to-stand proof with promoted
  cleanup binding and report-relative initial/final planner views, while the
  other 7 candidates were classified as `grasp_feasibility` blocked.
- Phase 91 added Broader Bound Proof Cleanup Rerun. The cleanup rerun consumed
  the existing `proof_008` artifact without re-executing the proof bundle,
  rendered the full visual report surface, made `observed_008` strict
  planner-backed for `nav, pick, nav, place`, and kept the global bridge
  blocked with 38 unmatched `api_semantic` subphases.
- Phase 92 added Prior Covered Proof Memory. The runner now excludes prior
  `planner_backed` + cleanup-binding-promoted requests as
  `prior_planner_proof_covered`; the dry-run against the current broader seed
  selected zero commands, excluded `proof_008` as covered, excluded nine
  grasp-infeasible requests, and rendered the prior proof views in the runner
  report.
- Phase 93 added Cleanup Report Artifact Adapter. Existing cleanup artifacts now
  regenerate `report.html` from `run_result.json` through the shared report
  underlay, so stale ignored reports do not act like a second implementation.
- Phase 120 closes the scenario-less report adapter gap. ADR-0003 visual
  artifacts without `scenario.json` now regenerate through the same shared
  underlay using a minimal public scenario shell, keeping the canonical
  `nav, pick, nav, open?, place` report rhythm without inventing private truth.
- Phase 94 added Seeded Source Pool and Proof Memory. MolmoSpaces generated-mess
  selection now uses the subprocess seed to rotate object identities while
  preserving semantic target fixtures, and proof-selection memory rejects local
  `proof_###`/`observed_###` matches when planner object identity conflicts.
  The patched seed 9 artifact validates with 10 generated objects and 44 robot
  timeline steps; prior-aware selection now picks four proof commands
  (`proof_003`, `proof_005`, `proof_006`, `proof_010`) instead of zero.
- Phase 95 added Seeded Selected Proof Execution. The four selected patched
  seed 9 proof commands executed locally through the shared proof-bundle runner
  with warmup, low RBY1M CuRobo memory, and wide placement profile. All four
  reached task sampling but remained `grasp_feasibility` blocked with
  `17 grasp failures; 15 candidate-removal calls`; no new planner-backed proof
  or cleanup-binding promotion was produced. The runner report still provides
  the visual review surface for selection, prior evidence, and proof results.
- Phase 96 added Planner Failure Diagnostic Views. Blocked task-sampler probes
  can now capture a bounded post-placement camera artifact through the same
  `image_artifacts` path used by successful initial/final planner views, and
  old diagnostic-only blocked reports render an inline task-sampler diagnostic
  view instead of an empty no-view state.
- Phase 97 added Post-Placement Rejection Views. Standalone planner reports and
  proof-bundle result cards now render grasp-failure diagnostics as a shared
  visual view, and checker gates require that visual whenever
  `task_sampler_failure_diagnostics.grasp_failures` is present.
- Phase 98 added the Grasp-Feasibility Blocker Matrix. Proof-bundle selection
  reports now render grasp-infeasible object-target pairs as visual cards before
  the detailed blocker table, and the runner checker requires the matrix when
  `grasp_feasibility_blockers` are present.
- Phase 99 added Proof-Bundle Local Runtime Preflight. Real proof-bundle
  execution now checks whether the configured MolmoSpaces Python imports
  canonical `molmo_spaces` before running warmup/proof commands, writes a
  `local_runtime_blocked` manifest/report when blocked, and renders
  `Local Runtime Preflight` evidence for the local-dev handoff.
- Phase 100 corrected the runtime preflight to the canonical upstream package
  import, `molmo_spaces`, and generated a ready local preflight report with
  zero selected proof commands.
- Phase 101 added Seeded Source Rotation Evidence. A seed 10 MolmoSpaces
  cleanup source artifact validated with 10 generated objects, 44 robot-view
  semantic steps, and 10 ready proof requests. Prior-aware dry-run selection
  picked five commands (`proof_001`, `proof_003`, `proof_005`, `proof_008`,
  `proof_010`) and excluded five requests as `prior_task_feasibility_blocked`;
  those selected commands still need a separate local execution phase before
  any new planner-backed cleanup coverage is claimed.
- Phase 102 added Seed 10 Selected Proof Execution. The five selected seed 10
  proof commands executed with local runtime preflight, RBY1M/CuRobo warmup,
  low memory, and wide placement. All five attempted proofs blocked as
  `grasp_feasibility` with 17 grasp failures, 15 candidate-removal calls, and
  one diagnostic view artifact each; none became planner-backed or promoted
  cleanup binding.
- Phase 103 added the Grasp-Feasibility Signature Matrix. Task-feasibility
  blocker naming now lives in a shared planner module, proof result summaries
  carry per-proof grasp signatures and grouped signature counts, proof-bundle
  reports render the grouped matrix, and the checker validates the view. The
  regenerated Phase 103 report groups the five Phase 102 blockers into one
  repeated signature.
- Phase 104 added Post-Execution Fallback Exhaustion for seed 10. With the
  Phase 102 executed bundle as prior memory, the dry-run selected zero commands,
  excluded all ten seed 10 requests as grasp-feasibility blockers, generated no
  fallback requests, and recorded `no_fallback_candidate_available` for all ten
  source requests.
- Phase 105 added Candidate Removal Effectiveness. The planner probe now
  records threshold-exceeded rows, candidate-removal call deltas,
  candidate-name presence before/after removal, effective-removal counts, and
  candidate-name misses; shared planner/proof-bundle reports render those
  fields so the next runtime slice can distinguish ineffective candidate
  removal from true grasp candidate exhaustion. A real Phase 105 RBY1M proof
  rerun confirmed the repeated seed-10 blocker has 17 grasp failures, 15
  removal calls, 0 effective removals, and 15 candidate-name misses.
- Phase 106 added Exact Pickup Candidate Binding. The exact sampler adapter now
  binds the live pickup candidate pool at `_select_pickup_object()` before
  upstream selection and renders the binding action in shared reports. The real
  Phase 106 rerun changed the blocker from 17 grasp failures / 15 ineffective
  removals to a direct invalid planner-object `KeyError`, with candidate count
  moving from 4 unrelated objects to the requested bread alias only.
- Phase 107 added Valid Cleanup Scene Binding. The checker can now require the
  cleanup scene XML to exist before accepting exact-scene evidence, and reports
  render exact task config blockers. A corrected seed-10 rerun with the
  canonical scene showed the requested bread alias exists: pickup binding moved
  the pool from 17 unrelated candidates to 1 exact candidate, robot placement
  succeeded, and the remaining blocker is one post-placement grasp failure
  with zero candidate-removal calls.
- Phase 108 added Exact Pickup Retry Budget. The exact sampler adapter now
  repeats the requested pickup candidate to a retry budget of 3, preserving the
  upstream default `max_failures=2` threshold path without restoring unrelated
  candidates. The valid-scene rerun produced 3 grasp failures, 1 threshold
  crossing, 1 effective candidate removal, and 0 candidate-name misses.
- Phase 109 adds Grasp Collision Diagnostics. The task-sampler diagnostics
  adapter records upstream grasp-load and non-colliding mask outcomes so the
  remaining exact-object grasp-feasibility blocker can be classified as missing
  cached grasps, zero collision-free grasps, or a hook exception. The valid-scene
  rerun classified the exact bread blocker as missing cached grasps for
  `Bread_1`: 3 grasp-load attempts, 3 `ValueError` load failures, and 0
  collision-mask checks.
- Phase 110 adds Missing Grasp Cache Signature. Proof-result summaries now keep
  `task_feasibility_blocker_kind=grasp_feasibility` but add
  `subkind=grasp_cache_missing`, failed grasp-load counts, and missing asset
  IDs such as `Bread_1` to the grouped signature matrix.
- Phase 111 adds Grasp Cache Routing Decision. Proof-bundle manifests and
  reports now route `grasp_cache_missing` evidence for `Bread_1` to
  `grasp_cache_mitigation` before exact retry, while keeping source rotation
  visible as `available_for_unproven_requests` for unrelated selected requests.
- Phase 112 adds Grasp Cache Availability Preflight. Proof-bundle manifests and
  reports now show that `Bread_1` object XML/OBJ assets are present locally but
  the rigid loader-compatible grasp cache files are missing for droid,
  droid-objaverse, and RUM sources.
- Phase 113 adds Runtime Assets Grasp Cache Preflight. The preflight now derives
  the runtime `ASSETS_DIR` from the planner scene XML and renders
  symlink-resolved missing cache targets under the local versioned grasp cache.
- Phase 114 adds Grasp Cache Validity Preflight. Reports now distinguish
  existing-but-empty rigid loader files from valid cache data; the installed
  droid `Bread_1` file is `present_but_invalid` with zero transforms.
- Phase 115 adds Semantic Cleanup Vocabulary. `semantic_timeline.py` now owns
  the raw phases, canonical surface/inside cleanup sequences, display labels,
  focused action prefixes, and loop variants used by the shared semantic loop,
  Cleanup Artifact Report, visual-core contract, and checkers.
- Phase 116 adds Grasp Cache Generation Preflight. The proof-bundle runner now
  renders the upstream rigid generation route for `Bread_1` and blocks visibly
  on missing `sklearn`, missing `python-fcl`, and missing Manifold
  `manifold`/`simplify` executables.
- Phase 117 adds Grasp Generation Setup Runner. The local MolmoSpaces runtime
  now has the rigid-path Python prerequisites and built Manifold executables,
  and the proof-bundle generation preflight reports `ready` with zero blockers.
- Phase 118 adds Grasp Cache Generation Runner. The generation path reaches
  `Bread_1` candidate grasp generation, but upstream perturbation filtering
  saves zero successful transforms, so install remains blocked and visible in
  the generation report.
- Phase 119 adds Grasp Filter Diagnostics. A bounded local diagnostic preserves
  the combined/manifold/simplified mesh, generated candidates, per-variant
  subsets, and filtered NPZ outputs. It generated 24 valid `Bread_1` candidates
  and showed zero successful transforms for `initial_contact`,
  `translation_shake`, and `upstream_like`, narrowing the next blocker to the
  initial contact/pose path inside perturbation testing.
- Phase 120 adds Report Artifact Scenario Fallback. Scenario-less ADR-0003
  cleanup artifacts now regenerate from `run_result.json` through the shared
  Cleanup Artifact Report adapter using a minimal public scenario shell, so
  stale local `report.html` files do not imply multiple report implementations.
- Phase 121 adds Grasp Initial Contact Diagnostics. A reusable MuJoCo sweep over
  the 24 preserved `Bread_1` candidates shows the upstream-sign approach remains
  zero-success, while positive-sign larger standoffs produce nonzero contacts
  without initial object displacement; the best local variant is
  `sign_1_dist_0.8_settle_1` with 9/24 successes.
- Phase 122 adds Grasp Pose Policy Cache Generation. The same MuJoCo probe now
  has cache-output mode, so the validated `sign_1_dist_0.8_settle_1` policy can
  write loader-compatible object-relative TCP transforms without creating a
  second approach implementation. The local run generated 9 valid transforms
  from 24 candidates, installed them to the droid `Bread_1` loader cache after
  generated-NPZ validation, and the post-install availability preflight returned
  `ready`.
- Phase 123 adds Cache-Ready Proof Rerun evidence. The warmed exact
  `observed_001` to refrigerator proof now loads the installed `Bread_1` droid
  cache (`cached_grasp_count=9`, `grasp_load_failure_count=0`) and finds two
  non-colliding grasps, so the prior missing-cache blocker is cleared. The
  proof remains `blocked_capability` because CuRobo reaches pre-grasp execution
  with no planned trajectory.
- Phase 124 adds Focused Report Timeline behavior. ADR-0003 raw FPV scan
  captures remain in `run_result.json`, Agent View, and Raw FPV Observations,
  but the primary Robot View Timeline now focuses on before/after and semantic
  cleanup action views so ADR-0003 artifacts keep the same first-pass visual
  rhythm as `output/molmo-agent-bridge-visual-codex/report.html`.
- Phase 125 adds CuRobo Policy Exception Context. The planner probe worker
  exception path now preserves the low-memory CuRobo profile, sampled cleanup
  task binding, promoted cleanup primitive binding, empty-or-nonempty binding
  blockers, and structured policy primitive state in top-level
  `manipulation_evidence`; reports render this as `Policy Exception
  Diagnostics`, and the checker can require it with
  `--require-policy-exception-context`. The warmed exact proof rerun at
  `output/debug-phase125-curobo-pregrasp-exception-context/run_result.json`
  returned `planner_backed` with `steps_executed=1`,
  `max_abs_qpos_delta=0.018310936580938183`, preserved CuRobo profile and exact
  cleanup binding, and no cleanup binding blockers, so the prior pre-grasp
  failure did not reproduce in the Phase 125 run.
- Phase 126 consumes that Phase 125 proof in the ADR-0003 cleanup primitive
  path. The checker now accepts bound inside-target cleanup objects that require
  `nav, pick, nav, open, place_inside`; the rerun at
  `output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json`
  marks `observed_001` to refrigerator planner-backed for 5 subphases while
  leaving 37 unmatched subphases `api_semantic`, so the report shows attached
  proof views, Cleanup Primitive Gate, Planner Cleanup Bridge, and a globally
  blocked bridge rather than a premature full cleanup claim.
- Phase 127 adds Planner Proof Quality Evidence. Attached planner proofs and
  proof bundles now classify proof strength through one shared module; cleanup
  reports render `Proof Quality`, and the ADR-0003 checker can require both
  proof-quality evidence and a minimum executed-step horizon before stronger
  cleanup claims are accepted.
- Phase 128 adds Planner Proof Quality Report Reuse. Planner-backed probe
  evidence now embeds proof quality, standalone proof reports and proof-bundle
  runner reports render `Planner Proof Quality`, and both probe and runner
  checkers can require minimum proof-quality horizons.
