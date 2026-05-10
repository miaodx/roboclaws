<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0507-autoplan-restore-20260507-162727.md -->

# MolmoSpaces Manipulation Spike

**Status:** Phase 108 exact pickup retry budget completed; next work is targeting the remaining exact-object grasp-feasibility failure before another cleanup rerun
**Created:** 2026-05-07
**Reviewed:** 2026-05-07 with `autoplan`; approved by user
**Workflow:** Matt-style plan -> autoplan -> local capability spike -> GSD
Phase 6 scaffold -> Phase 7 prompt-driven public cleanup -> Phase 8 real
MolmoSpaces/MuJoCo subprocess cleanup -> Phase 9 RBY1M visual plausibility ->
Phase 10 semantic cleanup substeps -> Phase 11 held-object carry visuals.
Phase 12 current-contract agent bridge -> Phase 13 bridge visual reports ->
Phase 14 ADR-0003 public/private cleanup -> Phase 15 Generated Mess Set scale
-> Phase 16 ADR-0003 MCP -> Phase 17 direct-agent dogfood -> Phase 18
synthetic OpenClaw Gateway viability -> Phase 19 real visual OpenClaw evidence
-> Phase 20 clean-policy semantic-loop hardening -> Phase 21 advisory scoring
-> Phase 22 raw FPV-only perception evidence -> Phase 23 planner-backed
manipulation provenance/proof gate -> Phase 24 planner runtime diagnostics ->
Phase 25 planner headless renderer -> Phase 26 cleanup planner proof
attachment -> Phase 27 cleanup planner-backed primitive gate -> Phase 28
RBY1M CuRobo target-runtime gate -> Phase 29 camera-only model-policy cleanup.
Phase 30 consolidated the shared Cleanup Artifact Report presentation so the
visual core keeps the same review shape across current-contract and ADR-0003
artifacts while still showing all contract-specific evidence. Phase 31 closed
staged RBY1M/CuRobo warmup-readiness evidence; the local target runtime still
times out at `rby1m_config_import`, so target execute-mode proof remains gated.
Phase 32 isolates Torch/CuRobo extension-cache state for the next retry instead
of mutating the global cache. It proves config import can reach
`CuroboPickAndPlacePlannerPolicy` from an output-local cache; execute mode now
blocks later on Warp API compatibility. Phase 33 plans a visible probe-local
Warp adapter before retrying target execute mode; that retry reaches
`execute_policy_run_start` and now blocks on CUDA memory pressure. Phase 34
records CUDA memory headroom as first-class report evidence before any planner
memory tuning or primitive replacement work; the latest target retry shows
about 9.1 GiB free at `execute_policy_run_start` and about 284.7 MiB free at
the OOM exception. Phase 35 adds a visible probe-local low-memory CuRobo
profile before retrying target execute mode again. That retry passes strict
standalone RBY1M/CuRobo planner-backed proof with nonzero robot-state movement;
Phase 36 moves current-contract and ADR-0003 cleanup demos through one shared
semantic cleanup loop; Phase 37 adds bridge-readiness evidence that joins the
target proof with cleanup primitive provenance. Phase 38 adds and tests the
strict planner-backed cleanup primitive executor seam behind the shared cleanup
loop. Phase 39 binds planner primitive evidence to the exact cleanup object and
target before real executor wiring. Phase 40 adds the adapter from bound
RBY1M/CuRobo proof attachments into cleanup primitive executor evidence while
blocking generic standalone proof. Phase 41 made the planner probe emit
sampled-task binding and promote cleanup primitive binding only on exact
request/sample match. Cleanup-loop primitives remain `api_semantic` until a
real object-specific executor maps ADR-0003 observed handles to upstream
sampled planner tasks and integrates target planner-backed primitives into the
cleanup subphases. Phase 42 completed the first half of that remaining bridge:
private observed-handle to planner-alias binding without leaking aliases into
Agent View or relabeling cleanup subphases. Phase 43 wires matching
probe-backed executor evidence into a bounded shared-loop cleanup attempt while
leaving default and mismatched-proof cleanup on the normal semantic path. Phase
44 adds proof-bundle coverage so a full cleanup artifact can select one bound
proof per cleaned object before passing the planner cleanup bridge. Phase 45
closes the remaining report architecture drift by centralizing visual-core
checks and routing ADR-0003 MCP robot-view capture through the shared semantic
timeline mapping. Phase 46 adds private proof request manifests and a local
runner so completed ADR-0003 cleanup artifacts can be turned into real bound
planner proof bundle runs without hand-matching aliases. Phase 47 makes that
proof-generation handoff visible in the shared cleanup report. Phase 48 adds
the corresponding visual report to the proof-bundle runner output. Phase 49
adds a checker for that runner manifest/report pair. Phase 50 moves the MCP
smoke demos onto the shared semantic cleanup loop. Phase 51 adds a dry-run
harness for repeatable proof-bundle runner command generation. Phase 52 names
the final cleanup rerun artifacts in runner manifests, reports, and checker
gates. Phase 53 adds the named local-dev execute-rerun gate for bound proof
bundles and final cleanup checker readiness. The local run executed five
RBY1M/CuRobo proofs, but final cleanup readiness remains blocked because the
sampled upstream tasks did not match the requested cleanup aliases. Phase 54
binds generated proof probes to the real cleanup scene XML and requested
planner aliases from a `molmospaces_subprocess` cleanup artifact. Local
exact-scene probes now reach upstream task sampling for the requested cleanup
objects, and the remaining blocker has narrowed to `HouseInvalidForTask` /
RBY1M robot placement infeasibility before sampled binding can promote. Phase
55 makes executed proof-bundle runner reports summarize each generated proof's
status, task-feasibility classification, cleanup binding promotion, blockers,
proof report, and planner views so fallback-selection work can consume explicit
bundle-level evidence. Phase 56 adds the first fallback-selection seam: a
runner can consume a prior proof-bundle manifest, exclude requests already known
to be RBY1M task-feasibility blocked, and report when alternate request
generation is required.
Phase 57 turns that fallback-required state into bounded private fallback
requests by preserving the cleanup object/target IDs while varying planner
aliases from observed-handle binding metadata. The runner report now renders
the generated fallback request rows and commands, but real RBY1M/CuRobo
execution still has to prove whether any generated request is feasible and can
promote cleanup primitive binding.
Phase 58 executed four generated fallback requests locally. The runner checker
passed with required proof outputs, but all four probes reported
`blocked_capability` with `timeout` at `rby1m_config_import`; no fallback reached
task sampling, planner-backed proof, cleanup binding promotion, or planner view
capture.
Phase 59 resolves the remaining report-vocabulary drift from the original
discussion: shared Cleanup Artifact Reports now use `nav`, `pick`, `nav`,
optional `open`, and `place` as primary labels while keeping
object/target/surface/inside as secondary role detail.
Phase 60 makes generated fallback timeout evidence visible in the same
proof-bundle runner report: the shared proof result summary now carries timeout
counts, execution-attempted state, last worker stage, compact worker stage
events, and stdout/stderr paths so local reports show `rby1m_config_import`
timeouts without opening each per-proof artifact.
Phase 61 adds an explicit visible RBY1M/CuRobo `config_import` warmup step to
the proof-bundle runner. When enabled, the runner records the warmup command
and artifacts, shares an output-local Torch extension cache with proof
commands, renders the warmup in `report.html`, and validates it through the
runner checker before the next generated-fallback retry.
Phase 62 ran that warmed generated fallback bundle locally. Warmup succeeded
through RBY1M/CuRobo config import, and the generated proofs no longer timed
out. All four reached task sampling, then failed with `KeyError` invalid
planner aliases (`ShelvingUnit|2|3`, `Book|surface|8|79`, `Sink|5|1|0`, and
`Bowl|surface|8|77`). The next blocker is exact-scene fallback alias validity,
not RBY1M/CuRobo warmup.
Phase 63 adds that validity gate to fallback generation. The runner now filters
upstream/display aliases containing `|` before creating executable proof
commands, renders filtered aliases in `report.html`, and checks that evidence.
The local dry-run filtered all four previously failing aliases and generated no
fallback commands, so the next blocker is discovering or deriving additional
exact-scene runtime aliases instead of retrying display IDs.
Phase 64 mines prior exact-scene `KeyError` proof outputs for runtime sibling
aliases from the valid-name list. The runner report now includes discovered
runtime aliases, filtered display aliases, generated fallback request rows, and
commands in one proof-bundle artifact. The Phase 64 dry-run generated four new
fallback commands from five discovered runtime aliases, so the next local-dev
slice is executing those commands.
Phase 65 executed those discovered runtime-sibling fallback commands locally
with RBY1M/CuRobo warmup. Warmup succeeded and all four proofs reached task
sampling with no config-import timeouts, but none became planner-backed or
promoted cleanup primitive binding. Target-sibling commands still block with
`HouseInvalidForTask`, while object-sibling commands fail as non-root bodies.
The next blocker is root-body alias validity and upstream task feasibility, not
report generation or fallback command discovery.
Phase 66 records that failed-candidate memory in the runner itself. Prior
discovered aliases carry forward from executed bundle manifests, non-root body
object aliases are filtered before command generation, and exact object/target
pairs that already hit `HouseInvalidForTask` are filtered as prior
task-feasibility-blocked pairs. The Phase 66 dry-run against the Phase 65
manifest generated two remaining commands for the untried book runtime sibling
and rendered discovered aliases, filtered aliases, filtered pairs, and commands
in one runner report.
Phase 67 executed those two remaining filtered fallback commands locally with
RBY1M/CuRobo warmup and strict proof-output checking. Both proofs reached task
sampling with no config-import timeout, but both failed with
`AssertionError: Object is not a root body` for the untried book runtime
sibling. The next blocker is deriving or validating pickup root-body aliases
before creating more object-side fallback commands.
Phase 68 carries prior filtered aliases and filtered pairs forward so the latest
executed bundle manifest is a complete prior input. The dry-run against the
Phase 67 manifest generated zero commands, rendered seven filtered aliases and
two filtered pairs, and makes the next blocker explicit: the current fallback
candidate pool is exhausted until pickup root-body aliases can be derived or
validated from a better source.
Phase 69 bakes the first root-body validity rule into fallback generation:
object-axis runtime aliases with nonzero variants are filtered as
`not_pickup_root_body_alias` before command generation, while target-axis
runtime siblings remain eligible. A dry-run against the older Phase 62 KeyError
evidence now generates only the two target-side commands and filters the
object-side non-root variants up front.
Phase 70 lets the proof-bundle runner consume multiple prior manifests at once.
The dry-run using Phase 62 KeyError evidence plus Phase 68 carried
failed-candidate memory generated zero commands while still rendering five
discovered aliases, seven filtered aliases, and two filtered pairs. The current
fallback pool is now exhausted without depending on a single chosen prior
manifest.
Phase 71 makes that exhausted pool explicit in the artifact schema and visual
report. Generated fallback selection now reports `Fallback status: exhausted`
when blocked requests remain but every candidate is filtered or unavailable,
and the runner checker validates the status.
Phase 72 adds the blocker summary for that exhausted state. The runner now
renders `Fallback Exhaustion Blockers` with stable codes for pickup root-body
alias gaps, target task-feasibility-blocked pairs, and source requests with no
remaining generated candidate.
Phase 73 handles the first object-side alias follow-up by normalizing non-root
runtime aliases back to their variant-0 pickup root alias. The current dry-run
shows those root aliases were already known, so the remaining generated
fallback blocker is target-side task-feasibility rather than a missing pickup
root alias source.
Phase 74 makes that remaining target-side blocker reviewable. Filtered fallback
pairs now carry the exact prior proof report/run-result paths and worker stage,
and prior fallback attempts merge by request ID plus planner aliases so
different runs do not overwrite distinct proof attempts.
Phase 75 adds a `Target Feasibility Blockers` report view that joins blocked
source requests and blocked generated fallback pairs into one table. The latest
dry-run shows four target blockers: two source requests without prior proof
links in the available evidence and two fallback pairs linked to Phase 65 proof
reports with `worker_exception` stage.
Phase 76 preserves exact task-sampler exception context in planner-probe worker
failures. A warmed local probe reached `execute_task_sample_start`, failed with
real `HouseInvalidForTask`, and still carried exact cleanup task config, exact
sampler adapter state, requested cleanup binding, and worker-stage evidence
into the report/checker path.
Phase 77 captures the upstream sampler failure mode behind that exception. The
warmed local report renders `Task Sampler Failure Diagnostics` with 17
robot-placement attempts, 17 asset failures for `Book_23`, and repeated
`RobotPlacementError` for
`book_be4d759484637aeb579b28e6a954b18d_1_0_8`.
Phase 78 adds a visible task-sampler robot-placement profile. The warmed local
report proves the relaxed profile changed the actual `place_robot_near` calls
from requested `max_tries=10` to effective `max_tries=50`, with radius
`[0.0, 1.2]`, safety radius `0.15`, and visibility disabled. The request still
blocks with 17 placement failures, so the next blocker is deeper scene-level
robot placement feasibility for `Book_23`, not hidden sampler defaults.
Phase 79 adds placement scene diagnostics. The warmed local report now shows
that exact `Book_23` has low local free space: 2,231 valid free map points in
the `[0.0, 1.2]m` sampling annulus, a 0.012326 free-space fraction, no free
points within 1.0m, and a nearest free point 1.111824m away.
Phase 80 adds a wide placement profile using radius `[0.0, 2.0]` and effective
`place_robot_near(max_tries=100)`. The warmed local report shows robot
placement now succeeds on all 17 attempts with zero placement failures, but the
task still ends in `HouseInvalidForTask` after downstream candidate removals.
Phase 81 captures that downstream rejection path. The warmed local report
renders `Post-Placement Candidate Rejections` with 17 grasp-failure reports and
15 candidate-removal calls after successful robot placement for the exact book
alias.
Phase 82 carries that evidence into proof-result summaries and proof-bundle
runner reports as `task_feasibility_blocker_kind=grasp_feasibility` with
`17 grasp failures; 15 candidate-removal calls`, so future selection can filter
grasp-infeasible exact aliases without parsing nested diagnostics.
Phase 83 carries that blocker kind/detail into proof request selection memory:
excluded requests, generated fallback provenance, filtered fallback pairs, and
a dedicated `Grasp Feasibility Blockers` runner report view.
Phase 84 makes that memory robust across regenerated proof manifests by matching
prior proof results by `request_id` first and then by cleanup `object_id` plus
`target_receptacle_id`, with `Prior match` rendered in runner reports.
Phase 85 lets that selection memory consume standalone planner-probe
`run_result.json` artifacts directly by normalizing them into the same
proof-result summary interface as prior proof-bundle manifests.
Phase 86 makes that consumed prior evidence visible in runner reports as
`Prior Proof Evidence`, preserving diagnostic rows, proof paths, and planner
view images when present before new proof commands are reviewed.
Phase 87 executed the remaining selected `proof_002` bowl/sink request. It also
blocked as `grasp_feasibility` with `17 grasp failures; 15 candidate-removal
calls`, so the next work must generate or discover a different exact-scene
candidate rather than retrying the two known blocked source requests.
Phase 88 carries nested prior proof evidence forward when a later proof-bundle
manifest is reused as the next prior input. The Phase88 dry-run uses only the
Phase87 manifest, preserves nested Phase81 evidence plus Phase87 proof results,
excludes both source requests, generates zero commands, and renders both prior
evidence rows in the same proof-bundle runner report.
Phase 89 scopes proof-selection memory by internal planner object plus public
target after guarded request-ID and cleanup-pair matching. A broader 10-object
MolmoSpaces cleanup artifact produced 10 ready proof requests and 176
robot-view images; the dry-run selected 8 new exact-scene candidates while
excluding only the two known grasp-infeasible internal book/shelf and bowl/sink
pairs.
Phase 90 executed those 8 selected broader candidates locally with
RBY1M/CuRobo warmup and the wide placement profile. Seven candidates remained
`grasp_feasibility` blocked, while `proof_008` passed as strict
planner-backed remote-control-to-stand evidence, promoted cleanup binding for
`nav, pick, nav, place`, and rendered report-relative initial/final planner
views in the shared runner report.
Phase 91 reran final cleanup with the existing `proof_008` result, without
re-executing the proof bundle. The cleanup report now shows `observed_008` as
strict planner-backed for `nav, pick, nav, place`, renders 44 robot timeline
steps plus attached planner proof views, and keeps the global bridge blocked
because the other 38 cleanup subphases remain `api_semantic`.
Phase 92 prevents the next proof expansion from retrying solved work:
proof-bundle selection now excludes prior `planner_backed` requests that also
promoted cleanup binding. The dry-run against the current broader seed selected
zero commands, excluded `proof_008` as `prior_planner_proof_covered`, excluded
nine grasp-infeasible requests, and rendered the prior proof views in the
runner report. The next slice should rotate to a different broader cleanup
source artifact rather than rerunning this seed.
Phase 93 closes the stale-report architecture gap: a Cleanup Report Artifact
Adapter can now regenerate `report.html` from an existing cleanup
`run_result.json` through the shared underlay. The referenced stale
`output/molmo-agent-bridge-visual-codex/report.html` was repaired locally to
show the canonical visual core and semantic subphase rails
`nav, pick, nav, open?, place`, then passed the agent-bridge checker.
Phase 94 closes the source-rotation identity gap: MolmoSpaces generated-mess
selection now uses the subprocess seed to choose different eligible objects on
the same fixed scene, and proof-selection memory rejects local `proof_###` /
`observed_###` matches when planner object identity conflicts. The patched seed
9 artifact selected four new proof commands after prior-memory filtering.
Phase 95 executed those four selected proof commands. All four reached task
sampling with the wide placement profile but remained `grasp_feasibility`
blocked with `17 grasp failures; 15 candidate-removal calls`, so no new
planner-backed cleanup primitive coverage is available for a cleanup rerun yet.
Phase 96 closes the blocked-proof report visual gap: task-sampler failures can
now emit bounded post-placement camera artifacts through the same
`image_artifacts` interface as successful initial/final planner views, while
older diagnostic-only artifacts render an inline task-sampler diagnostic view
instead of an empty no-view state.
Phase 97 adds the specific visual view for the current grasp-feasibility
blocker: standalone planner reports and proof-bundle result cards now render
post-placement grasp failures, candidate removals, threshold removals, and
candidate-count movement from the same shared report helper.
Phase 98 adds the selection-level companion view: proof-bundle reports now show
grasp-infeasible object-target pairs as a `Grasp Feasibility Blocker Matrix`
before the detailed blocker table, so source-rotation decisions are visually
reviewable.
Phase 99 adds a local-dev runtime preflight before real proof-bundle execution.
If the configured MolmoSpaces Python cannot import canonical `molmo_spaces`,
the runner writes a `local_runtime_blocked` manifest/report with
`Local Runtime Preflight` evidence instead of failing before report generation.
Phase 100 corrects that preflight to the actual upstream package import
(`molmo_spaces`) and records ready local preflight evidence with zero selected
proof commands against the current seeded source plus prior memory.
Phase 101 records the next source-rotation step. A seed 10 cleanup source
artifact validated with 10 generated objects, 44 robot-view semantic steps, and
10 ready proof requests. Prior-aware dry-run selection produced five commands
(`proof_001`, `proof_003`, `proof_005`, `proof_008`, `proof_010`) while
excluding five requests as `prior_task_feasibility_blocked`. The next slice
should execute those selected commands locally, then only rerun cleanup if any
selected proof becomes planner-backed and promotes cleanup binding.
Phase 102 executed those five selected seed 10 proof commands locally with
runtime preflight, RBY1M/CuRobo warmup, low memory, and wide placement. All
five attempts produced proof outputs and diagnostic views, but every request
blocked as `grasp_feasibility` with 17 grasp failures and 15 candidate-removal
calls. No new planner-backed proof or cleanup-binding promotion was produced,
so the next slice should target the shared grasp-feasibility blocker rather
than rerunning cleanup.
Phase 103 makes that repeated blocker easier to reason about before the next
runtime experiment. Task-feasibility blocker naming moved into a shared planner
module, proof result summaries now carry per-proof grasp signatures and grouped
signature counts, and proof-bundle reports render a `Grasp Feasibility
Signature Matrix`. The regenerated Phase 103 report groups all five Phase 102
proof blockers into one repeated signature, so the next slice can target that
shared blocker pattern directly.
Phase 104 closes the seed 10 source pool after execution evidence. A
post-execution fallback dry-run using the Phase 102 bundle as prior memory
selects zero commands, excludes all ten seed 10 requests as grasp-feasibility
blocked, generates zero fallback requests, and records
`no_fallback_candidate_available` for all ten source requests. The next slice
should either reduce the shared grasp-feasibility blocker or rotate to a new
source with a different candidate strategy.
Phase 105 closes the blocker-explanation gap inside the repeated
grasp-feasibility signature. The planner probe now records whether each
threshold-triggered `_remove_candidate_object()` call actually finds and
removes the requested name from upstream `candidate_objects`, and shared
planner/proof-bundle reports render effective-removal counts, candidate-name
misses, threshold state, and removal-call deltas. The real Phase 105 probe
confirmed the seed-10 bread-to-refrigerator blocker has 17 grasp failures, 15
removal calls, 0 effective removals, and 15 candidate-name misses, so the next
slice should target candidate identity binding, proof candidate source
rotation, or a grasp-feasibility mitigation.
Phase 106 closes the candidate identity binding slice. The exact cleanup
sampler adapter now binds the live pickup candidate pool at
`_select_pickup_object()` rather than reset-time, and shared planner/proof
reports render the exact pickup action plus before/after candidate counts. The
real Phase 106 bread-to-refrigerator rerun injected the requested bread alias,
moving the pickup pool from 4 unrelated candidates to 1 exact candidate with 0
grasp failures and 0 removal calls. The remaining blocker is now a direct
`KeyError` invalid planner object name, so the next slice should fix proof
candidate source / runtime object alias validity before another cleanup rerun.
Phase 107 closes the stale scene evidence gap behind that invalid-alias result.
The planner checker now has a `--require-cleanup-scene-bound` gate, shared
reports render exact task config blockers, and the corrected local rerun uses
the canonical seed-10 cleanup scene XML. With the valid scene bound, the
requested bread alias exists: pickup binding moves the candidate pool from 17
unrelated candidates to 1 exact candidate, robot placement succeeds with one
diagnostic view, and the remaining blocker is one post-placement grasp failure
with zero candidate-removal calls.
Phase 108 preserves upstream grasp-threshold semantics after exact pickup
binding. The adapter repeats the requested pickup candidate to a retry budget
of 3 while keeping unrelated candidates out of the pool, and shared reports
render that budget. The valid-scene rerun now records 3 grasp failures, one
threshold crossing, 1 candidate-removal call, 1 effective removal, and 0
candidate-name misses. The remaining blocker is cleanly the exact object's
grasp feasibility.

## Why This Exists

Roboclaws is shifting its strategic center from direct VLM game loops toward
OpenClaw / coding-agent robot control through a small tool contract.

AI2-THOR remains the stable baseline and regression backend. MolmoSpaces is the
future-default substrate for manipulation work because it has richer scenes,
manipulable objects, grasp data, and a path toward MuJoCo / ManiSkill / Isaac.

This spike should prove a single coding agent can run the visible cleanup task
`帮我收拾这个房间` through a small MolmoSpaces-backed tool contract before we
attempt OpenClaw, hardware, or multi-agent work on the new substrate.

## Operating Decisions

- Use a dual-backend transition: keep AI2-THOR, add MolmoSpaces.
- Direct coding-agent MCP path comes first.
- OpenClaw path comes second after direct MCP works.
- Territory/coverage stay AI2-THOR-only until the one-agent MolmoSpaces cleanup
  demo works well.
- Room randomization happens before the run, outside MCP.
- The first public proof is cleanup-first, not a separate pick/place milestone.
- MolmoSpaces API-backed semantic manipulation is acceptable for v0, but every
  artifact must disclose whether each primitive used `real`, `api_semantic`,
  `scripted`, or `shim` behavior.
- Navigation comes inside the demo path. `goto` is acceptable; add other
  abilities only when the cleanup loop exposes a real gap.
- Split-model navigation work is paused until this path proves useful.
- Do not build a broad backend-neutral simulator abstraction before the
  MolmoSpaces API shape is known.

## Capability Gate

Do not ingest this plan into GSD until the cleanup-first capability spike proves
the APIs below on the target local workstation.

| Capability | Must prove | Evidence |
| --- | --- | --- |
| Install/runtime | MolmoSpaces and the chosen sim path import and run locally. | Command log with versions and any required extras. |
| Scene load/reset | A deterministic scene can be loaded and reset by seed. | Minimal script plus run directory. |
| Object inventory | Objects and receptacles can be listed with stable IDs/types. | Sample `scene_objects` payload. |
| Camera frames | Before/after images can be captured for reports. | Saved image artifacts. |
| State readback | Final object/receptacle state can be scored after actions. | Sample state dump used by scorer. |
| Semantic manipulation | Object state can be changed through MolmoSpaces APIs or a clearly-labeled temporary shim. | Primitive provenance recorded in trace and `run_result.json`. |
| Cleanup scoring | Seeded misplaced objects can be scored against private valid receptacles. | Sample scorer input/output with private manifest kept out of MCP context. |
| Failure semantics | Failed/stale/impossible actions return explicit errors. | Example failure payloads. |

If any required capability is missing, stop after the spike, document the
blocker, and do not fake the cleanup demo as a successful MolmoSpaces result.

### Local Capability Spike Result - 2026-05-07

The capability spike ran locally against upstream `allenai/molmospaces` main at
commit `3c50ae6093f7e4a4ef32529f8a773715da410a2f`.

Environment result:

- Roboclaws' repo `.venv` is Python `3.10.19`; upstream MolmoSpaces requires
  Python `>=3.11`, so the integration must use an isolated Python 3.11 runtime
  until or unless Roboclaws raises its Python floor.
- Isolated setup succeeded with
  `uv venv --python 3.11 /tmp/roboclaws-molmospaces-spike/.venv` and
  `uv pip install --python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --torch-backend cpu -e ".[mujoco]"`.
- Installed versions: `molmo-spaces 0.0.1`, `mujoco 3.4.0`,
  `molmospaces-resources 0.0.1b4`.
- A minimal MuJoCo EGL render produced a `(64, 64, 3) uint8` RGB frame. This
  proves the local workstation can render headless MuJoCo frames without
  involving AI2-THOR or a real VLM.

API/resource result:

| Capability | Result | Evidence |
| --- | --- | --- |
| Install/runtime | Passed with an isolated Python 3.11 venv; blocked for the repo Python 3.10 venv. | Upstream `pyproject.toml` requires `>=3.11`; local install/import succeeded in `/tmp/roboclaws-molmospaces-spike/.venv`. |
| Scene load/reset | Passed for a tiny on-demand ProcTHOR val scene. | `get_scenes("procthor-10k", "val")` found `val_0.xml`; `install_scene_from_source_index("procthor-10k-val", 0)` installed `procthor-10k-val_val_0.tar.zst`; `mujoco.MjModel.from_xml_path(...)` loaded 415 bodies, 3492 geoms, 129 joints, and `mj_resetData` restored `qpos` exactly. |
| Object inventory | Passed from scene metadata and MuJoCo model state. | `get_scene_metadata(val_0.xml)` returned 140 objects; top categories included `Pencil`, `Chair`, `Pen`, `CellPhone`, `Television`, `Plate`, and `Cup`. |
| Camera frames | Passed at MuJoCo renderer level. | `mujoco.Renderer(...).render()` returned RGB frames for both a toy model and the loaded MolmoSpaces scene. |
| State readback | Passed at MuJoCo state level. | Free-joint object positions are readable through `data.xpos` and `data.qpos`; `ladle_...` moved by `delta_x=0.1` after a controlled `qpos` edit and `mj_forward`. |
| Semantic manipulation | Partially passed as `api_semantic`, not as real robot manipulation. | Direct MuJoCo free-joint edits can move objects and be scored, but that must be labeled `api_semantic`; RBY1M/Franka planner-backed pick/place remains unproven for this demo. |
| Cleanup scoring | Ready for implementation, not upstream-provided as the Roboclaws scenario. | Upstream benchmark schemas cover pick, pick/place, open/close, and nav-to-object episode specs; Roboclaws still needs its private valid-receptacle manifest and 3-of-5 scorer. |
| Failure semantics | Passed at ID lookup level. | `mujoco.mj_name2id(..., "missing-object-id") == -1`; the MCP layer should translate that into `stale_reference` rather than success. |

Operational finding:

- Avoid broad MolmoSpaces config imports during normal Roboclaws startup. A
  config-instantiation probe triggered the resource manager and pulled about
  5 GB into `~/.cache/molmo-spaces-resources`, mostly `objects/thor`,
  `objathor_metadata`, `grasps/droid`, and all robot packages. The first
  implementation slice must use an explicit pinned resource manifest and
  on-demand scene installation only.
- The aborted config probe briefly left the MolmoSpaces cache manifest missing
  the `grasps/droid: 20251116` entry; the local manifest was repaired before
  continuing. Treat this as evidence that demo setup scripts must be
  idempotent and must fail before partial bulk downloads when a manifest is too
  broad.

GSD handoff decision:

- The original "identify actual APIs" gate is satisfied for a narrow first
  GSD phase: fake-backend contracts, private scorer, report schema, and a
  direct MCP cleanup server that uses `api_semantic` object moves against
  MolmoSpaces/MuJoCo state.
- Do not claim real robot manipulation yet. A later local-dev acceptance gate
  must separately prove planner-backed RBY1M or Franka pick/place before any
  artifact uses `primitive_provenance="real"`.
- Do not make Roboclaws import MolmoSpaces at top level. Keep it behind an
  optional subprocess/extra or adapter boundary so the existing AI2-THOR paths
  and CI stay Python 3.10-safe.

### Phase 6 Implementation Result - 2026-05-07

The narrow GSD phase shipped the first cleanup artifact loop:

- `roboclaws/molmo_cleanup/` defines the public/private scenario contract,
  private scorer, API-semantic backend, direct-call MCP-style contract, and
  report renderer.
- `examples/molmospaces_cleanup_demo.py` runs a deterministic scripted cleanup
  and writes `trace.jsonl`, `run_result.json`, `scenario.json`,
  `private_manifest.json`, `before.png`, `after.png`, and `report.html`.
- `just harness::molmo-cleanup` and `just verify::molmo-cleanup` are the focused
  harness and verify gates for this pilot.
- `.planning/phases/06-molmospaces-api-semantic-cleanup/06-VERIFICATION.md`
  records the verification evidence.

Latest harness result:

| Field | Value |
| --- | --- |
| Artifact dir | `output/molmo-cleanup-harness/` |
| Scenario | `molmo-cleanup-default-7` |
| Cleanup status | `success` |
| Restored objects | `5/5` |
| Success threshold | `3/5` |
| Primitive provenance | `api_semantic` |
| Planner | `scripted_reference` |

Boundary:

- This is still not real robot manipulation. It proves the direct cleanup
  artifact contract, private scoring, reports, and provenance labeling.
- The scripted reference demo uses the private manifest to choose targets, so it
  is harness proof of the contract, not autonomous policy performance.
- MolmoSpaces itself remains behind a future optional Python 3.11 adapter or
  subprocess boundary; this phase keeps the repo Python 3.10-safe.

### Phase 7 Prompt-Driven Cleanup Result - 2026-05-07

The follow-up GSD phase closed the gap between "scripted scaffold" and
"prompt-driven cleanup proof" for the easy semantic scenario:

- `roboclaws/molmo_cleanup/policy.py` defines a public-only cleanup policy that
  consumes task text plus public `scene_objects` data.
- `examples/molmospaces_cleanup_demo.py --planner public_heuristic --task
  "帮我整理这个房间"` runs the cleanup loop without using the private manifest as
  planner input.
- `just harness::molmo-prompt-cleanup` and
  `just verify::molmo-prompt-cleanup` are the focused prompt-proof gates.
- `.planning/phases/07-molmospaces-prompt-driven-cleanup-demo/07-VERIFICATION.md`
  records the verification evidence.

Latest prompt harness result:

| Field | Value |
| --- | --- |
| Artifact dir | `output/molmo-prompt-cleanup-harness/` |
| Task prompt | `帮我整理这个房间` |
| Scenario | `molmo-cleanup-default-7` |
| Cleanup status | `success` |
| Restored objects | `5/5` |
| Success threshold | `3/5` |
| Planner | `public_heuristic` |
| Planner uses private manifest | `false` |
| Primitive provenance | `api_semantic` |

Boundary:

- This is now prompt-driven through public room/tool state, not private-manifest
  scripted planning.
- It is still not a real VLM/OpenClaw policy and still not real robot
  manipulation; primitive execution remains `api_semantic`.
- The next meaningful pipeline stage is either a real coding-agent/OpenClaw
  policy proof over this same public contract or a Python 3.11 MolmoSpaces
  subprocess adapter.

### Phase 8 Real MolmoSpaces Subprocess Result - 2026-05-07

The follow-up GSD phase closed the fake/shim/backend gap in the prompt cleanup
artifact:

- `roboclaws/molmo_cleanup/subprocess_backend.py` shells the Python 3.10 repo
  process into the isolated Python 3.11 MolmoSpaces runtime at
  `/tmp/roboclaws-molmospaces-spike/.venv/bin/python`.
- `scripts/molmospaces_subprocess_worker.py` loads upstream
  `procthor-10k-val` scene index 0 through MolmoSpaces resource installation,
  then loads the resulting MJCF into MuJoCo.
- The worker builds public `observe` / `scene_objects` data from real
  MolmoSpaces scene metadata plus MuJoCo state readback, while the private
  manifest remains scorer-only.
- `place` uses `api_semantic` direct MuJoCo free-joint `qpos` mutation against
  the loaded real scene. This is not planner-backed robot manipulation, so it is
  deliberately not labeled `real`.
- `just harness::molmo-real-cleanup` and `just verify::molmo-real-cleanup` are
  the focused real-runtime gates.
- `.planning/phases/08-molmospaces-real-subprocess-cleanup/08-VERIFICATION.md`
  records the verification evidence.

Latest real-runtime harness result:

| Field | Value |
| --- | --- |
| Artifact dir | `output/molmo-real-cleanup-harness/` |
| Backend | `molmospaces_subprocess` |
| Runtime | Python `3.11.14`, MuJoCo `3.4.0` |
| Scene | upstream `procthor-10k-val` scene index `0` |
| Scene stats | 140 metadata objects, 415 MuJoCo bodies, 3492 geoms, 129 joints |
| Task prompt | `帮我整理这个房间` |
| Cleanup status | `success` |
| Restored objects | `5/5` |
| Success threshold | `3/5` |
| Planner | `public_heuristic` |
| Planner uses private manifest | `false` |
| Primitive provenance | `api_semantic` |
| Required artifacts | `before.png`, `after.png`, `trace.jsonl`, `run_result.json`, `report.html` |

Boundary:

- This now satisfies the real upstream MolmoSpaces/MuJoCo scene requirement for
  the semantic cleanup proof.
- It still does not prove RBY1M/Franka planner-backed pick/place. Future
  artifacts may use `primitive_provenance="real"` only after that planner-backed
  path is proven.
- It is still a deterministic public heuristic, not an OpenClaw/VLM policy.
  OpenClaw integration remains a separate follow-up.

### Phase 9 RBY1M Visual Plausibility Result - 2026-05-08

The follow-up GSD phase made the real MolmoSpaces run reviewable from the
robot's perspective:

- `--include-robot --robot-name rby1m --record-robot-views` adds FPV, chase,
  map, and public verification views for the cleanup timeline.
- Target-facing base yaw and target-framing head pitch make focused FPV frames
  face the current object or receptacle.
- Same-room stand-off selection is checked against MuJoCo room outlines.
- `just verify::molmo-robot-visual` is the focused RBY1M visual gate.
- `.planning/phases/09-molmospaces-fpv-room-plausibility/09-VERIFICATION.md`
  records the verification evidence.

Boundary:

- This is still `api_semantic` manipulation, not planner-backed robot
  pick/place.
- The visual verification camera is a public MuJoCo state-report aid, not a
  private manifest view.

### Phase 10 Semantic Cleanup Substeps Result - 2026-05-08

The follow-up GSD phase replaced the coarse cleanup loop with object-level
semantic substeps:

- Each target records `navigate_to_object -> pick -> navigate_to_receptacle ->
  place/place_inside -> object_done`.
- Fridge targets record `open_receptacle` before `place_inside`.
- The apple is placed inside the real fridge state, with final containment
  recorded as `contained_in=<fridge id>` and `location_relation=inside`.
- `run_result.json` records `semantic_loop_variant`,
  `semantic_substeps`, and `final_containment`.
- The robot report shows semantic phase badges and suppresses the misleading
  Verification panel for non-focused `before`, `observe`, `scene_objects`, and
  `after` rows.
- `just harness::molmo-real-cleanup` and `just verify::molmo-robot-visual`
  both pass with `backend=molmospaces_subprocess`, `planner=public_heuristic`,
  and `planner_uses_private_manifest=false`.
- `.planning/phases/10-molmospaces-semantic-substeps/10-VERIFICATION.md`
  records the verification evidence.

Latest semantic-substep harness result:

| Field | Value |
| --- | --- |
| Real artifact dir | `output/molmo-real-cleanup-harness/` |
| Robot visual artifact dir | `output/molmo-robot-visual-harness/` |
| Backend | `molmospaces_subprocess` |
| Runtime | Python `3.11.14`, MuJoCo `3.4.0` |
| Task prompt | `帮我整理这个房间` |
| Cleanup status | `success` |
| Restored objects | `5/5` |
| Planner | `public_heuristic` |
| Planner uses private manifest | `false` |
| Primitive provenance | `api_semantic` |
| Semantic loop | `navigate-pick-navigate-open-place-object_done` |
| Robot view steps | `25` |
| Apple final relation | `inside` refrigerator |

Boundary:

- This completes the current public semantic cleanup demo. It still does not
  prove RBY1M/Franka planner-backed pick/place, so `primitive_provenance="real"`
  remains deferred.
- It is still a deterministic public heuristic, not a real VLM/OpenClaw policy.

### Phase 11 Held-Object Carry Visuals Result - 2026-05-08

The follow-up GSD phase fixed the mismatch where the semantic state said an
object was held, but the rendered object stayed at the pickup pose while RBY1M
navigated to the target receptacle:

- `navigate_to_receptacle` now moves the held object's real MuJoCo free-joint
  qpos to a robot-relative held pose whenever RBY1M changes pose.
- `open_receptacle` does the same after moving RBY1M to the opened-fridge access
  pose, so the held apple follows the robot before `place_inside`.
- Tool responses record
  `state_mutation=robot_base_qpos+held_object_freejoint_qpos` for carried
  navigation and
  `mujoco_receptacle_joint_qpos+robot_base_qpos+held_object_freejoint_qpos` for
  fridge opening.
- The visual checker now requires held-object `navigate_to_receptacle` rows to
  have positive FPV object pixels and verifies the object position is the
  expected robot-relative held pose.
- `.planning/phases/11-molmospaces-held-object-carry-visuals/11-VERIFICATION.md`
  records the verification evidence.

Latest carried-object visual evidence from
`output/molmo-robot-visual-harness/run_result.json`:

| Row | Object | FPV object pixels | Robot-relative error |
| --- | --- | ---: | ---: |
| `0005_navigate_receptacle_1` | Apple | `1917` | `0.0` |
| `0010_navigate_receptacle_2` | Book | `22602` | `0.0` |
| `0014_navigate_receptacle_3` | Bowl | `18569` | `0.000001` |
| `0018_navigate_receptacle_4` | Pillow | `38946` | `0.0` |
| `0022_navigate_receptacle_5` | RemoteControl | `3798` | `0.0` |

Boundary:

- This improves visual/semantic consistency for the `api_semantic` demo. It is
  still not planner-backed RBY1M/Franka manipulation, so
  `primitive_provenance="real"` remains deferred.
- The planner remains deterministic `public_heuristic` and public-only:
  `planner_uses_private_manifest=false`.

## Upstream Findings

Checked against upstream MolmoSpaces docs/source on 2026-05-07:

- MuJoCo is the primary runtime for this spike. MolmoSpaces supports classic
  MuJoCo and optional MuJoCo Filament installs, and upstream currently states
  data generation and benchmarking are only supported for MuJoCo.
- ManiSkill is useful as a future rendering/loading path because the upstream
  `molmo_spaces_maniskill` package can load MolmoSpaces MJCF assets and scenes
  into SAPIEN/ManiSkill, but it is not the first execution backend for our
  coding-agent MCP demo.
- Isaac Sim / Isaac Lab remain deferred because they are heavier than needed for
  this demo.
- The full Hugging Face dataset is large. Use a pinned micro-set and on-demand
  asset install; never require the whole dataset for a Roboclaws demo.
- Upstream task support maps well to our cleanup-first direction: `PickTask`,
  `PickAndPlaceTask`, `PickAndPlaceNextToTask`, `PickAndPlaceColorTask`,
  `OpeningTask`, `DoorOpeningTask`, and `NavToObjTask`.
- Upstream includes mobile manipulation robots: `RBY1` and `RBY1M` are the best
  fit for Roboclaws' "moving robot with arm(s)" story. `RBY1M` is the preferred
  demo embodiment because it is a mecanum-wheel mobile manipulator / humanoid
  form. Unitree G1-like humanoids are not native in MolmoSpaces today and should
  remain future custom integration work.

Observed small-set download sizes from the public Hugging Face tree on
2026-05-07, before decompression:

| Resource | Approx. archive size | Use |
| --- | ---: | --- |
| `mujoco/scenes/procthor-10k-val/20251217` | 82 MB | First small procedural scene pack. |
| `mujoco/scenes/ithor/20251217` | 540 MB | Hand-authored rooms with articulated assets. |
| `mujoco/robots/rby1/20251224` | 8 MB | Mobile humanoid-style robot. |
| `mujoco/robots/rby1m/20251224` | 11 MB | Preferred mecanum-wheel mobile manipulator. |
| `mujoco/robots/franka_droid/20260127` | 43 MB | Fallback official pick/place benchmark robot. |
| `mujoco/objects/thor/20251117` | 1.6 GB | Avoid initially unless adding standalone objects outside the chosen scene. |
| `mujoco/grasps/droid/20251116` | 384 MB | DROID/Franka grasp annotations. |

The capability spike should record actual disk use after extraction because
archive granularity and lazy-linking behavior may change upstream.

## Demo Scenario Shortlist

Use this order; do not start with a broad "all rooms" setup.

| Priority | Scenario | Scene set | Robot | Why |
| --- | --- | --- | --- | --- |
| 1 | Cleanup: `帮我收拾这个房间` | one iTHOR or ProcTHOR room with 5 seeded misplaced objects | RBY1M target; Franka fallback if needed | The public "wow, it works" proof for robot-agent developers. |
| 2 | One-room navigation-to-object: "Go to the mug/book." | `procthor-10k-val`, same house | RBY1/RBY1M | Bring-up helper for camera, base movement, and object inventory if cleanup exposes nav gaps. |
| 3 | Articulation: "Open the drawer/cabinet/fridge." | `ithor`, one kitchen/office room | RBY1M or Franka fallback | Add only if cleanup needs visible open/close abilities. |
| 4 | One-room pick/place: "Pick up the book/cup and place it on the table." | `procthor-10k-val`, one `house_inds` value | RBY1M if planner works; Franka fallback | Internal debugging fallback, not a standalone milestone. |
| 5 | Two-room cleanup | one small ProcTHOR house with two rooms | RBY1M | Only after single-room cleanup works. |

Avoid for the first demo:

- `holodeck` and `procthor-objaverse` scene sets. They are good later, but they
  pull us toward Objaverse-scale dependencies and more visual variability.
- Full benchmark sweeps. Use benchmark task definitions as examples, not as the
  first Roboclaws product surface.
- G1-like humanoids. Use RBY1M now; revisit G1 after the MCP/scenario/scoring
  path works.

## Small Asset Strategy

The demo must work from a tiny pinned asset manifest, not from a full dataset
install.

Start with this target bundle:

```text
roboclaws-molmo-demo-v0/
  scenes:
    - procthor-10k-val: one selected house
    - ithor: one selected articulated room, only if needed for open/close
  objects:
    - prefer objects already embedded/referenced by the selected scenes
    - install standalone thor objects only if the cleanup randomizer needs them
  robots:
    - rby1m
    - franka_droid fallback
  grasps:
    - omit initially unless MolmoSpaces API-backed cleanup requires them
```

Capability spike requirements:

- Pin exact upstream asset versions in a small manifest.
- Record archive size and extracted disk size.
- Verify that the selected scenes load without installing unrelated scene sets.
- Prefer `install_scene_with_objects_and_grasps_from_path(...)` or equivalent
  on-demand installation over bulk download.
- If upstream archive granularity still downloads a larger source shard, record
  it honestly and keep the selected shard count minimal.
- First attempt should use scene-existing objects only; adding standalone objects
  is a second step because it may pull the larger object bank.

## Renderer And Embodiment Choice

Default path:

1. **MuJoCo classic** for the capability spike and CI-adjacent fake-backend
   contracts.
2. **MuJoCo Filament** for nicer public screenshots/reports if the install is
   stable on the local workstation.
3. **ManiSkill** only as a follow-up visual/runtime comparison after the MuJoCo
   MCP path works.
4. **Isaac Sim / Isaac Lab** deferred.

Robot path:

1. **RBY1M** is the target embodiment for the visible Roboclaws demo because it
   is a moving robot with arms and fits the household cleanup story.
2. **RBY1** is acceptable for mobile navigation and object-search checks.
3. **Franka DROID / Franka FR3** remain fallback bring-up robots because they
   align with upstream pick/place benchmarks.
4. **G1-like humanoid** remains future work. It likely requires importing an
   external MuJoCo model, creating robot config/view/controller bindings, and
   designing locomotion or whole-body-control assumptions before it can be a
   credible Roboclaws demo.

## Architecture Shape

```text
scripts/prepare_molmospaces_room.py
        |
        v
output/runs/<id>/scenario.json  +  private scoring manifest
        |
        v
MolmoSpaces MCP entry point
        |
        +--> observe / scene_objects / goto / pick / place / open / close / done
        |
        v
Coding agent skill
        |
        v
trace.jsonl + run_result.json + report.html
        |
        v
state-delta scorer
```

The tool contract is the abstraction boundary. Keep implementation narrow until
the capability gate has real API facts.

## Initial MCP Surface

Keep the tool surface small:

- `observe(label="")`
- `scene_objects(filter_types="")`
- `goto(object_id | location_id, distance=...)`
- `pick(object_id)`
- `place(receptacle_id | location_id)`
- `open(object_id)`
- `close(object_id)`
- `done(reason)`

Contract requirements:

- Tool responses must use stable object/receptacle identifiers or return an
  explicit stale-reference error.
- `scene_objects` must support filtering/truncation so large scenes do not flood
  agent context.
- The server should bind loopback-only by default.
- The private scoring manifest must never be exposed through MCP or copied into
  agent prompt context.
- Timeout/no-progress must be an explicit terminal status, not success.
- Manipulation responses must include a provenance field:
  `real`, `api_semantic`, `scripted`, or `shim`.

## First Demo: Cleanup-First Semantic Manipulation

Goal: natural-language room cleanup that is impressive as a runnable demo and
honest as an engineering artifact.

Example:

```text
帮我收拾这个房间
```

Expected tool flow:

```text
observe -> scene_objects -> goto -> pick/place/open/close as needed -> observe -> done
```

Pre-run setup should create a seeded messy room, outside MCP:

```bash
python scripts/prepare_molmospaces_room.py \
  --scenario cleanup-room \
  --seed 7 \
  --messiness easy \
  --output output/runs/<id>/scenario.json
```

Private scoring manifest example:

```json
{
  "misplaced": [
    {
      "object_type": "Book",
      "start": "floor",
      "valid_targets": ["Bookshelf", "Desk", "CoffeeTable"]
    },
    {
      "object_type": "Cup",
      "start": "floor",
      "valid_targets": ["Table", "CounterTop"]
    }
  ]
}
```

The agent must not see this private manifest. It should infer the room state
through `observe` and `scene_objects`.

Pass criteria:

- At least 3 of 5 misplaced objects move to valid receptacles.
- No high-severity failure: lost object, impossible placement marked as success,
  or timeout with no progress.
- `trace.jsonl` records all tool calls, result status, state delta, and
  primitive provenance.
- `run_result.json` records backend, scenario id, seed, final status, artifact
  paths, score summary, and primitive provenance summary.
- `report.html` shows initial room, final room, restored/missed object table,
  primitive provenance, and tool trace.
- The report states whether `pick` / `place` / `open` / `close` used real
  MolmoSpaces behavior, API-backed semantic manipulation, a scripted planner, or
  a temporary shim.
- A robot-agent developer can rerun the demo through the existing
  `just code::codex` / `just code::cc` workflow shape.

## Task Slices

These are approved vertical slices. The capability spike made the first GSD
handoff concrete enough to proceed for the narrow `api_semantic` cleanup path;
Phase 7 then added the prompt-driven public-policy proof.

1. **Cleanup capability spike**
   Completed locally on 2026-05-07. Keep the result in this plan as source
   context; do not repeat broad config-instantiation probes in GSD.

2. **Provenance and fake-backend contract**
   Define the primitive provenance enum and fake-backend response shapes before
   real MolmoSpaces code. Reuse existing trace/report patterns where possible
   and keep additive compatibility with current trace consumers. This is the
   first GSD implementation slice.

3. **Scenario builder and scoring**
   Add seeded room messiness outside MCP, private manifest, state-delta scoring,
   and report rendering. Use `tdd` for manifest parsing, scorer behavior, and
   privacy boundaries.

4. **Direct MCP cleanup demo**
   Add the minimal MolmoSpaces MCP server/entry point, then run
   `帮我收拾这个房间` through a coding agent and validate 3-of-5 cleanup on an
   easy seed. The first implementation may use `api_semantic` MuJoCo state
   changes, but must label that provenance in `trace.jsonl`, `run_result.json`,
   and `report.html`. Keep failures visible in `run_result.json` and the
   report.

5. **Prompt-driven public cleanup**
   Completed in Phase 7. The prompt `帮我整理这个房间` now drives a public-only
   cleanup policy using `observe` / `scene_objects` data, with
   `planner_uses_private_manifest=false` in `run_result.json`.

6. **Real MolmoSpaces subprocess cleanup**
   Completed in Phase 8. The prompt `帮我整理这个房间` now runs through the same
   public cleanup loop against a real upstream MolmoSpaces/MuJoCo scene loaded
   by the isolated Python 3.11 runtime, with
   `backend=molmospaces_subprocess` in `run_result.json`.

7. **RBY1M visual cleanup and semantic substeps**
   Completed in Phases 9 and 10. The real subprocess cleanup now has
   RBY1M FPV/chase/map/verification views, target-facing robot orientation,
   same-room pose evidence, and object-level semantic substeps including
   fridge open/place-inside containment.

8. **OpenClaw follow-up**
   Reuse the working MCP surface through OpenClaw only after the direct cleanup
   demo is stable. Split this into a separate GSD phase if direct MCP cleanup is
   not stable quickly.

9. **Docs and ADR**
   Reframe README / ARCHITECTURE / technical design after evidence exists. Add
   an ADR that AI2-THOR remains baseline and MolmoSpaces is the next substrate
   for manipulation.

## Validation Plan

Cloud-testable checks:

- Scenario JSON parsing and seed determinism.
- Private manifest parsing and state-delta scoring.
- Public cleanup policy inference from task text and public scene objects.
- MCP tool request/response schemas with a fake MolmoSpaces backend.
- Additive `trace.jsonl` and `run_result.json` fields.
- Report rendering for before/after images, restored/missed table, trace
  summary, and primitive provenance.

Local-dev checks:

- MolmoSpaces/MuJoCo install and import.
- Scene load/reset and frame capture.
- Object inventory and object state readback.
- API-backed semantic manipulation behavior, with provenance labels.
- End-to-end cleanup coding-agent run restoring at least 3 of 5 misplaced
  objects.

Do not claim real MolmoSpaces validation from cloud-only evidence.

## Artifact Requirements

`trace.jsonl`:

- Keep the existing trace shape additive-only.
- Record every tool call, result status, error reason, and primitive provenance.
- Do not log `.env`, API keys, or private scoring manifests.

`run_result.json`:

- Record backend, scenario id, seed, final status, terminate reason, artifact
  paths, score summary, and primitive provenance.
- Distinguish `success`, `partial_success`, `failed`, `timeout`, and
  `blocked_capability`.

`report.html`:

- Show initial and final room snapshots.
- Show restored/missed object table.
- Show tool trace summary.
- Show backend primitive provenance near the pass/fail summary.
- Avoid wording that makes a shim look like real manipulation.

## Error And Rescue Rules

| Failure | Rescue |
| --- | --- |
| MolmoSpaces local install or APIs do not support the needed loop. | Stop after capability spike, document exact blocker, and do not fake cleanup success. |
| API-backed semantic behavior or scripted shim becomes indistinguishable from real manipulation. | Store primitive provenance in `run_result.json`, trace events, and report. |
| Cleanup prompt is too open and produces noisy failures. | Seed easy scenarios first, cap to 5 misplaced objects, require 3/5 restored. |
| Local-only validation gets implied as cloud-validated. | File/use a `local-dev` validation issue with exact commands and artifacts. |
| Scope expands into territory/multi-agent before one-agent works. | Keep territory and multi-agent explicitly deferred until cleanup evidence exists. |
| Large scene inventory overwhelms context. | Filter by visible/relevant types and cap response size. |
| Object/receptacle IDs drift between observe and action. | Use stable IDs or explicit stale-object errors. |

## Deferred

- Multi-agent MolmoSpaces.
- Territory/coverage on MolmoSpaces.
- Low-level arm control and VLA action experts.
- Isaac Lab humanoid migration.
- Full backend-neutral simulator abstraction.
- Split-model navigation optimization.
- Raising cleanup beyond 3-of-5 until the first easy cleanup demo works.

## GSD Handoff Trigger

The 2026-05-07 local capability spike identifies enough concrete MolmoSpaces /
MuJoCo APIs for a narrow GSD phase. The handoff is allowed with these limits:

- Optionally run `to-issues` first if the work should be divided across multiple
  agents or tracked in GitHub Issues.
- Add/update the phase in `.planning/ROADMAP.md`.
- Create `.planning/phases/<phase>/` from this doc.
- Let GSD own execution, validation, summaries, and shipped state.
- Keep the first phase scoped to `api_semantic` cleanup, fake-backend contracts,
  scorer, artifact schema, report rendering, and direct coding-agent MCP.
- Defer real RBY1M/Franka planner-backed manipulation and OpenClaw until the
  direct MCP cleanup artifact is stable and explicitly provenance-labeled.

During implementation, use `tdd` inside the slices where behavior needs to drive
the code: scenario scoring, manifest parsing, MCP tool contracts, artifact
schema, and any regression found during local MolmoSpaces validation.

## Review Decisions Incorporated

| Decision | Outcome |
| --- | --- |
| Keep direct coding-agent MCP before OpenClaw. | Accepted. |
| Require capability matrix before GSD ingest. | Accepted. |
| Require primitive provenance in artifacts. | Accepted. |
| Keep `to-issues` optional before GSD. | Accepted. |
| Treat `report.html` as artifact UI, not product UI. | Accepted. |
| Keep territory/coverage deferred. | Accepted. |
| Gate real MolmoSpaces validation as local-dev. | Accepted. |
| Make `帮我收拾这个房间` the first public proof instead of a separate pick/place milestone. | Accepted in office-hours follow-up. |
| Split OpenClaw follow-up if direct cleanup is unstable. | Accepted as guidance. |

## Current Workflow State

```text
completed:
  gsd-ingest-docs docs/plans/molmospaces-manipulation-spike.md
  gsd-plan-phase 06-molmospaces-api-semantic-cleanup
  gsd-execute-phase 06-molmospaces-api-semantic-cleanup
  gsd-verify-work 06-molmospaces-api-semantic-cleanup
  gsd-plan-phase 07-molmospaces-prompt-driven-cleanup-demo
  gsd-execute-phase 07-molmospaces-prompt-driven-cleanup-demo
  gsd-verify-work 07-molmospaces-prompt-driven-cleanup-demo
  gsd-plan-phase 08-molmospaces-real-subprocess-cleanup
  gsd-execute-phase 08-molmospaces-real-subprocess-cleanup
  gsd-verify-work 08-molmospaces-real-subprocess-cleanup
  gsd-plan-phase 09-molmospaces-fpv-room-plausibility
  gsd-execute-phase 09-molmospaces-fpv-room-plausibility
  gsd-verify-work 09-molmospaces-fpv-room-plausibility
  gsd-plan-phase 10-molmospaces-semantic-substeps
  gsd-execute-phase 10-molmospaces-semantic-substeps
  gsd-verify-work 10-molmospaces-semantic-substeps
  gsd-plan-phase 23-molmospaces-planner-backed-manipulation-proof
  gsd-execute-phase 23-molmospaces-planner-backed-manipulation-proof
  gsd-verify-work 23-molmospaces-planner-backed-manipulation-proof
  gsd-plan-phase 24-molmospaces-planner-runtime-diagnostics
  gsd-execute-phase 24-molmospaces-planner-runtime-diagnostics
  gsd-verify-work 24-molmospaces-planner-runtime-diagnostics
  gsd-plan-phase 25-molmospaces-planner-headless-renderer
  gsd-execute-phase 25-molmospaces-planner-headless-renderer
  gsd-verify-work 25-molmospaces-planner-headless-renderer
  gsd-plan-phase 26-molmospaces-cleanup-planner-proof-attachment
  gsd-execute-phase 26-molmospaces-cleanup-planner-proof-attachment
  gsd-verify-work 26-molmospaces-cleanup-planner-proof-attachment
  gsd-plan-phase 27-molmospaces-cleanup-planner-backed-primitives
  gsd-execute-phase 27-molmospaces-cleanup-planner-backed-primitives
  gsd-verify-work 27-molmospaces-cleanup-planner-backed-primitives
  gsd-plan-phase 28-molmospaces-rby1m-curobo-runtime-gate
  gsd-execute-phase 28-molmospaces-rby1m-curobo-runtime-gate
  gsd-verify-work 28-molmospaces-rby1m-curobo-runtime-gate
  gsd-plan-phase 29-molmospaces-camera-model-policy-cleanup
  gsd-execute-phase 29-molmospaces-camera-model-policy-cleanup
  gsd-verify-work 29-molmospaces-camera-model-policy-cleanup
  gsd-plan-phase 30-molmospaces-report-underlay-consolidation
  gsd-execute-phase 30-molmospaces-report-underlay-consolidation
  gsd-verify-work 30-molmospaces-report-underlay-consolidation
  gsd-plan-phase 31-molmospaces-rby1m-curobo-warmup-readiness
  gsd-execute-phase 31-molmospaces-rby1m-curobo-warmup-readiness
  gsd-verify-work 31-molmospaces-rby1m-curobo-warmup-readiness
  gsd-plan-phase 32-molmospaces-rby1m-curobo-cache-isolation
  gsd-execute-phase 32-molmospaces-rby1m-curobo-cache-isolation
  gsd-verify-work 32-molmospaces-rby1m-curobo-cache-isolation
  gsd-plan-phase 33-molmospaces-rby1m-warp-compatibility
  gsd-execute-phase 33-molmospaces-rby1m-warp-compatibility
  gsd-verify-work 33-molmospaces-rby1m-warp-compatibility
  gsd-plan-phase 34-molmospaces-rby1m-cuda-memory-headroom
  gsd-execute-phase 34-molmospaces-rby1m-cuda-memory-headroom
  gsd-verify-work 34-molmospaces-rby1m-cuda-memory-headroom
  gsd-plan-phase 35-molmospaces-rby1m-curobo-memory-profile
  gsd-execute-phase 35-molmospaces-rby1m-curobo-memory-profile
  gsd-verify-work 35-molmospaces-rby1m-curobo-memory-profile
  gsd-plan-phase 36-molmospaces-shared-semantic-cleanup-loop
  gsd-execute-phase 36-molmospaces-shared-semantic-cleanup-loop
  gsd-verify-work 36-molmospaces-shared-semantic-cleanup-loop
  gsd-plan-phase 37-molmospaces-planner-cleanup-bridge-readiness
  gsd-execute-phase 37-molmospaces-planner-cleanup-bridge-readiness
  gsd-verify-work 37-molmospaces-planner-cleanup-bridge-readiness
  gsd-plan-phase 50-molmospaces-mcp-smoke-shared-semantic-loop
  gsd-execute-phase 50-molmospaces-mcp-smoke-shared-semantic-loop
  gsd-verify-work 50-molmospaces-mcp-smoke-shared-semantic-loop
  gsd-plan-phase 51-molmospaces-planner-proof-bundle-runner-harness
  gsd-execute-phase 51-molmospaces-planner-proof-bundle-runner-harness
  gsd-verify-work 51-molmospaces-planner-proof-bundle-runner-harness
  gsd-plan-phase 52-molmospaces-planner-proof-bundle-cleanup-rerun-artifacts
  gsd-execute-phase 52-molmospaces-planner-proof-bundle-cleanup-rerun-artifacts
  gsd-verify-work 52-molmospaces-planner-proof-bundle-cleanup-rerun-artifacts
  gsd-plan-phase 53-molmospaces-planner-proof-bundle-execute-rerun
  gsd-execute-phase 53-molmospaces-planner-proof-bundle-execute-rerun
  gsd-verify-work 53-molmospaces-planner-proof-bundle-execute-rerun
  gsd-plan-phase 54-molmospaces-bind-proof-probes-to-cleanup-scene
  gsd-execute-phase 54-molmospaces-bind-proof-probes-to-cleanup-scene
  gsd-verify-work 54-molmospaces-bind-proof-probes-to-cleanup-scene
  gsd-plan-phase 55-molmospaces-proof-bundle-result-feasibility-report
  gsd-execute-phase 55-molmospaces-proof-bundle-result-feasibility-report
  gsd-verify-work 55-molmospaces-proof-bundle-result-feasibility-report
  gsd-plan-phase 56-molmospaces-proof-request-feasibility-selection
  gsd-execute-phase 56-molmospaces-proof-request-feasibility-selection
  gsd-verify-work 56-molmospaces-proof-request-feasibility-selection
  gsd-plan-phase 57-molmospaces-proof-request-fallback-generation
  gsd-execute-phase 57-molmospaces-proof-request-fallback-generation
  gsd-verify-work 57-molmospaces-proof-request-fallback-generation
  gsd-plan-phase 58-molmospaces-generated-fallback-proof-execution
  gsd-execute-phase 58-molmospaces-generated-fallback-proof-execution
  gsd-verify-work 58-molmospaces-generated-fallback-proof-execution
  gsd-plan-phase 59-molmospaces-plain-semantic-report-labels
  gsd-execute-phase 59-molmospaces-plain-semantic-report-labels
  gsd-verify-work 59-molmospaces-plain-semantic-report-labels
  gsd-plan-phase 60-molmospaces-fallback-timeout-stage-reporting
  gsd-execute-phase 60-molmospaces-fallback-timeout-stage-reporting
  gsd-verify-work 60-molmospaces-fallback-timeout-stage-reporting
  gsd-plan-phase 61-molmospaces-fallback-proof-warmup
  gsd-execute-phase 61-molmospaces-fallback-proof-warmup
  gsd-verify-work 61-molmospaces-fallback-proof-warmup
  gsd-plan-phase 62-molmospaces-warmed-generated-fallback-proof-execution
  gsd-execute-phase 62-molmospaces-warmed-generated-fallback-proof-execution
  gsd-verify-work 62-molmospaces-warmed-generated-fallback-proof-execution
  gsd-plan-phase 63-molmospaces-exact-scene-fallback-alias-validation
  gsd-execute-phase 63-molmospaces-exact-scene-fallback-alias-validation
  gsd-verify-work 63-molmospaces-exact-scene-fallback-alias-validation
  gsd-plan-phase 64-molmospaces-fallback-runtime-alias-discovery
  gsd-execute-phase 64-molmospaces-fallback-runtime-alias-discovery
  gsd-verify-work 64-molmospaces-fallback-runtime-alias-discovery
  gsd-plan-phase 85-molmospaces-standalone-prior-proof-ingest
  gsd-execute-phase 85-molmospaces-standalone-prior-proof-ingest
  gsd-verify-work 85-molmospaces-standalone-prior-proof-ingest
  gsd-plan-phase 86-molmospaces-prior-proof-evidence-report
  gsd-execute-phase 86-molmospaces-prior-proof-evidence-report
  gsd-verify-work 86-molmospaces-prior-proof-evidence-report
  gsd-plan-phase 87-molmospaces-selected-proof-candidate-execution
  gsd-execute-phase 87-molmospaces-selected-proof-candidate-execution
  gsd-verify-work 87-molmospaces-selected-proof-candidate-execution
  gsd-plan-phase 88-molmospaces-nested-prior-proof-evidence-carry-forward
  gsd-execute-phase 88-molmospaces-nested-prior-proof-evidence-carry-forward
  gsd-verify-work 88-molmospaces-nested-prior-proof-evidence-carry-forward
  gsd-plan-phase 89-molmospaces-planner-object-proof-selection-memory
  gsd-execute-phase 89-molmospaces-planner-object-proof-selection-memory
  gsd-verify-work 89-molmospaces-planner-object-proof-selection-memory
  gsd-plan-phase 90-molmospaces-broader-selected-proof-execution
  gsd-execute-phase 90-molmospaces-broader-selected-proof-execution
  gsd-verify-work 90-molmospaces-broader-selected-proof-execution
  gsd-plan-phase 91-molmospaces-broader-bound-proof-cleanup-rerun
  gsd-execute-phase 91-molmospaces-broader-bound-proof-cleanup-rerun
  gsd-verify-work 91-molmospaces-broader-bound-proof-cleanup-rerun
  gsd-plan-phase 92-molmospaces-prior-covered-proof-selection-memory
  gsd-execute-phase 92-molmospaces-prior-covered-proof-selection-memory
  gsd-verify-work 92-molmospaces-prior-covered-proof-selection-memory
  gsd-plan-phase 93-molmospaces-cleanup-report-artifact-adapter
  gsd-execute-phase 93-molmospaces-cleanup-report-artifact-adapter
  gsd-verify-work 93-molmospaces-cleanup-report-artifact-adapter
  gsd-plan-phase 94-molmospaces-seeded-source-pool-proof-memory
  gsd-execute-phase 94-molmospaces-seeded-source-pool-proof-memory
  gsd-verify-work 94-molmospaces-seeded-source-pool-proof-memory
  gsd-plan-phase 95-molmospaces-seeded-selected-proof-execution
  gsd-execute-phase 95-molmospaces-seeded-selected-proof-execution
  gsd-verify-work 95-molmospaces-seeded-selected-proof-execution

next pipeline candidates:
  rotate proof sources or diagnose/reduce the shared RBY1M grasp-feasibility
  blocker before another cleanup rerun
```
