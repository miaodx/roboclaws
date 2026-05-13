---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Better Views
status: active
stopped_at: Phase 135 MolmoSpaces CI live-agent reports implemented and non-live verified; hosted live proof pending secrets/run.
last_updated: "2026-05-13T18:08:00+08:00"
last_activity: 2026-05-13
progress:
  total_phases: 136
  completed_phases: 132
  total_plans: 166
  completed_plans: 153
  percent: 92
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** First public demonstration of multiple OpenClaw agent instances simultaneously controlling multiple simulated robots in competition and cooperation, with visible output for every feature.
**Current focus:** Phase 135 promotes the three known-good local MolmoSpaces
Claude Code provider-profile cleanup reports into an opt-in GitHub-hosted CI
path with local rehearsal, MolmoSpaces/MuJoCo asset caching/prewarm, and
Pages-visible report/status tiles. The repo-side implementation is complete;
hosted live proof is pending GitHub Actions secrets and an opt-in run.

## Current Position

**Current Phase:** 135
**Current Phase Name:** MolmoSpaces CI live-agent reports
**Current Plan:** 1
**Total Plans in Phase:** 1
**Total Phases:** 136
**Progress:** 92%

Phase: 135 (molmospaces-ci-live-agent-reports) - COMPLETE
Plan: 1 of 1 complete - `135-01` added local rehearsal, non-interactive Claude
Code live cleanup CI execution, MolmoSpaces asset prewarm/cache, and Pages
status/report publishing for the three model entries.
Status: Phase 135 is implemented and non-live verified. Real hosted/live proof
is intentionally not claimed until GitHub Actions secrets are configured and the
opt-in workflow runs.

Phase 35 produced strict standalone target planner-backed proof with
2 executed steps, `max_abs_qpos_delta=0.04167305757535879`, and no capability
blockers. Phase 36 routed current-contract and ADR-0003 object cleanup through
one shared semantic cleanup driver. Phase 37 now joins that target proof with
the cleanup primitive gate in ADR-0003 artifacts. The latest artifact reports
target runtime ready, cleanup primitives not ready, and bridge status
`blocked_capability` because cleanup subphases still use `api_semantic`.
Phase 38 closed the implementation seam before object-specific RBY1M/CuRobo
cleanup primitive replacement. Phase 39 closed the object/target binding
hardening slice. Phase 40 closed the adapter slice from bound target proof into
the executor seam. Phase 41 closed the probe-source binding slice. Phase 42
closed the observed-handle to planner-alias binding slice. Phase 43 closed the
bounded executor wiring slice. Phase 44 closed the proof-bundle coverage slice.
Phase 45 closed the remaining report/semantic mapping drift surfaced by the
ADR-0003 visual review. Phase 46 closed the local-dev handoff from cleanup
artifacts to repeatable bound planner proof generation. Phase 47 made that
handoff visible in the shared Cleanup Artifact Report. Phase 48 made the
runner output itself visually reviewable. Phase 49 added the checker for that
runner output. Phase 50 removed the remaining hand-written MCP smoke cleanup
loops and reused the shared semantic driver. Phase 51 made the
cleanup-to-proof-bundle runner handoff repeatable as a dry-run harness. Phase
52 closed cleanup rerun artifact tracking in runner manifests, reports, and
checker gates. Phase 53 added a named local-dev harness for executing proof
bundles and rerunning cleanup. The local run executed five `planner_backed`
RBY1M/CuRobo proofs and passed the runner checker with required proof and
cleanup rerun outputs, but the final cleanup rerun correctly remained
`blocked_capability` because no proof promoted cleanup primitive binding.
Phase 54 changed proof requests and probe execution to carry the real cleanup
scene XML plus requested planner aliases from `molmospaces_subprocess`
artifacts. Local exact-scene probes now reach the real cleanup-scene task
sampling path; the remaining blocker is upstream `HouseInvalidForTask` /
RBY1M robot placement infeasibility before sampled binding can promote.
Phase 55 added bundle-level proof result summaries and report rendering for
per-proof status, task-feasibility classification, cleanup binding promotion,
blockers, proof report links, and planner views.
Phase 56 added proof request feasibility selection so the runner can consume a
prior proof-result summary, skip requests already known task-feasibility
blocked, and report `fallback_required` when no ready request remains.
Phase 57 added private fallback request generation so blocked source requests
can generate bounded alternate planner-alias proof commands while preserving
cleanup-facing object/target IDs and rendering the generated rows in the runner
report/checker.
Phase 58 executed four generated fallback proof requests locally. The runner
checker passed with `--require-proof-outputs`, but every proof reported
`blocked_capability` with blocker `timeout` at `rby1m_config_import`; none
reached task sampling, planner-backed proof, cleanup binding promotion, or
planner view capture.
Phase 59 made `nav`, `pick`, `nav`, optional `open`, and `place` the primary
Cleanup Artifact Report labels while preserving object/target/surface/inside
as secondary role detail.
Phase 60 made generated fallback timeout evidence visible in proof-bundle
result summaries and runner reports by carrying timeout counts,
execution-attempted state, last worker stage, compact worker stage events, and
stdout/stderr artifact paths.
Phase 61 added an explicit RBY1M/CuRobo `config_import` warmup step to the
proof-bundle runner. Warmup and proof commands can now share an output-local
Torch extension cache, and the warmup is rendered and checked in runner
artifacts.
Phase 62 executed the warmed generated fallback bundle locally. Warmup got
through RBY1M/CuRobo config import, and all four generated proofs reached task
sampling. They now fail with `KeyError` invalid planner aliases instead of
timeout.
Phase 63 filters upstream/display aliases from generated fallback command
inputs while keeping them visible in the runner manifest/report. The dry-run
against the current local artifact filtered the four invalid aliases from Phase
62, generated no fallback commands, and left the next blocker as exact-scene
runtime alias discovery rather than retrying display IDs.
Phase 64 mines those prior exact-scene `KeyError` proof outputs for same-family
runtime aliases. The runner now renders discovered runtime aliases and turns
them into bounded generated fallback commands. The Phase 64 dry-run generated
four new fallback commands from five discovered runtime aliases and passed the
runner checker.
Phase 65 executed those discovered runtime-sibling fallback commands locally
with RBY1M/CuRobo warmup. Warmup succeeded and all four proofs reached task
sampling without config-import timeouts, but all remained `blocked_capability`:
target-sibling aliases still hit `HouseInvalidForTask`, object-sibling aliases
hit `AssertionError: Object is not a root body`, and no proof became
planner-backed, promoted cleanup binding, or emitted planner views.
Phase 66 carries that failed-candidate memory forward. The runner now preserves
prior discovered aliases from executed bundle manifests, filters prior non-root
body object aliases, filters prior task-feasibility-blocked alias pairs, renders
`Filtered Fallback Pairs`, and validates those rows through the checker. The
Phase 66 dry-run against the Phase 65 manifest generated two remaining commands
for the untried book runtime sibling and left the bowl request unavailable.
Phase 67 executed those two remaining commands locally with RBY1M/CuRobo
warmup and strict proof-output checking. Both reached task sampling without
timeout, but both failed with `AssertionError: Object is not a root body` for
`book_be4d759484637aeb579b28e6a954b18d_1_2_8`; no proof became
planner-backed, promoted cleanup binding, or emitted planner views.
Phase 68 carries prior filtered aliases and filtered pairs forward. The dry-run
against the Phase 67 manifest generated zero commands, reported
`fallback_required=true`, rendered five discovered aliases, seven filtered
aliases, and two filtered pairs, and left both source requests unavailable
through the current fallback pool.
Phase 69 adds an upfront pickup root-variant filter. Object-axis runtime aliases
with nonzero variants are filtered as `not_pickup_root_body_alias` before
command generation, while target-axis runtime siblings remain eligible. The
dry-run against Phase 62 KeyError evidence generated only two target-side
commands and filtered three object-side non-root variants.
Phase 70 lets the proof-bundle runner consume multiple prior proof-bundle
manifests and merge prior proof results with fallback-generation memory before
selection. The dry-run using Phase 62 and Phase 68 prior manifests generated
zero commands, kept `fallback_required=true`, and rendered five discovered
aliases, seven filtered aliases, and two filtered pairs in one report.
Phase 71 surfaces fallback generation status. The dry-run against the merged
prior evidence reports `Fallback status: exhausted`, zero generated commands,
five discovered aliases, seven filtered aliases, and two filtered pairs, and
the runner checker validates that status/report state.
Phase 72 summarizes the blockers behind that exhausted fallback pool. The
dry-run reports three `Fallback Exhaustion Blockers`: three non-root
object-side aliases require a richer pickup root-body alias source, two known
object/target alias pairs remain target task-feasibility blocked, and two
source requests have no remaining generated candidate.
Phase 73 normalizes those non-root object-side runtime aliases back to their
variant-0 pickup root aliases. The dry-run reports three normalized aliases,
zero generated commands, and only two remaining exhaustion blockers:
target-side task-feasibility-blocked pairs and source requests with no
remaining generated candidate.
Phase 74 makes the remaining target-side filters directly reviewable. The
dry-run preserves both Phase 65 target-feasibility proof report links despite
colliding generated fallback request IDs across prior manifests, and renders
their `worker_exception` stage in `Filtered Fallback Pairs`.
Phase 75 joins source request blockers and generated fallback-pair blockers
into one `Target Feasibility Blockers` report table. The dry-run reports four
target blockers: two source requests without prior proof report links in the
available evidence and two fallback pairs linked to Phase 65 proof reports with
`worker_exception` stage.
Phase 76 preserves exact task-sampler exception context when upstream sampling
raises before normal probe completion. The warmed local retry reached
`execute_task_sample_start`, failed with `HouseInvalidForTask`, and still
rendered exact cleanup task config, exact sampler adapter state, requested
cleanup binding, and worker-stage evidence.
Phase 77 captures the upstream sampler failure mode behind `HouseInvalidForTask`.
The warmed local probe rendered `Task Sampler Failure Diagnostics` with 17
robot-placement attempts, 17 asset failures for `Book_23`, 17 candidate
removals, and repeated `RobotPlacementError` for the exact book alias.
Phase 78 adds a visible relaxed task-sampler robot-placement profile. The
warmed local probe proves the profile changed the actual upstream
`place_robot_near` calls from requested `max_tries=10` to effective
`max_tries=50`, with radius `[0.0, 1.2]`, safety radius `0.15`, and visibility
checking disabled, but the exact `Book_23` request still failed all 17
placement attempts.
Phase 79 adds placement scene diagnostics to explain that remaining failure.
The warmed local probe rendered 17 scene diagnostics and showed `Book_23` has
2,231 valid free map points in the `[0.0, 1.2]m` annulus, free-space fraction
`0.012326`, no free points below `1.0m`, and nearest free point distance
`1.111824m`.
Phase 80 adds the wide placement profile. The warmed local probe uses radius
`[0.0, 2.0]` and effective `place_robot_near(max_tries=100)`, clearing robot
placement on all 17 attempts with zero placement failures and zero asset
failures. The run still ends in `HouseInvalidForTask` after 15 downstream
candidate removals.
Phase 81 captures those downstream candidate rejections. The warmed local probe
records 17 grasp-failure reports and 15 candidate-removal calls for the exact
book alias after successful robot placement.
Phase 82 classifies that Phase 81 artifact as
`task_feasibility_blocker_kind=grasp_feasibility` with
`17 grasp failures; 15 candidate-removal calls`, and renders the summary in
proof-bundle runner reports.
Phase 83 carries that classification into proof request selection memory:
excluded requests, generated fallback provenance, filtered fallback pairs, and
dedicated `Grasp Feasibility Blockers` runner report rows now preserve the
blocker kind/detail.
Phase 84 makes that memory robust across regenerated manifests by matching
prior proof results by `request_id` first, then cleanup `object_id` plus
`target_receptacle_id`; runner reports render the `Prior match` kind.
Phase 85 lets the runner consume standalone planner-probe `run_result.json`
evidence by normalizing it into the same prior proof result summary interface
before cleanup-pair selection.
Phase 86 renders consumed prior proof evidence in runner reports, preserving
diagnostics, proof paths, and planner-view images before new proof commands.
Phase 87 executed the remaining selected `proof_002` bowl/sink request. It
passed runner checking with required outputs but is also blocked as
`grasp_feasibility` with `17 grasp failures; 15 candidate-removal calls`.
Phase 88 carries nested prior proof evidence forward when a later proof-bundle
manifest is reused as the next prior input. The dry-run using only the Phase87
manifest preserves nested Phase81 evidence plus Phase87 proof results, excludes
both current source requests as grasp-infeasible, generates zero commands, and
renders both prior evidence rows in the shared runner report.
Phase 89 scopes proof-selection memory by guarded request ID, cleanup pair, and
internal planner object plus public target. The broader source artifact emits
10 ready proof requests and 176 robot-view images; the post-fix dry-run selects
8 new proof commands while excluding the two known grasp-infeasible internal
book/shelf and bowl/sink pairs by `planner_object_target` match.
Phase 90 executed those 8 selected broader candidates with RBY1M/CuRobo warmup
and the wide task-sampler placement profile. Seven are still
`grasp_feasibility` blocked, while `proof_008` is strict `planner_backed`
remote-control-to-stand evidence with promoted cleanup binding, sampled-task
match, and initial/final planner head-camera views.
Phase 91 reran cleanup with the existing `proof_008` artifact without
re-executing proof probes. The final cleanup report renders 44 robot timeline
steps, 176 robot-view images, attached planner proof initial/final views,
cleanup primitive gate, and planner cleanup bridge. `observed_008` is strict
planner-backed for `nav, pick, nav, place`, while 38 unmatched subphases remain
`api_semantic`, keeping the global primitive gate and bridge blocked.
Phase 92 adds prior covered-proof selection memory. The runner now excludes
prior results that are both `planner_backed` and cleanup-binding promoted,
reporting them as `prior_planner_proof_covered`. The dry-run against the
current broader seed selected zero commands, excluded `proof_008` as covered,
excluded nine grasp-infeasible requests, rendered prior proof views, and left
the next step as rotating to a new broader source pool.
Phase 93 adds a Cleanup Report Artifact Adapter. Existing cleanup artifacts can
now regenerate `report.html` from `run_result.json` through the shared report
underlay, reusing the canonical visual core and semantic subphase rails. The
referenced stale visual Codex report was repaired locally and passed the
agent-bridge checker without rerunning MolmoSpaces.
Phase 94 adds Seeded Source Pool and Proof Memory. Generated-mess selection now
uses the MolmoSpaces subprocess seed to choose different eligible object
identities while keeping semantic target fixtures stable, and proof-selection
memory rejects local `proof_###` / `observed_###` matches when planner object
identity conflicts. The patched seed 9 artifact validates with 10 generated
objects and 44 robot timeline steps; the prior-aware dry run selects 4 proof
commands.
Phase 95 adds Seeded Selected Proof Execution. The four selected patched seed 9
proof commands executed through the shared proof-bundle runner with warmup, low
RBY1M CuRobo memory, and wide placement profile. All four reached task sampling
but remained `grasp_feasibility` blocked with `17 grasp failures; 15
candidate-removal calls`; no new planner-backed proof or cleanup-binding
promotion was produced.
Phase 96 adds Planner Failure Diagnostic Views. Blocked task-sampler probes can
now capture one bounded post-placement camera artifact through the same
`image_artifacts` interface used by successful planner views, and
diagnostic-only blocked reports render an inline task-sampler diagnostic view
instead of an empty no-view state.
Phase 97 adds Post-Placement Rejection Views. Standalone planner reports and
proof-bundle result cards now render grasp-failure diagnostics as a shared
visual view, and checkers require that visual whenever grasp-failure
diagnostics are present.
Phase 98 adds a Grasp-Feasibility Blocker Matrix. Proof-bundle selection
reports now render grasp-infeasible object-target pairs as visual cards before
the detailed blocker table, and the runner checker requires that matrix when
grasp blockers are present.
Phase 99 adds Proof-Bundle Local Runtime Preflight. Real proof-bundle execution
now checks the configured MolmoSpaces Python import path before running
warmup/proof commands and writes a `local_runtime_blocked` report when the
runtime is not ready.
Phase 100 corrects the runtime preflight import to canonical `molmo_spaces`;
the local default MolmoSpaces Python now records `Local Runtime Preflight`
status `ready` for the current zero-command seeded-selection handoff.
Phase 101 records seed 10 source rotation. The source cleanup artifact validates
with 10 generated objects, 44 robot-view semantic steps, and 10 ready proof
requests. Prior-aware dry-run selection chooses five commands
(`proof_001`, `proof_003`, `proof_005`, `proof_008`, `proof_010`) and excludes
five requests as `prior_task_feasibility_blocked`.
Phase 102 executes those five selected seed 10 commands. All five proof outputs
are present and checked, but every request remains `grasp_feasibility` blocked
with 17 grasp failures, 15 candidate-removal calls, and one diagnostic view
artifact; no proof became planner-backed or promoted cleanup binding.
Phase 103 centralizes planner task-feasibility blocker summaries and renders a
bundle-level `Grasp Feasibility Signature Matrix`. The regenerated report from
Phase 102 proof outputs groups all five blockers into one repeated signature.
Phase 104 records post-execution fallback exhaustion for seed 10. The dry-run
using Phase 102 as prior memory selects zero commands, excludes all ten seed 10
requests as grasp-feasibility blockers, generates no fallback requests, and
records `no_fallback_candidate_available` for all ten source requests.
Phase 105 records candidate-removal effectiveness. New task-sampler diagnostics
distinguish grasp-threshold rows, removal-call rows, candidate-name misses, and
effective candidate-pool removals, and shared reports render those fields. The
real Phase 105 RBY1M proof rerun stayed `blocked_capability` but showed 17
grasp failures, 15 removal calls, 0 effective removals, and 15 candidate-name
misses.
Phase 106 binds the exact pickup candidate pool at `_select_pickup_object()`.
The real rerun stayed `blocked_capability` but changed the blocker shape:
candidate count moved from 4 unrelated upstream candidates to 1 requested bread
alias, grasp failures/removal calls dropped to 0, and the remaining blocker is
a direct invalid planner-object `KeyError`.
Phase 107 requires valid cleanup scene binding before exact-scene evidence is
accepted. The corrected seed-10 rerun used the canonical cleanup scene XML,
passed the stricter checker, moved the pickup pool from 17 unrelated candidates
to the requested bread alias, placed the robot once, captured one diagnostic
view, and now blocks at one post-placement grasp failure with zero
candidate-removal calls.
Phase 108 preserves exact pickup retry budget after binding. The valid-scene
rerun kept only the requested bread alias, repeated it to a budget of 3, and
now records 3 grasp failures, 1 threshold crossing, 1 candidate-removal call,
1 effective removal, and 0 candidate-name misses.
Phase 109 adds grasp collision diagnostics and reruns the valid scene. The
exact bread object maps to `Bread_1`; upstream attempts to load 512 cached
grasps three times, raises `ValueError` each time because no grasp file exists,
and never reaches collision masking.
Phase 110 keeps the top-level blocker as `grasp_feasibility` but classifies the
signature as `grasp_cache_missing`, carrying failed grasp-load counts and
missing asset IDs such as `Bread_1` into the shared runner report matrix.
Phase 111 routes that signature before another retry. The proof-bundle runner
now emits a `grasp_feasibility_mitigation_decision` and renders a visual
decision panel that chooses `grasp_cache_mitigation` for `Bread_1` while
keeping source rotation available only for separate unproven requests.
Phase 112 records the grasp-cache availability preflight for that route. The
proof-bundle runner now emits `grasp_cache_availability_preflight` and renders
the exact rigid loader paths checked by MolmoSpaces, proving the local
`Bread_1` object assets are present while droid, droid-objaverse, and RUM
rigid grasp-cache files are absent.
Phase 113 binds that preflight to the runtime MolmoSpaces assets root. The
runner now derives `ASSETS_DIR` from `planner_scene.scene_xml` and renders
symlink-resolved cache targets such as
`grasps/droid/20251116/Bread_1/Bread_1_grasps_filtered.npz`.
Phase 114 validates rigid cache contents before marking an asset ready. The
installed droid `Bread_1` file exists but contains zero transforms, so the
runner now reports `present_but_invalid` and keeps `Bread_1` missing-cache
blocked.
Phase 115 centralizes the semantic cleanup vocabulary. Raw cleanup phases,
surface/inside canonical sequences, display labels, focused action prefixes,
and loop variant strings now live in `semantic_timeline.py`; the shared cleanup
loop, Cleanup Artifact Report, visual-core checks, and checkers import them
instead of carrying local copies.
Phase 116 records the grasp cache generation preflight. The proof-bundle runner
now renders the `Bread_1` object XML, proposed upstream `run_rigid.py` command,
generated NPZ path, final droid loader cache target, and local prerequisite
blockers. Current generation is blocked by missing `sklearn`, missing
`python-fcl`, and missing Manifold `manifold` / `simplify` executables.
Phase 117 adds a reusable grasp-generation setup runner and runs it locally.
The runner installs the rigid-path Python prerequisites, initializes/builds
Manifold, and reruns the generation preflight with `status=ready` and zero
blockers.
Phase 118 adds a reusable grasp-cache generation/install runner and report. The
runner reaches `Bread_1` candidate generation, fixes the mesh-XML and checkout
assets-symlink issues, but blocks install because perturbation filtering saves
zero successful transforms.
Phase 119 adds a bounded grasp-filter diagnostics runner and report. The local
diagnostic preserves mesh/candidate/filter intermediates, generated 24 valid
`Bread_1` candidates, and showed zero successful transforms for
`initial_contact`, `translation_shake`, and `upstream_like`.
Phase 120 adds a scenario-less fallback to the Cleanup Report Artifact Adapter.
ADR-0003 visual cleanup artifacts without `scenario.json` now regenerate from
`run_result.json` through the shared report underlay using a minimal public
scenario shell, so stale local reports do not behave like separate
implementations.
Phase 121 adds a reusable grasp initial-contact diagnostic runner and report.
The local `Bread_1` sweep evaluated 24 candidates across 30 approach variants:
upstream-sign variants remained zero-success, while the best positive-sign
variant, `sign_1_dist_0.8_settle_1`, produced 9/24 successes with zero initial
object displacement.
Phase 122 adds a reusable grasp pose-policy cache runner and report. The
validated `sign_1_dist_0.8_settle_1` policy now runs through the shared MuJoCo
probe in cache-output mode, generated 9 valid transforms, installed them into
the droid `Bread_1` loader cache, and revalidated cache availability as ready.
Phase 123 reruns the exact cache-ready `observed_001` proof. The warmed run
loads 9 cached `Bread_1` grasps, finds 2 non-colliding grasps, matches the exact
cleanup binding, and blocks later at CuRobo pre-grasp trajectory generation.
Phase 124 focuses the cleanup report Robot View Timeline. ADR-0003 raw FPV
scan captures stay in `run_result.json`, Agent View, and Raw FPV Observations,
but the visual-core timeline now emphasizes before/after plus semantic cleanup
actions so ADR-0003 reports match the current-contract visual rhythm.
Phase 125 preserves CuRobo policy exception context and reruns the warmed exact
`observed_001` proof. The real run returned `planner_backed` for one execution
step with `max_abs_qpos_delta=0.018310936580938183`, preserved the CuRobo
profile and exact cleanup binding at top level, and did not reproduce the
pre-grasp no-planned-trajectory exception.
Phase 126 consumes the Phase 125 proof in the final ADR-0003 cleanup primitive
path. `observed_001` to refrigerator is planner-backed for `nav`, `pick`,
`nav`, `open`, and `place_inside`; the remaining 37 unmatched subphases stay
`api_semantic`, so the Cleanup Primitive Gate and Planner Cleanup Bridge remain
blocked at the run level.
Phase 127 adds Planner Proof Quality Evidence so attachments, bundles, reports,
and checkers classify proof strength through one shared module. The current
Phase 125 proof is now explicitly one-step motion evidence, not a full
pick/place or containment claim.
Phase 128 reuses that quality vocabulary across standalone planner probes and
proof-bundle runner reports. Individual proof reports, runner summaries, and
cleanup reports now render the same proof-strength tiers.
Phase 129 makes prior-covered selection proof-quality-aware. One-step prior
proof memory still satisfies the default horizon, but stricter proof-bundle runs
can reselect that request until a prior proof reaches the requested step count.
Phase 130 routes report generation for Molmo cleanup run directories and
`run_result.json` files through the shared Cleanup Report Artifact Adapter even
when callers use the generic report entrypoint.
Phase 131 renders the requested proof execution horizon in proof-bundle
manifests and runner reports, including command steps, quality target,
prior-covered coverage floor, and blockers when command generation is below the
requested proof horizon.
Phase 132 renders generated proof command cleanup tools as display-ready
semantic subphase rails, so dry-run proof reports show the shared
`nav, pick, nav, open?, place` intent before local execution.
Phase 133 adds explicit request-id filtering to the proof-bundle runner. The
bounded Phase 126 stricter dry-run selects only `proof_001`, renders
`Request ID Filter`, and passes the runner checker with max selected requests
set to 1.
Phase 134 canonicalizes cleanup tool ordering across proof request bindings,
probe-side parsing, promoted cleanup primitive bindings, and proof command
construction. The bounded `proof_001` dry-run now emits the same
`nav, pick, nav, open?, place` order in `--cleanup-tools`, manifest `tools`, and
the report semantic rail.
Phase 135 adds the opt-in MolmoSpaces live cleanup CI/report path: local
rehearsal, non-interactive Claude Code execution, MolmoSpaces/MuJoCo asset
prewarm/cache, GitHub-hosted serialized model entries, and Pages-visible
success/skipped/failed tiles for the three known-good local model variants.
Last activity: 2026-05-13 - Completed Phase 135 MolmoSpaces CI live-agent
reports implementation and non-live verification.

Progress: [##########] 100%
Next blocker: land the Molmo live CI branch to `main`, then run the opt-in
hosted Molmo live workflow with the configured GitHub Actions secrets
`KIMI_API_KEY` and `MIMO_TP_KEY` to collect real provider/runner evidence.
(Phase 08 satisfies the MolmoSpaces prompt-cleanup definition of done with a real upstream MuJoCo scene and subprocess backend. Phase 09 completes the visual FPV/same-room follow-up. Phase 10 completes the semantic-substep/report follow-up. Phase 11 completes the held-object carry visual follow-up. Phase 12 proves current-contract agent/OpenClaw tool viability. Phase 13 makes those agent bridge artifacts visually reviewable. Phase 14 implements the ADR-0003 public/private real-world-style cleanup boundary. Phase 15 closes the larger hidden Generated Mess Set lower-bound gap. Phase 16 exposes the ADR-0003 MCP agent surface. Phase 17 completes direct coding-agent dogfood on that stricter surface. Phase 18 completes synthetic OpenClaw Gateway dogfood on the same ADR-0003 MCP surface. Phase 19 completes real visual evidence on the same surface. Phase 20 completes clean-policy semantic-loop enforcement. Phase 21 completes advisory scoring/model-check artifacts. Phase 22 completes raw FPV-only perception evidence. Phase 23 completes the planner-backed manipulation provenance/proof gate. Phase 24 completes runtime diagnostics for strict planner probe blockers. Phase 25 completes the headless renderer blocker and produces a strict Franka planner-backed proof. Phase 26 attaches that proof to cleanup reports without changing cleanup-loop primitive provenance. Phase 27 completes the per-subphase cleanup primitive gate. Phase 28 completes the RBY1M/CuRobo target-runtime gate. Phase 29 completes camera-only model-policy cleanup. Phase 30 completes canonical report visual-core consolidation. Phase 31 completes staged RBY1M/CuRobo warmup evidence. Phase 32 completes isolated CuRobo extension-cache evidence. Phase 33 completes visible Warp compatibility evidence.)

## Performance Metrics

**Velocity:**

- Total plans completed: 135 (18 historical retrofit + 3 completed in Phase 02.4 + Phase 6/7/8/9/10/11/12/13/14 MolmoSpaces plans plus follow-on MolmoSpaces slices through Phase 135)
- Average duration: n/a (ingested from retrospectives, not GSD-tracked)
- Total execution time: n/a (pre-GSD work)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Core simulation + games | 6 | n/a | n/a |
| 1.5. CI + dev topology | 2 | n/a | n/a |
| 2. OpenClaw bridge (original) | 3 | n/a | n/a |
| 2.1. Transport correction | 3 | n/a | n/a |
| 2.2. Long-running OpenClaw games | 3 | n/a | n/a |
| 2.3. Digest pin (declined) | 1 | n/a | n/a |
| 2.4. View-experiment A/B | 3 | n/a | n/a |
| 6. MolmoSpaces cleanup pilot | 4 | n/a | n/a |
| 7. MolmoSpaces prompt cleanup | 2 | n/a | n/a |
| 8. MolmoSpaces real subprocess cleanup | 1 | ~2h | ~2h |
| 9. MolmoSpaces FPV room plausibility | 1 | ~2h | ~2h |
| 10. MolmoSpaces semantic substeps | 1 | ~2h | ~2h |
| 11. MolmoSpaces held-object carry visuals | 1 | ~1h | ~1h |
| 12. MolmoSpaces current-contract agent bridge | 1 | ~3h | ~3h |
| 13. MolmoSpaces agent bridge visual results | 1 | ~3h | ~3h |
| 14. MolmoSpaces real-world cleanup harness | 1 | ~2h | ~2h |

**Recent Trend:**

- Last 3 shipped phases: 133, 134, 135
- Trend: MolmoSpaces cleanup path now has ADR-0003 cleanup reports that attach strict planner proof without changing cleanup primitive provenance, a strict per-subphase gate for future planner-backed cleanup primitives, a target RBY1M/CuRobo runtime gate, a camera-only model-policy cleanup path, one canonical report visual core shared across the demos, staged RBY1M/CuRobo warmup-readiness evidence, isolated CuRobo extension-cache evidence, visible Warp compatibility evidence, measured CUDA memory headroom evidence, strict standalone RBY1M/CuRobo planner-backed proof under a visible low-memory profile, one shared semantic cleanup driver, explicit planner cleanup bridge-readiness evidence, a strict per-call executor seam for planner-backed cleanup primitives, object/target binding for that evidence, a probe-backed executor adapter that blocks generic standalone proof, planner probe diagnostics that promote cleanup binding only on exact request/sample match, private observed-handle to planner-alias binding, bounded opt-in executor wiring for one matching cleanup object, proof-bundle coverage for full synthetic cleanup gate readiness, a shared visual-core checker that rejects stale report shapes, private planner-proof request manifests for repeatable local proof-bundle generation, report visibility for those private proof requests, visual proof-bundle runner command reports, a checker for runner manifest/report integrity, shared-loop reuse in the MCP smoke demos, a dry-run harness for the proof-bundle runner, cleanup-rerun artifact tracking for executed bundle flows, a local execute-rerun gate, exact cleanup-scene proof binding, proof-bundle result summaries, proof request feasibility selection that skips prior infeasible requests before reruns, generated fallback proof requests that turn blocked source requests into private alternate planner-alias commands, local execution evidence showing those generated fallbacks time out at RBY1M config import before proof or binding, bundle-level timeout-stage reporting so those failures remain visible in the shared runner report, a visible shared-cache warmup step for generated fallback retries, local warmed execution evidence moving the blocker from config-import timeout to invalid exact-scene planner aliases, exact-scene fallback alias filtering that reports display aliases without generating invalid proof commands, runtime alias discovery that mines prior KeyError valid-name lists into new exact-scene fallback commands, local execution evidence showing those runtime-sibling commands reach task sampling but still block on task feasibility or non-root-body alias validity before proof, binding, or views, failed-candidate memory that prevents retrying known non-root aliases and prior task-feasibility-blocked alias pairs, filtered fallback execution evidence showing the remaining book runtime sibling is also non-root, filter carry-forward that preserves the exhausted fallback pool across manifests, pickup root-variant filtering that prevents future object-side non-root retries from older KeyError evidence, prior proof evidence merge so alias discovery and failed-candidate memory can be selected together from multiple manifests, explicit fallback exhaustion status in runner manifests/reports/checkers, stable fallback exhaustion blocker summaries that name root-body alias gaps, target task-feasibility-blocked pairs, and no-candidate source requests, pickup root alias normalization that proves the current object-side root aliases are already derivable, target feasibility proof links that preserve distinct prior fallback attempts across colliding generated IDs, a target feasibility blocker matrix that joins source and fallback blockers in one report view, task-sampler exception context that proves the exact sampler adapter was applied before warmed `HouseInvalidForTask` failures, task-sampler failure diagnostics that expose repeated Book_23 robot-placement failures, a relaxed task-sampler placement profile proving the actual upstream placement calls now receive `max_tries=50` while the exact Book_23 request remains infeasible, placement scene diagnostics showing the original infeasibility is driven by low local map free space around the exact object, a wide placement profile showing robot placement can clear while `HouseInvalidForTask` remains downstream, post-placement rejection diagnostics showing that downstream blocker is repeated grasp/candidate rejection, proof-result classification making that blocker machine-readable as `grasp_feasibility`, selection memory preserving that blocker through excluded requests, generated fallback provenance, filtered fallback pairs, and report blocker views, cleanup-pair proof memory keeping those filters attached across regenerated request IDs, standalone prior proof ingest bringing Phase 81-style planner-probe artifacts into the same selection interface as prior proof-bundle manifests, prior proof evidence reporting that keeps consumed prior diagnostics and planner-view artifacts visible in the runner report, selected proof candidate execution showing both current source requests are grasp-infeasible, nested prior proof evidence carry-forward so later runner generations preserve older blocker evidence from a single manifest input, planner-object proof memory so broader source artifacts can select new exact-scene commands without retrying known internal blocked pairs, broader selected proof execution showing one selected broader candidate is strict planner-backed with cleanup binding and views, broader bound proof cleanup rerun proving that one matching cleanup object can consume that proof while unmatched objects remain api-semantic and bridge-blocked, prior covered proof memory preventing that solved proof from being selected again, local runtime preflight that catches missing MolmoSpaces runtimes before proof execution, seed 10 source-rotation evidence, seed 10 selected proof execution showing all five selected requests are still grasp-feasibility blocked, grasp-feasibility signature grouping that collapses repeated executed blocker patterns into one reviewable matrix, seed 10 fallback exhaustion showing no generated fallback candidates remain under current rules, a grasp-cache routing decision that sends `Bread_1` missing-cache evidence to cache mitigation while keeping source rotation separate for unproven requests, a grasp-cache availability preflight that proves the `Bread_1` object asset exists while rigid loader cache files are absent, a runtime-assets preflight that resolves the missing loader paths through the MolmoSpaces symlink root, a validity preflight that rejects the installed empty `Bread_1` NPZ as `present_but_invalid`, semantic vocabulary centralization for `nav, pick, nav, open?, place`, a report-visible grasp generation preflight, reusable local setup that turns generation prerequisites ready, a generation/install report that exposes the remaining zero-success perturbation filter blocker, bounded filter diagnostics showing that even no-shake/no-rotate initial contact saves zero transforms for the generated `Bread_1` subset, a positive-standoff initial-contact sweep with 9/24 successes, scenario-less cleanup report regeneration through the same visual underlay, a validated droid `Bread_1` loader cache with 9 installed transforms, and a cache-ready exact proof rerun that clears grasp loading but exposes CuRobo pre-grasp trajectory planning as the next blocker.
- Phase 125 update: the warmed exact proof no longer reproduces the pre-grasp
  no-planned-trajectory blocker and passes the strict planner-probe checker as
  `planner_backed` for one execution step.
- Phase 126 update: the Phase 125 proof is now consumed by the final ADR-0003
  cleanup primitive path for the inside-target `observed_001` refrigerator
  sequence. The artifact is intentionally mixed and bridge-blocked because the
  remaining cleanup objects still lack matching planner proof coverage.
- Phase 127 update: attached planner proofs now carry Planner Proof Quality
  Evidence, reports render `Proof Quality`, and checker gates can require a
  minimum executed-step horizon before stronger cleanup claims are accepted.
- Phase 128 update: standalone planner-probe reports and proof-bundle runner
  reports now render the same proof-quality tiers, and their checkers can
  require proof-quality evidence before accepting stricter proof horizons.
- Phase 129 update: prior-covered proof selection now requires prior proof
  quality to meet the requested coverage horizon before suppressing a request.
- Phase 130 update: generic report generation now detects Molmo cleanup
  artifacts and delegates to the shared Cleanup Report Artifact Adapter.
- Phase 131 update: proof-bundle runner manifests and reports now render Proof
  Execution Horizon details before local execution, and the runner checker can
  require that view.
- Phase 132 update: proof-bundle command rows now carry cleanup tools and
  render display-ready semantic subphase rails in the shared cleanup vocabulary.
- Phase 133 update: proof-bundle runs can now be filtered to explicit
  `--request-id` values, and reports/checkers show requested, matched,
  unavailable, and missing IDs.
- Phase 134 update: cleanup tool ordering now normalizes through the shared
  semantic timeline helper so proof command flags, manifest rows, and report
  rails all preserve `nav, pick, nav, open?, place`.
- Phase 135 update: the Molmo live CI report path is implemented with local
  dry-run rehearsal, non-interactive Claude Code execution, MolmoSpaces cache
  prewarm, serialized GitHub-hosted model entries, and Pages status/report
  manifest rendering. Hosted live proof remains pending Actions secrets and an
  opt-in run.
- Report label note: Phase 59 makes `nav, pick, nav, open?, place` the primary
  Cleanup Artifact Report vocabulary and keeps object/target/surface/inside as
  secondary role detail.

*Updated after each plan completion — prior entries are one-time ingest backfill.*
| Phase 02.6 P02 | 25min | 3 tasks | 2 files |
| Phase 02.6 P03 | 5min  | 1 task  | 1 file  |
| Phase 02.6 P04 | 7min  | 3 tasks | 2 files |
| Phase 02.6 P05 | 7min  | 1 task  | 3 files (2 deleted, 1 edited) |
| Phase 02.6 P06 | 32min | 6 tasks | 2 files |
| Phase 02.6 P07 | 20min | 3 tasks | 3 files |
| Phase 08 P01 | ~2h | 4 tasks | 18 files |
| Phase 09 P01 | ~2h | 4 tasks | 10 files |
| Phase 10 P01 | ~2h | 4 tasks | 18 files |
| Phase 11 P01 | ~1h | 4 tasks | 7 files |
| Phase 12 P01 | ~3h | 4 tasks | 15 files |
| Phase 13 P01 | ~3h | 4 tasks | 14 files |
| Phase 14 P01 | ~2h | 4 tasks | 15 files |
| Phase 15 P01 | ~2h | 4 tasks | 8 files |
| Phase 16 P01 | ~3h | 6 tasks | 10 files |
| Phase 17 P01 | ~1h | 5 tasks | 10 files |
| Phase 18 P01 | ~2h | 5 tasks | 13 files |
| Phase 19 P01 | ~2h | 5 tasks | 9 files |
| Phase 20 P01 | ~1h | 5 tasks | 11 files |
| Phase 21 P01 | ~1h | 5 tasks | 13 files |
| Phase 22 P01 | ~1h | 5 tasks | 15 files |
| Phase 23 P01 | ~1h | 5 tasks | 11 files |
| Phase 24 P01 | ~1h | 5 tasks | 12 files |
| Phase 25 P01 | ~1h | 5 tasks | 10 files |
| Phase 26 P01 | ~2h | 5 tasks | 8 files |
| Phase 27 P01 | ~1h | 5 tasks | 9 files |
| Phase 28 P01 | ~1h | 5 tasks | 7 files |
| Phase 29 P01 | ~2h | 5 tasks | 9 files |
| Phase 30 P01 | ~1h | 5 tasks | 9 files |
| Phase 31 P01 | ~1h | 5 tasks | 10 files |
| Phase 32 P01 | ~1h | 5 tasks | 10 files |
| Phase 33 P01 | ~1h | 5 tasks | 10 files |
| Phase 34 P01 | ~1h | 5 tasks | 6 files |
| Phase 35 P01 | ~1h | 5 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Phase 16 planning (2026-05-09):** ADR-0006 adds a stricter real-world Molmo
  cleanup MCP surface backed by `RealWorldCleanupContract`. It should expose
  Metric Map, Fixture Hints, waypoint observation, Observed Object Handles, and
  semantic cleanup tools, but not current-contract `scene_objects`. The first
  slice uses a deterministic MCP smoke agent; direct Codex/Claude/OpenClaw
  dogfood against the stricter surface follows once this MCP contract is stable.
- **Phase 16 completion (2026-05-09):** The ADR-0003 cleanup contract now has a
  separate `molmo_cleanup_realworld` MCP server/factory. Its public tool surface
  excludes `scene_objects`, rejects that tool explicitly, and writes
  agent-driven real-world artifacts with the shared Agent View, Private
  Evaluation, Score, Cleanup Trace, and Robot View Timeline report underlay.
  Real seed 1 evidence restored 8/10 hidden generated objects, swept all public
  waypoints, recorded no disturbance, and passed the checker with
  `policy=realworld_contract_smoke_agent`. Direct Codex/Claude/OpenClaw dogfood
  against this stricter contract remains a follow-up, not a Phase 16 claim.
- **Phase 17 planning (2026-05-09):** ADR-0007 splits direct coding-agent
  dogfood from the Phase 16 deterministic MCP smoke. The phase should add a
  real-world cleanup skill, direct server entrypoint, checker assertions, and
  focused recipes for clean ADR-0003 agent artifacts before attempting OpenClaw
  Gateway dogfood.
- **Phase 17 completion (2026-05-09):** Direct coding-agent dogfood on
  `molmo_cleanup_realworld` is now possible and checker-gated. The new
  `skills/molmo-realworld-cleanup/SKILL.md` teaches the public ADR-0003 loop,
  `examples/molmo_realworld_cleanup_agent_server.py` starts the direct agent
  server, and `scripts/check_molmo_realworld_cleanup_result.py` can enforce a
  clean agent run with no `scene_objects` trace events. Claude Code produced a
  clean synthetic direct-agent artifact (`policy=claude_code_agent`, 5/5
  restored, full sweep, no disturbance). Codex was attempted but blocked by
  non-interactive MCP call cancellation and a local bwrap sandbox error.
- **Phase 18 planning (2026-05-09):** ADR-0008 evaluates OpenClaw Gateway after
  direct coding-agent dogfood stabilized the strict ADR-0003 MCP skill and
  checker. The first Gateway gate may be minimum tool-use viability rather than
  full clean cleanup success, but it must still use `molmo_cleanup_realworld`,
  avoid `scene_objects`, and produce clear artifacts or an exact blocker.
- **Phase 18 completion (2026-05-09):** OpenClaw Gateway completed a clean
  synthetic ADR-0003 MCP cleanup run through `molmo_cleanup_realworld` with
  `policy=openclaw_agent`, 5/5 restored generated objects, full waypoint sweep,
  no disturbance, no stale references, and no `scene_objects` trace events.
  The checker now supports `--require-openclaw-minimum`, and
  `just verify::molmo-realworld-openclaw-dogfood-kit` guards the OpenClaw
  minimum artifact shape. The local Gateway attempt surfaced a launch-path
  requirement: the MCP server must bind `--host 0.0.0.0` for Docker
  `host.docker.internal` reachability; `127.0.0.1` leaves Gateway with only
  `session_status`.
- **ADR-0009 (2026-05-09):** MolmoSpaces cleanup demos now share one
  **Cleanup Artifact Report** underlay in `roboclaws/molmo_cleanup/report.py`
  and one semantic display model in `semantic_timeline.py`. Report-facing
  semantic subphases render as `nav -> pick -> nav -> open? -> place`, while
  raw traces retain full tool names.
- **Phase 19 planning (2026-05-09):** ADR-0010 splits real visual OpenClaw
  evidence from Phase 18's synthetic Gateway proof. The phase must run the
  ADR-0003 `molmo_cleanup_realworld` surface with `backend=molmospaces_subprocess`,
  `--include-robot`, and `--record-robot-views`, then validate Agent View,
  Private Evaluation, Score, Semantic Substeps, Robot View Timeline, and the
  FPV/chase/map/verification PNG set through the shared report underlay.
- **Phase 19 completion (2026-05-09):** OpenClaw visual evidence is now
  checker-gated. `just verify::molmo-realworld-openclaw-visual-dogfood-kit`
  produced a clean OpenClaw-labeled real MolmoSpaces/RBY1M artifact with 176
  robot-view PNGs. A live Gateway run produced a minimum-valid visual artifact
  with 48 robot-view PNGs, 14/14 waypoint sweep, no `scene_objects`, and the
  full shared report view set. The live run failed clean policy success because
  the model skipped `navigate_to_object`/`navigate_to_receptacle` and chose
  weak destinations, so future OpenClaw hardening should target semantic-loop
  obedience and destination choice.
- **Phase 20 planning (2026-05-09):** ADR-0011 makes the semantic cleanup loop
  executable in the ADR-0003 MCP contract. `pick` should require
  `navigate_to_object`, `place` should require `navigate_to_receptacle`, and
  fridge-like `place_inside` should require `open_receptacle`. Clean
  OpenClaw evidence should reject semantic-order errors rather than relying on
  prompt-only obedience.
- **Phase 20 completion (2026-05-09):** The ADR-0003 real-world MCP contract now
  rejects skipped semantic phases with public `semantic_order` errors and
  `required_tool` recovery hints. The strict clean checker rejects nonzero
  semantic-order errors. Direct-agent and OpenClaw-labeled synthetic dogfood
  gates both pass with `semantic_order_errors=0`, and the existing real visual
  OpenClaw clean artifact still passes the strict clean visual checker.
- **Phase 21 planning (2026-05-09):** ADR-0012 adds a non-authoritative
  advisory scoring/model-check artifact. The default adapter should be
  deterministic and CI-safe, write `advisory_evaluation.json`, render an
  Advisory Review report panel, and never change deterministic pass/fail
  fields.
- **Phase 21 completion (2026-05-09):** ADR-0003 deterministic and MCP
  artifacts now include non-authoritative advisory scoring with schema
  `advisory_cleanup_scoring_v1`. The shared Cleanup Artifact Report renders an
  Advisory Review panel, `scripts/check_molmo_realworld_cleanup_result.py`
  supports `--require-advisory-scoring`, and the ADR-0003 harness recipes
  require it for new artifacts.
- **Phase 22 planning (2026-05-09):** ADR-0013 adds an evidence-mode raw
  FPV-only observation contract for ADR-0003. The phase should keep the current
  visible-detection mode as default, add `perception_mode=raw_fpv_only`, record
  public raw FPV observation rows and FPV artifacts, render them through the
  shared Cleanup Artifact Report, and checker-gate the evidence without
  claiming clean camera-only cleanup success.
- **Phase 22 completion (2026-05-09):** ADR-0003 deterministic and MCP paths now
  support `perception_mode=raw_fpv_only`. Raw mode suppresses structured
  movable-object detections and observed handles, records public
  `raw_fpv_observations`, attaches FPV artifacts from the existing RBY1M
  robot-view capture path, and renders a Raw FPV Observations report panel.
  `just verify::molmo-realworld-raw-fpv` passed with 14 raw observations, 16
  robot-view steps, full waypoint sweep, and expected cleanup failure because
  camera-only object registration is not part of this slice.
- **Phase 23 planning (2026-05-09):** ADR-0014 adds a planner-backed
  manipulation provenance/proof gate. Existing cleanup primitives remain
  `api_semantic`; the phase should add shared manipulation provenance metadata,
  report rendering, a standalone MolmoSpaces planner probe, and a checker that
  accepts blocked-capability evidence only when explicit while requiring real
  planner execution evidence for the strict proof gate.
- **Phase 23 completion (2026-05-09):** Current-contract and ADR-0003 cleanup
  artifacts now include `manipulation_evidence` that makes `api_semantic`
  execution explicit. The shared report underlay renders `Manipulation
  Provenance`, and the standalone planner probe/checker path can record
  blocked-capability evidence without satisfying strict planner proof. The
  default `just verify::molmo-planner-manipulation-probe` gate passed with
  `PickAndPlacePlannerPolicy` import evidence and
  `status=blocked_capability`.
- **Phase 24 planning (2026-05-09):** ADR-0015 adds runtime diagnostics for
  strict planner probe blockers. The planner probe should enable faulthandler,
  record planner dependency availability, render Runtime Diagnostics in the
  shared planner report, and keep `--require-planner-backed` semantics strict.
- **Phase 24 completion (2026-05-09):** Planner probe artifacts now carry
  `runtime_diagnostics` in `manipulation_evidence`, emit an early stdout
  diagnostics JSON line before risky planner imports, and render a shared
  `Runtime Diagnostics` report panel. The default verify gate passed with
  diagnostics present. Franka execute-mode evidence is now actionable as
  `SIGSEGV` in `glfw.create_window` during MolmoSpaces task sampling, with a
  faulthandler stack in stderr. RBY1M config-import evidence confirms
  `ModuleNotFoundError: No module named 'curobo'` and
  `runtime_diagnostics.modules.curobo.available=false`.
- **Phase 25 planning (2026-05-09):** ADR-0016 adds a probe-local headless
  renderer adapter for strict Franka execute-mode proof. The default GLFW path
  segfaults, while raw EGL env vars hit an upstream Linux/CGL import bug.
  Phase 25 should patch the MolmoSpaces renderer constructor only inside the
  worker process to pass `device_id=0`, record that override in diagnostics,
  and keep `--require-planner-backed` strict.
- **Phase 25 completion (2026-05-09):** The planner probe now sets EGL env vars
  for execute-mode workers and patches both MolmoSpaces renderer call sites
  (`env.env.MjOpenGLRenderer` and `utils.scene_maps.MjOpenGLRenderer`) inside
  the worker process. The strict Franka headless artifact passed
  `--require-planner-backed` with `status=planner_backed`,
  `steps_executed=2`, `max_abs_qpos_delta=0.01846538091255523`, and initial/
  final wrist-camera views. This closes standalone Franka planner proof but not
  ADR-0003 cleanup-loop integration.
- **Phase 26 planning (2026-05-09):** ADR-0017 adds an Attached Planner Proof
  artifact inside ADR-0003 cleanup reports. The phase should validate a strict
  planner probe `run_result.json`, copy proof images into the cleanup run, render
  `Attached Planner-Backed Proof`, and keep cleanup primitive provenance as
  `api_semantic` until the cleanup loop actually calls planner-backed
  primitives.
- **Phase 26 completion (2026-05-09):** ADR-0003 cleanup artifacts now accept a
  strict planner probe `run_result.json`, copy its initial/final proof views,
  render `Attached Planner-Backed Proof`, and can be checker-gated with
  `--require-planner-proof-attachment`. The local MolmoSpaces/RBY1M artifact
  passed with `backend=molmospaces_subprocess`, 176 robot-view PNGs, 2 attached
  planner-proof PNGs, and cleanup primitive provenance still `api_semantic`.
- **Phase 27 planning (2026-05-09):** ADR-0018 adds a per-subphase
  planner-backed cleanup primitive gate. The phase should derive
  `cleanup_primitive_evidence` from semantic substeps, render the gate in the
  shared Cleanup Artifact Report, accept explicit blocked-capability evidence
  for current `api_semantic` cleanup, and reject current artifacts when strict
  planner-backed cleanup primitives are required.
- **Phase 27 completion (2026-05-09):** Cleanup artifacts now derive and render
  `cleanup_primitive_evidence` as a `Cleanup Primitive Gate`. The checker
  accepts current artifacts only with
  `--accept-blocked-planner-cleanup-primitives` and rejects them with
  `--require-planner-backed-cleanup-primitives` because the cleanup subphases
  remain `api_semantic`.
- **Phase 28 planning (2026-05-09):** ADR-0019 adds an explicit RBY1M/CuRobo
  runtime gate. The phase should derive `rby1m_curobo_gate` from planner probe
  artifacts, render it in the shared planner probe report, accept current
  missing-CuRobo blockers only as explicit blocked-capability evidence, and
  reject Franka strict proof as RBY1M/CuRobo readiness.
- **Phase 28 completion (2026-05-09):** Planner probe artifacts now include
  `rby1m_curobo_gate`, and reports render `RBY1M CuRobo Gate`. The checker
  accepts current RBY1M blocked evidence only with
  `--accept-rby1m-curobo-blocked` and rejects it with
  `--require-rby1m-curobo-ready`.
- **Phase 15 planning (2026-05-09):** ADR-0005 makes the Generated Mess Set size
  explicit and configurable. The ADR-0003 real-world harness should use 10
  hidden generated objects as the default v1 evidence shape, while retaining the
  five-object synthetic fixture for fast tests and current-contract
  compatibility. The Scorer must evaluate the whole generated set and derive the
  success threshold from the actual generated count.
- **Phase 15 completion (2026-05-09):** The Generated Mess Set selector now
  lives in `roboclaws/molmo_cleanup/generated_mess.py` and is reused by the real
  MolmoSpaces subprocess worker. `just harness::molmo-realworld-cleanup`
  requests 10 hidden generated objects by default, and
  `scripts/check_molmo_realworld_cleanup_result.py` can enforce that lower
  bound. Real seed 1 evidence produced `generated_mess_count=10`, 10 semantic
  substep rows, 44 robot timeline steps, 176 PNGs, and `cleanup_status=success`.
- **Phase 14 completion (2026-05-09):** ADR-0003 is now implemented as a
  separate real-world-style cleanup harness. The Cleanup Agent sees only
  `metric_map`, room-level `fixture_hints`, waypoint `observe` results, and
  `observed_*` handles; private Generated Mess Set, target count, acceptable
  destination sets, and exact scorer truth are written only to post-run
  `private_evaluation` artifacts/report sections. The deterministic sweep
  baseline passed the real MolmoSpaces subprocess gate for seeds 1, 2, and 3
  with exact `mess_restoration_rate=0.8`, full sweep coverage, and no
  disturbance. A follow-up within the same phase added RBY1M visual report
  parity: current-contract bridge reports and ADR-0003 harness reports now
  share `roboclaws/molmo_cleanup/semantic_timeline.py` as the underlying
  semantic timeline/report model. Seed 1 now produces a `Robot View Timeline`
  with 23 focused robot steps and 92 FPV/chase/map/verification PNGs using
  `navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? ->
  place/place_inside` object phases while keeping Agent View and Private
  Evaluation separate. The first slice keeps the existing generated mess count
  of 5; expanding to 10-20 objects is a follow-up.
- **Phase 12 completion (2026-05-08):** The Molmo cleanup current contract now
  has a separate FastMCP bridge for external agents. Codex and Claude Code both
  completed clean direct MCP runs (`success`, 5/5 restored, no stale references)
  using `skills/molmo-cleanup/SKILL.md`. OpenClaw Gateway also restored 5/5 and
  terminated cleanly, but made one recovered stale-reference attempt by using a
  sofa/simulator-style id as an object id; the skill and observe instruction now
  explicitly say object IDs must come only from `scene_objects.objects[*]` and
  receptacles are targets only. This phase remains `contract=current_contract`
  and does not satisfy ADR-0003 because global `scene_objects` is still exposed.
- **Phase 13 completion (2026-05-08):** Agent bridge reports now have the same
  RBY1M robot-view timeline and semantic mid-phase visual rows as the Molmo
  robot visual harness. Visual dogfood passed for Codex, Claude Code, and
  OpenClaw, but the scores were 4/5, 4/5, and 3/5 because public semantic
  choices can miss private scorer truth. This is expected current-contract
  behavior, not ADR-0003 realism.
- **Phase 08 completion (2026-05-07):** The MolmoSpaces cleanup definition of
  done now requires and has evidence for `backend=molmospaces_subprocess`, an
  isolated Python 3.11 runtime, upstream `procthor-10k-val` scene loading, real
  metadata/object-state readback, public-only prompt planning for
  `帮我整理这个房间`, scorer-only private manifest use, and the required
  `before.png` / `after.png` / `trace.jsonl` / `run_result.json` /
  `report.html` artifacts. Provenance remains `api_semantic` because the worker
  mutates real MuJoCo free-joint `qpos`; reserve `real` for future
  RBY1M/Franka planner-backed pick/place.
- **Phase 09 completion (2026-05-08):** RBY1M FPV orientation now uses
  target-facing base yaw for horizontal direction and a separately recorded
  target-framing head pitch for camera readability. Same-room stand-off
  selection is checked against MuJoCo room outlines, and the visual gate now
  requires positive FPV target pixels on focused manipulation steps.
- **Phase 10 completion (2026-05-08):** Cleanup execution is now recorded as
  object-level semantic substeps. Fridge cleanup opens the real articulated
  fridge joint, places the apple with `place_inside`, and records final
  containment/readback as `location_relation=inside`. Robot timeline rows now
  include semantic phase badges, and non-focused context rows no longer show a
  misleading Verification panel. `primitive_provenance=api_semantic` remains
  correct because these commands mutate real MuJoCo state but are not
  planner-backed RBY1M/Franka pick/place.
- **Phase 11 completion (2026-05-08):** Held objects now visually travel with
  RBY1M during semantic cleanup navigation. `navigate_to_receptacle` and
  fridge `open_receptacle` update the held object's real MuJoCo free-joint qpos
  to the robot-relative held pose, and the visual checker requires positive FPV
  object pixels plus robot-relative position evidence on carried navigation
  rows. This remains `api_semantic`, not planner-backed robot manipulation.
- **Phase 02.4 planning (2026-04-21):** GSD decomposition starts with `examples/openclaw_demo.py` (single-agent push-model navigation) before territory/coverage. Phase scope remains the full A/B study; only the execution order changed.
- **Phase 02.4 execution checkpoint (2026-04-21):** Plans `02.4-01` through `02.4-03` are complete and the cloud-safe slice of `02.4-04` (`scripts/analyze_view_experiment.py` plus synthetic-data coverage) is implemented. The actual Kimi/NVIDIA sweep and `docs/view-experiment-2026-04.md` remain local-dev only and are tracked in issue #70.
- **Cross-phase local follow-up (2026-04-22):** The Phase 02.4 view family is now shared with the shipped Phase 02.6 autonomous MCP path. `examples/openclaw_nav_autonomous.py --views map-v2+chase` completed locally with real Kimi + AI2-THOR (`done`, 2 observes + 1 move + 1 done in the summary-fix smoke), and the MCP server now fails fast on bind collisions instead of burning the full wall-clock budget behind a dead listener.
- **Phase 02.4 decision lock (2026-04-24):** The old `baseline` / `map-v2` / `map-v2+chase` A/B study is now historical only. Runtime support was standardized on `map-v2+chase`, user-facing `--views` flags were removed from the main examples, and `02.4-04` was superseded rather than executed.
- **Phase 5 completion (2026-04-23):** The codebase-simplification phase closed all 9 plans in a single verified worktree batch. Eighteen target files finished at or below their original line caps (`9,378` → `9,175`, net `-203`), targeted example/API guards stayed green, and the final repo-wide `pytest`, `ruff check`, and `ruff format --check` gates passed after a small pre-existing lint cleanup in unrelated scripts/tests.
- **Phase 02.7 planning completion (2026-04-22):** The queued autonomous follow-up now has a full GSD planning bundle under `.planning/phases/02.7-openclaw-intermediate-message-capture/`: four executable plan files plus `02.7-RESEARCH.md` and `02.7-VALIDATION.md`. Scope remains unchanged: compare real Gateway streaming vs terminal-body capture, persist transcript artifacts additively, surface them in `report.html`, and validate the shipped path locally. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 5 planning completion (2026-04-23):** Iterative codebase simplification phase now has a full GSD planning bundle under `.planning/phases/05-iterative-codebase-simplification/`: nine executable plan files covering all major source files (visualizer.py, mcp_server.py, reporter.py, transport.py, game modules, provider modules, supporting modules, and example scripts). All plans wave 1, independent, atomic commits, pytest + ruff gate per commit. Verification passed. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 4 planning completion (2026-04-23):** The queued refactor-safety follow-up now has a full GSD planning bundle under `.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/`: four executable plan files plus `04-RESEARCH.md` and `04-VALIDATION.md`. Scope is locked to tiny contract fixtures, a thin capture harness, a separate baseline-vs-candidate analyzer, and a local baseline-refresh workflow. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 4 execution completion (2026-04-23):** The refactor-regression harness phase is now implemented. Added `roboclaws/regression.py`, capture/analyze CLIs, operator docs, contract/analyzer tests, and the first real local evidence bundle in `.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md`. Live probe feedback tightened the harness in two places: `openclaw-autonomous` now treats `terminated_by=error` / zero-observe runs as capture failures, and `explore-vlm` analyzer thresholds now use ratio-or-absolute slack (`usd` +$0.01, `wallclock` +120s) so small same-commit Kimi workflow proofs do not fail on cold-start variance alone. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 02.6 plan 01 (2026-04-21)**: MCP server default bind is `127.0.0.1` (localhost-only) per threat model T-02.6-01; Gateway container reaches via `host.docker.internal` → host-gateway → loopback. Bind is NOT env-configurable — only via explicit argument.
- **Phase 02.6 plan 01 (2026-04-21)**: Trace schema additive-only rule: `tests/fixtures/trace_schema_reference.json` freezes sim_server.py key-sets at phase entry; MCP server emits a SUPERSET. `snapshot_metrics` is the one exception — EQUALITY checked because `run_result_json["sim_server_metrics"]` consumers depend on exact names.
- **Phase 02.6 plan 01 (2026-04-21)**: `mcp[cli]>=1.27` in `dev` + new `openclaw` extra; NOT in top-level `[project].dependencies` (core library stays installable without the Gateway path, mirroring ai2thor).
- **Phase 2.3 (LOCKED, 2026-04-20)**: Decline digest-pinning the Gateway image; keep `ghcr.io/openclaw/openclaw:2026.4.14`. One-click rollback digest recorded in ADR.
- **Phase 2.2 (2026-04-16)**: Ship 3 symmetric Layer 3 tiles (nav / territory / coverage); reject UC1 Persona Showdown framing.
- **Phase 2.2 (2026-04-16)**: "Long-running" = within a single game run; no cross-run MEMORY persistence.
- **Phase 2.1**: Gateway transport is `POST /v1/chat/completions` with `model="openclaw/<agentId>"`; not `/tools/invoke`.
- **Phase 2.1**: Inline base64 image transport; no bind mount.
- Phase 02.6 plan 02 (2026-04-21): ROBOCLAWS_TOOL_PROFILE validated against {minimal, coding, messaging} with hard die 1 on typos (T-02.6-06). SIM_SERVER_URL kept as translate-and-warn fallback one wave; plan 05 removes it. main fallback agent intentionally left without tools.profile (Gateway insists on it existing but never routes). Test pattern: line-based heredoc extraction + base-path replacement exec's python3 against tmp config root (docker-free regression coverage).
- **Phase 02.6 plan 03 (2026-04-21)**: SKILL.md budget is body-only (post second-`---`, non-blank lines), measured via awk extractor not `wc -l`. Final: 10 body lines / 25 total (down from 245, ~90% reduction). Don't enumerate forbidden tools in SKILL.md — profile: minimal removes them from the agent surface, so documenting "don't use exec" both wastes tokens AND risks re-teaching the behavior.
- **Phase 02.6 plan 03 (2026-04-21)**: Prefixed tool-name convention (`roboclaws__observe` etc., double-underscore separator per spike F-2) is load-bearing in SKILL.md — the agent reads exactly the name the tool registry exposes, no translation. Dropped the optional SOULs pointer because SOULs load into `SOUL.md` via bootstrap, not via skill-file reference.
- **Phase 02.6 plan 04 (2026-04-21)**: Kickoff prompt delegates loop mechanics to SKILL.md rather than duplicating tool recipes — shrunk from 38 source lines / 13 non-empty to 7 source lines / 5 non-empty. No "if X fails, try Y" fallback language (that pattern is what let Kimi drift back to `exec` under Phase 2.5). `run_result_json["sim_server_metrics"]` JSON key kept verbatim across the HTTP -> MCP swap — the 8-key snapshot_metrics contract is stable so the JSON shape doesn't change; inline comment at emission site documents the name-vs-backing mismatch. `env.setdefault("ROBOCLAWS_MCP_URL", ...)` pattern (not `env[...]=...`) honors operator-supplied URLs; dual-layer regression coverage — bootstrap side (plan 02 Task 3) + example side (plan 04 Task 3) — guards threat T-02.6-23.
- **Phase 02.6 plan 05 (2026-04-21)**: Pure-deletion plan pattern works when upstream plans fully migrate callers — a recursive grep across `roboclaws/ examples/ tests/ scripts/` returned zero live importers before the `git rm`, and full pytest (475 passed, 1 skipped) held post-delete. Kept historical doc-comments referencing `sim_server.py` in mcp_server.py docstring + example + fixtures — the dependency-scan pattern scoped to `from/import sim_server|openclaw\.sim_server|SimHTTPServer` deliberately excludes prose refs, because the `sim_server_metrics` JSON key + trace-schema source-pointer metadata are frozen contracts that document schema continuity. Kept the plan-02 `SIM_SERVER_URL→ROBOCLAWS_MCP_URL` deprecation-warning fallback in the bootstrap (graceful-degrade for stale shells); only the dead `-e SIM_SERVER_URL=...` docker-run arg was removed.
- Phase 02.6 plan 06 (2026-04-21): Probe 1 uncovered plan 01 T-02.6-01 assumption error — 127.0.0.1 MCP bind unreachable from Gateway container on Linux kernel 6.17 + Docker 29.2.1; fix was host='0.0.0.0' at the example call site (not a default change in mcp_server.py), preserving threat-model intent for other callers.
- Phase 02.6 plan 06 (2026-04-21): Probe 6 prompt-token ratio = 0.568 against live Gateway image 2026.4.14 — not the 0.408 from the spike. The ROADMAP SC#4 threshold of <=0.50 cannot be honored without action; Task 8 operator to choose (revise threshold | trim MCP | image drift investigation).
- Phase 02.6 plan 07 (2026-04-21): Docs-update plan pattern — retro focuses on surprising-only lessons (host='0.0.0.0' Linux gotcha + coding-profile 26% drift) rather than recapping shipped facts. Shipped facts belong in per-plan SUMMARYs. Three-way doc cross-linking (retro ↔ operator ↔ internals) with no prose duplication. Orchestrator added retrospective as third deliverable beyond the plan's 2 tasks; committed under the same docs(phase-02.6-07) prefix.

### Roadmap Evolution

- Phase 2.4 closed (2026-04-24): **Better Views** now has a locked product decision. The repo keeps only the `map-v2+chase` runtime path; the old multi-variant experiment is retained as historical context plus analysis tooling, not as an active gate.
- Phase 12 completed (2026-05-08): **MolmoSpaces current-contract agent
  bridge** — current semantic cleanup contract exposed through FastMCP and
  validated with Codex, Claude Code, and OpenClaw Gateway against the same 5/5
  public rule-based baseline.
- Phase 13 completed (2026-05-08): **MolmoSpaces agent bridge visual results**
  — current-contract agent bridge reports now include robot-view images and
  semantic mid-phase rows comparable to the visual harness; public-agent score
  gaps are documented as private-target limitations.
- Phase 14 completed (2026-05-09): **MolmoSpaces real-world cleanup harness**
  — ADR-0003 public/private contract implemented with metric-map, room fixture
  hints, observed handles, deterministic private scoring, and three-seed real
  MolmoSpaces subprocess evidence.
- Phase 15 completed (2026-05-09): **MolmoSpaces Generated Mess Set scale** —
  ADR-0005 configurable hidden Generated Mess Set size with a real 10-object
  MolmoSpaces/RBY1M evidence run.
- Phase 16 completed (2026-05-09): **MolmoSpaces real-world agent MCP** —
  ADR-0006 exposes the ADR-0003 public cleanup contract through MCP without the
  current-contract `scene_objects` shortcut.
- Phase 17 completed (2026-05-09): **MolmoSpaces real-world agent dogfood** —
  ADR-0007 adds the direct coding-agent skill/server/checker kit for the
  ADR-0003 MCP surface and validates a clean Claude Code synthetic run.
- Phase 24 completed (2026-05-09): **MolmoSpaces planner runtime diagnostics** —
  ADR-0015 adds faulthandler-backed stderr crash evidence, dependency
  availability diagnostics, and shared-underlay Runtime Diagnostics reports for
  strict planner probe blockers.
- Phase 25 completed (2026-05-09): **MolmoSpaces planner headless renderer** —
  ADR-0016 localizes an EGL renderer-device override to the standalone planner
  probe worker and produces a passing strict Franka planner proof.
- Phase 26 completed (2026-05-09): **MolmoSpaces cleanup planner proof
  attachment** — ADR-0017 renders a strict standalone planner proof in cleanup
  reports without relabeling cleanup-loop primitives.
- Phase 27 completed (2026-05-09): **MolmoSpaces cleanup planner-backed
  primitive gate** — ADR-0018 defines, renders, and checker-gates the
  per-subphase evidence required for actual planner-backed cleanup primitive
  claims.
- Phase 28 planned (2026-05-09): **MolmoSpaces RBY1M CuRobo runtime gate** —
  ADR-0019 defines the target-robot runtime readiness gate before actual
  cleanup primitive replacement.
- Phase 28 completed (2026-05-09): **MolmoSpaces RBY1M CuRobo runtime gate** —
  ADR-0019 renders and checker-gates RBY1M/CuRobo readiness; current local
  evidence remains blocked because CuRobo JIT/config import times out before
  planner execution.
- Phase 29 planned (2026-05-09): **MolmoSpaces camera model policy cleanup** —
  ADR-0020 defines a camera-model policy mode that derives observed handles from
  public raw FPV observations with explicit simulated/model provenance while
  reusing the shared ADR-0003 semantic cleanup/report underlay.
- Phase 29 completed (2026-05-09): **MolmoSpaces camera model policy cleanup** —
  `camera_model_policy` mode and `infer_camera_model_candidates` register
  model-labelled observed handles from public raw FPV observations. The real
  MolmoSpaces/RBY1M visual artifact restores 2/2 generated targets and renders
  Raw FPV Observations, Camera Model Policy, Semantic Substeps, Robot View
  Timeline, Agent View, Private Evaluation, and the cleanup primitive gate in
  the shared report.
- Phase 30 planned (2026-05-09): **MolmoSpaces report underlay consolidation** —
  ADR-0021 defines the canonical Cleanup Artifact Report presentation sequence
  and shared report-facing semantic subphase labels.
- Phase 30 completed (2026-05-09): **MolmoSpaces report underlay consolidation** —
  `render_cleanup_report` now owns one visual core sequence across
  current-contract and ADR-0003 artifacts. Semantic Substeps, Robot View
  Timeline, and Cleanup Primitive Gate all reuse one semantic timeline mapping.
  Phase 59 later made the primary report labels plain (`nav`, `pick`, `open`,
  `place`) and kept object/target/surface/inside as secondary role detail.
- Phase 31 planned (2026-05-09): **MolmoSpaces RBY1M CuRobo warmup
  readiness** — ADR-0022 records staged worker evidence for RBY1M/CuRobo
  config/JIT warmup before retrying target execute-mode proof.
- Phase 31 completed (2026-05-09): **MolmoSpaces RBY1M CuRobo warmup
  readiness** — planner probe timeout artifacts now preserve worker stages and
  render `Worker Stage Timeline`. The local 300-second RBY1M/CuRobo run records
  `last_worker_stage=rby1m_config_import`, CuRobo available, CUDA Torch
  available, and strict readiness rejected because execute mode was not
  attempted.
- Phase 32 planned (2026-05-09): **MolmoSpaces RBY1M CuRobo cache isolation** —
  ADR-0023 defines an isolated `TORCH_EXTENSIONS_DIR` retry and CuRobo
  extension cache diagnostics before the next target execute-mode attempt.
- Phase 32 completed (2026-05-09): **MolmoSpaces RBY1M CuRobo cache
  isolation** — planner probe artifacts now record `CuRobo Extension Cache`.
  The output-local cache has 5/5 known CuRobo `.so` files and 0 locks. RBY1M
  config import succeeds; execute mode reaches `execute_policy_construct` and
  blocks on `AttributeError: module 'warp' has no attribute 'torch'`.
- Phase 33 planned (2026-05-09): **MolmoSpaces RBY1M Warp compatibility** —
  ADR-0024 defines a probe-local `warp.torch.device_from_torch` adapter and
  visible Warp API-shape evidence before the next target execute-mode retry.
- Phase 33 completed (2026-05-09): **MolmoSpaces RBY1M Warp compatibility** —
  planner probe artifacts now render `Warp Compatibility`. The probe-local
  adapter provides `warp.torch.device_from_torch`, target execution reaches
  `execute_policy_run_start`, and strict readiness remains blocked by CUDA
  `OutOfMemoryError`.
- Phase 38 completed (2026-05-09): **MolmoSpaces planner-backed cleanup
  primitive executor** — `PlannerBackedCleanupContractAdapter` and
  `planner_cleanup_primitive_executor_v1` now provide the only strict path from
  semantic cleanup subphases to `primitive_provenance=planner_backed`. The
  cleanup primitive gate rejects relabeled steps without per-call executor
  evidence, while default artifacts remain `api_semantic`.
- Phase 39 completed (2026-05-09): **MolmoSpaces planner primitive target
  binding** — the cleanup primitive gate now requires per-call planner evidence
  to match the semantic cleanup object and target fixture before a subphase is
  strict-ready. The report shows this binding in the Cleanup Primitive Gate
  table.
- Phase 40 completed (2026-05-09): **MolmoSpaces probe-backed cleanup primitive
  executor** — planner proof attachments can now become cleanup primitive
  executor results only when they have explicit cleanup primitive binding.
  Generic standalone target proof returns `planner_probe_missing_cleanup_binding`.
- Phase 41 planned (2026-05-09): **MolmoSpaces planner probe cleanup binding** —
  make the planner probe record sampled pickup/place task names, accept optional
  requested cleanup binding fields, and promote cleanup primitive binding only
  on exact request/sample match.
- Phase 41 completed (2026-05-09): **MolmoSpaces planner probe cleanup
  binding** - planner probe artifacts now carry sampled task binding,
  requested cleanup binding, promoted cleanup primitive binding on exact
  request/sample match, and mismatch blockers. Generic proof remains target
  runtime proof only.
- Phase 42 planned (2026-05-09): **MolmoSpaces observed handle planner
  binding** - split cleanup-facing observed handles from planner-facing sampled
  task aliases so probe proof can satisfy both ADR-0003 executor matching and
  upstream sampled-task matching.
- Phase 42 completed (2026-05-09): **MolmoSpaces observed handle planner
  binding** - `observed_handle_planner_binding_v1` resolves registered observed
  handles to backend planner aliases privately, extends probe binding aliases,
  and keeps promoted cleanup primitive binding keyed by the observed handle.
- Phase 43 planned (2026-05-09): **MolmoSpaces bounded planner cleanup
  executor** - add opt-in harness wiring so matching probe-backed proof can
  drive bounded shared-loop cleanup subphases without changing default cleanup.
- Phase 43 completed (2026-05-09): **MolmoSpaces bounded planner cleanup
  executor** - the ADR-0003 cleanup harness now has an opt-in
  `--use-planner-proof-for-cleanup-primitives` path. Matching proof binding
  wraps only the matching observed-handle/target loop with the probe-backed
  executor; default and mismatched-proof cleanup remain `api_semantic`.
- Phase 44 planned (2026-05-10): **MolmoSpaces planner proof bundle cleanup** -
  add proof-bundle attachment/selection so a full cleanup artifact can require
  one matching bound proof per cleaned object before the planner cleanup bridge
  reports ready.
- Phase 44 completed (2026-05-10): **MolmoSpaces planner proof bundle
  cleanup** - `planner_backed_cleanup_proof_bundle_v1` attaches multiple
  strict bound proofs, the ADR-0003 harness selects the matching proof per
  observed handle/target, and the synthetic seed-7 full cleanup passes the
  existing planner primitive and bridge-ready checker gates.
- Phase 45 completed (2026-05-10): **MolmoSpaces report visual core
  contract** - current-contract and ADR-0003 checkers now enforce one visual
  report core, and ADR-0003 MCP robot-view capture reuses the shared semantic
  timeline mapping.
- Phase 46 completed (2026-05-10): **MolmoSpaces planner proof request
  manifest** - ADR-0003 cleanup artifacts now emit private proof request
  manifests, and a local runner writes exact dry-run proof-bundle commands with
  opt-in probe execution and cleanup rerun.
- Phase 47 completed (2026-05-10): **MolmoSpaces planner proof request report
  view** - cleanup reports now render private planner proof requests after
  planner bridge evidence and before Agent View, while the checker keeps older
  no-manifest artifacts valid.
- Phase 48 completed (2026-05-10): **MolmoSpaces planner proof bundle runner
  report** - the local proof-bundle runner now writes `report.html` beside its
  JSON manifest, including exact probe commands, expected proof reports, and
  optional cleanup rerun command evidence.
- Phase 49 completed (2026-05-10): **MolmoSpaces planner proof bundle runner
  checker** - the local proof-bundle runner manifest/report pair now has a
  checker for schema, counts, command metadata, report sections, and optional
  expected proof output existence.
- Phase 50 completed (2026-05-10): **MolmoSpaces MCP smoke shared semantic
  loop** - current-contract and ADR-0003 MCP smoke demos now reuse the shared
  `nav -> pick -> nav -> open? -> place` cleanup driver.
- Phase 51 completed (2026-05-10): **MolmoSpaces planner proof bundle runner
  harness** - the proof-bundle runner has a dry-run harness and verification
  recipe for repeatable command/report generation.
- Phase 52 completed (2026-05-10): **MolmoSpaces planner proof bundle cleanup
  rerun artifacts** - executed proof-bundle flows now name final cleanup rerun
  manifests/reports/checker outputs explicitly.
- Phase 53 completed (2026-05-10): **MolmoSpaces planner proof bundle execute
  rerun** - the local-dev gate executes bound proof bundles, reruns cleanup,
  and checks final planner-backed cleanup readiness; its first real run exposed
  sampled-task mismatch as the blocker.
- Phase 54 completed (2026-05-10): **MolmoSpaces bind proof probes to cleanup
  scene** - proof-bundle commands now carry the real cleanup scene XML and
  requested planner aliases; local exact-scene probes narrow the blocker to
  upstream `HouseInvalidForTask` / RBY1M robot placement infeasibility.
- Phase 55 completed (2026-05-10): **MolmoSpaces proof bundle result
  feasibility report** - executed proof-bundle runner manifests/reports now
  summarize each proof's status, task-feasibility classification, cleanup
  binding promotion, blockers, proof report links, and planner views.
- Phase 56 completed (2026-05-10): **MolmoSpaces proof request feasibility
  selection** - proof-bundle runs can now consume prior result summaries, skip
  requests already known task-feasibility blocked, and report fallback-required
  state when no ready request remains.
- Phase 57 completed (2026-05-10): **MolmoSpaces proof request fallback
  generation** - proof-bundle runs can now generate private alternate
  planner-alias requests for prior task-feasibility-blocked source requests
  while preserving cleanup-facing IDs.
- Phase 58 completed (2026-05-10): **MolmoSpaces generated fallback proof
  execution** - four generated fallback proof requests executed locally and
  passed the runner checker with required proof outputs, but all timed out at
  `rby1m_config_import` before task sampling, planner-backed proof, cleanup
  binding promotion, or planner views.
- Phase 59 completed (2026-05-10): **MolmoSpaces plain semantic report labels**
  - shared cleanup reports now use `nav`, `pick`, `nav`, optional `open`, and
  `place` as primary labels while preserving role detail separately.
- Phase 60 completed (2026-05-10): **MolmoSpaces fallback timeout stage
  reporting** - generated fallback proof result summaries and runner reports
  now surface timeout counts, execution-attempted state, last worker stage,
  compact worker stage events, and stdout/stderr paths.
- Phase 61 completed (2026-05-10): **MolmoSpaces fallback proof warmup** -
  proof-bundle runs can include a visible RBY1M/CuRobo config-import warmup
  sharing an output-local Torch extension cache with proof commands.
- Phase 62 completed (2026-05-10): **MolmoSpaces warmed generated fallback
  proof execution** - warmed local execution reached task sampling and moved
  the blocker from config-import timeout to invalid exact-scene planner aliases.
- Phase 63 completed (2026-05-10): **MolmoSpaces exact-scene fallback alias
  validation** - generated fallback commands now filter upstream/display aliases
  and report filtered candidates instead of retrying known-invalid IDs.
- Phase 64 completed (2026-05-10): **MolmoSpaces fallback runtime alias
  discovery** - prior exact-scene `KeyError` valid-name lists now produce
  same-family runtime sibling fallback commands and report discovered aliases.
- Phase 5 completed (2026-04-23): **Iterative codebase simplification** — all 9 plans closed, 18 target files simplified, net `-203` targeted lines, and final repo-wide `pytest` + `ruff` gates passed. Per-plan summaries live under `.planning/phases/05-iterative-codebase-simplification/`.
- Phase 4 added (2026-04-23): **Refactor regression harnesses for VLM, territory/coverage, and OpenClaw**. The phase was added via the `phase.add` workflow, then tightened for this repo: root `PLAN.md` is explicitly kept as a source context file, `04-CONTEXT.md` seeds the planning bundle, and the intended harness shape follows existing repo patterns (`results.jsonl` runner + separate analyzer + small fixture-backed contract tests).

### Pending Todos

[From .planning/todos/pending/ — none yet. Root `TODOS.md` is also empty by design as of 2026-04-20; all future TODOs originate from this roadmap.]

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260423-q71 | codebase simplification: extract game helpers, dedup example utilities, split vlm.py providers, split bridge.py transport, refactor reporter build_run_section | 2026-04-23 | 9e1fe35 | [260423-q71-codebase-simplification-extract-game-hel](./quick/260423-q71-codebase-simplification-extract-game-hel/) |

### Blockers/Concerns

- No active blocker for the MolmoSpaces cleanup definition of done. Phase 08
  completed the real-scene subprocess proof, Phase 09 completed the
  target-facing FPV / same-room visual-review follow-up, Phase 10 completed
  the semantic substep / fridge containment / report-row follow-up, Phase 11
  completed the held-object carry visual follow-up, Phase 12 completed
  current-contract Codex/Claude/OpenClaw tool-viability proof, Phase 13
  completed visual agent bridge reporting, and Phase 14 completed ADR-0003
  public/private cleanup separation. Phase 15 completed larger hidden generated
  mess sets, Phase 16 completed the ADR-0003 MCP surface, and Phase 17
  completed direct coding-agent dogfood on that surface. Phase 18 completed
  synthetic OpenClaw Gateway viability, Phase 19 completed real visual OpenClaw
  evidence, Phase 20 completed semantic-loop enforcement, Phase 21 completed
  advisory scoring/model checks, Phase 22 completed raw FPV-only perception
  evidence, Phase 23 completed planner-backed provenance/proof gating, and
  Phase 24 completed runtime diagnostics for strict planner blockers. Phase 25
  completed standalone strict Franka planner proof with a headless renderer
  adapter. Phase 26 attached that proof to cleanup reports while preserving
  `api_semantic` cleanup primitive provenance. Phase 27 completed the
  per-subphase primitive gate before actual primitive replacement. Phase 28
  completed the RBY1M/CuRobo readiness boundary, which is currently blocked by
  CuRobo JIT/config-import timeout before planner execution. Phase 29 completed
  camera-only model-policy cleanup, Phase 30 consolidated the shared report
  visual core, and Phase 31 made that RBY1M/CuRobo warmup blocker precise:
  `output/molmo-planner-rby1m-curobo-warmup/run_result.json` records
  `last_worker_stage=rby1m_config_import` after a 300-second timeout. Phase 32
  proved an isolated output-local cache gets RBY1M config import through
  `CuroboPickAndPlacePlannerPolicy`, and execute mode now blocks later at Warp
  API compatibility (`module 'warp' has no attribute 'torch'`). Phase 33 makes
  that adapter visible and probe-local, then moves execution to
  `execute_policy_run_start`; Phase 35 later produced strict standalone target
  proof, Phase 36 consolidated the shared loop, Phase 37 added bridge-readiness
  evidence, Phase 38 added the strict primitive executor seam, Phase 39 bound
  primitive evidence to exact cleanup object/target, Phase 40 added the
  probe-backed executor adapter, Phase 41 made the probe emit exact-match
  cleanup binding, Phase 42 split observed handles from planner aliases, Phase
  43 wired matching proof into a bounded shared-loop cleanup attempt, Phase 44
  added proof-bundle coverage for every cleaned object/subphase, Phase 45
  enforced the shared report visual core, Phase 46 added private proof request
  manifests plus the local bundle runner, Phase 47 rendered those requests in
  cleanup reports, Phase 48 rendered proof-bundle runner command reports, and
  Phase 49 added a checker for those runner artifacts. Phase 50 removed the
  remaining MCP smoke-loop duplication, Phase 51 added a proof-bundle runner
  dry-run harness, Phase 52 tracked cleanup rerun artifacts, Phase 53 added the
  local execute-rerun gate, and Phase 54 bound probes to the exact cleanup
  scene. Phase 55 made executed proof-bundle result status, task feasibility,
  blockers, binding promotion, and planner views visible in the bundle report.
  Phase 56 added proof request feasibility selection from prior summaries.
  Phase 57 added generated fallback proof requests from private planner-alias
  candidates. Phase 58 executed those generated requests and showed the active
  planner-backed cleanup blocker is now timeout at `rby1m_config_import`, not
  report drift, random alias sampling, missing fallback generation, or repeated
  known-infeasible reruns.
- **Known Phase 02.6 artifact gap (now planned as Phase 02.7):** Autonomous artifacts currently show tool traffic plus the final assistant message, but not the intermediate assistant transcript. This is a queued follow-up, not a blocker for the already-shipped 02.6 MCP loop.
- **Environment split is real:** this local session had AI2-THOR available,
  VLM keys in `.env`, and the isolated Python 3.11 MolmoSpaces runtime. Phase
  08 makes claims only about real MolmoSpaces/MuJoCo scene loading and
  semantic state mutation, not about real VLM/OpenClaw behavior.

> **Resolved 2026-04-20:** The two WARNINGs initially carried from
> `.planning/INGEST-CONFLICTS.md` (image-payload contract, coverage
> semantics) were verified stale — both were already shipped in commit
> `ddfb523` on 2026-04-15, and issue #52 was closed the same day. The
> stale-ingest claim came from a dated validation report
> (`docs/research/05-real-model-smoke-validation.md`, 2026-04-14) that
> the synthesizer treated as current state. See
> `.planning/INGEST-CONFLICTS.md` "UPDATE 2026-04-20" header for full
> evidence and the `feedback_verify_ingest_claims` memory for the
> lesson.

- **Resolved 2026-04-21:** Phase 02.6 plan 06 Probe 6 threshold (ratio 0.568 > 0.50) resolved by revising ROADMAP SC#4 from ≤0.50 to ≤0.60 to match live Gateway reality. Live probe's 43% reduction is a real, material win; spike's 0.408 is not reproducible because Gateway's coding profile shrank 26% between the spike and the probe on the same image tag. Full narrative in `docs/retrospectives/phase-2.6.md` § "The two surprises worth remembering" #2.

## Deferred Items

Items acknowledged and carried forward from the new-mode ingest:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Ops | Gateway image digest pin (`sha256:7ea07…a594ed`) | LOCKED DECLINED | 2026-04-20 |
| Architecture | Phase 3 Isaac Lab migration (humanoid + multi-embodiment nav) | Deferred indefinitely (requires GPU + USD scenes) | 2026-04-20 |
| Framing | Phase 2.2 UC1 Persona Showdown / UC2 cross-run MEMORY | Rejected at final gate | 2026-04-16 |

## Session Continuity

Last session: 2026-05-13T18:08:00+08:00
Stopped at: Phase 135 MolmoSpaces CI live-agent reports implemented and
non-live verified. A branch `workflow_dispatch` found the Molmo live job needed
`just` installed and confirmed GitHub Pages deployment is protected to `main`;
branch dispatches can rehearse the matrix without deploying Pages.
The next external validation should run `workflow_dispatch` with
`molmo_live=true` on `main` or push to `main` with `[molmo-live]` in the commit
message, using the configured GitHub Actions secrets `KIMI_API_KEY` and
`MIMO_TP_KEY`.
Report generation routes Molmo cleanup artifacts to the shared visual underlay,
prior-covered selection can reselect one-step proof memory when a higher
horizon is requested, proof-bundle dry-run reports expose command quality plus
semantic subphase intent, request filtering keeps the next local proof attempt
to one selected command, and executable `--cleanup-tools` now matches the
report rail.
Latest phase artifacts are
`docs/adr/0125-canonicalize-proof-command-cleanup-tool-order.md`,
`docs/plans/molmospaces-canonical-proof-command-tool-order.md`, and
`.planning/phases/134-molmospaces-canonical-proof-command-tool-order/134-01-canonical-proof-command-tool-order-PLAN.md`.
Phase 37 evidence lives under
`output/molmospaces-planner-cleanup-bridge-readiness/` and remains bridge-blocked
for full cleanup because it predates proof-bundle coverage.
Latest executed cleanup artifact:
`output/debug-phase94-seeded-source-candidate-seed9/run_result.json`.
Latest executed standalone proof artifact:
`output/debug-phase109-grasp-collision-diagnostics/run_result.json`.
Latest proof-bundle dry-run artifact:
`output/debug-phase134-canonical-tool-order-dry-run/proof_bundle_run_manifest.json`.
Latest proof-bundle dry-run report:
`output/debug-phase134-canonical-tool-order-dry-run/report.html`.
Latest grasp-cache generation artifact:
`output/debug-phase118-grasp-cache-generation-min/generation_result.json`.
Latest grasp-cache generation report:
`output/debug-phase118-grasp-cache-generation-min/report.html`.
Latest grasp-filter diagnostics artifact:
`output/debug-phase119-grasp-filter-diagnostics/filter_diagnostics_result.json`.
Latest grasp-filter diagnostics report:
`output/debug-phase119-grasp-filter-diagnostics/report.html`.
Latest regenerated stale report:
`output/molmo-agent-bridge-visual-codex/report.html`.
Latest regenerated scenario-less report:
`output/molmo-realworld-report-underlay-visual/report.html`.
Latest grasp initial-contact diagnostics artifact:
`output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json`.
Latest grasp initial-contact diagnostics report:
`output/debug-phase121-grasp-initial-contact-diagnostics/report.html`.
Latest grasp pose-policy cache artifact:
`output/debug-phase122-grasp-pose-policy-cache/pose_policy_cache_result.json`.
Latest grasp pose-policy cache report:
`output/debug-phase122-grasp-pose-policy-cache/report.html`.
Latest cache-ready exact proof artifact:
`output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json`.
Latest cache-ready exact proof report:
`output/debug-phase123-cache-ready-proof001-warmed-rerun/report.html`.
Latest planner-backed exact proof artifact:
`output/debug-phase125-curobo-pregrasp-exception-context/run_result.json`.
Latest planner-backed exact proof report:
`output/debug-phase125-curobo-pregrasp-exception-context/report.html`.
Latest bound-proof cleanup rerun artifact:
`output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json`.
Latest bound-proof cleanup rerun report:
`output/debug-phase126-phase125-bound-proof-cleanup-rerun/report.html`.
Latest focused cleanup report examples:
`output/molmo-agent-bridge-visual-codex/report.html` and
`output/molmo-realworld-report-underlay-visual/report.html`.
Latest Molmo CI live dry-run manifest:
`output/molmo/ci-rehearsal-all/site/molmo/live/live-report-manifest.json`.
Resume file: .planning/phases/135-molmospaces-ci-live-agent-reports/135-01-ci-live-agent-reports-PLAN.md

## Dual-Stack Workflow

- **gstack** owns pre-plan deliberation: `docs/`, `PLAN.md` (root), research reports.
- **GSD** owns execution: `.planning/` (this directory), STATE.md, ROADMAP.md, phase plans.
- Pre-plan → plan handoff: when a drafted phase in root `PLAN.md` is ready for execution, the owner runs `/gsd-plan-phase <phase>` and this STATE.md is updated.

**Active Phase:** None. Phase 135 MolmoSpaces CI live-agent reports is complete
for repo-side implementation and non-live verification; hosted live proof is
pending GitHub Actions secrets and an opt-in workflow run.
