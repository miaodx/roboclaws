---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Better Views
status: active
stopped_at: Phase 45 MolmoSpaces report visual core contract completed on 2026-05-10; next planner-backed cleanup work should produce or rerun real multi-proof artifacts.
last_updated: "2026-05-10T00:00:00+08:00"
last_activity: 2026-05-10
progress:
  total_phases: 38
  completed_phases: 38
  total_plans: 41
  completed_plans: 41
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** First public demonstration of multiple OpenClaw agent instances simultaneously controlling multiple simulated robots in competition and cooperation, with visible output for every feature.
**Current focus:** Phase 45 completed report visual-core consolidation after the ADR/report gap review. The next planner-backed cleanup slice should produce or rerun real multi-proof artifacts rather than only synthetic proof-bundle coverage.

## Current Position

Phase: 45 (molmospaces-report-visual-core-contract) - COMPLETE
Plan: 1 of 1 complete - `45-01` centralized report visual-core checks and
removed duplicated ADR-0003 MCP robot-view semantic mapping.
Status: Phase 35 produced strict standalone target planner-backed proof with
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
ADR-0003 visual review.
Last activity: 2026-05-10 - Completed Phase 45 report visual core contract.

Progress: [##########] 100%
Phase 45 note: stale ignored `output/` reports may fail the tightened visual-core checker until regenerated with the shared renderer.
(Phase 08 satisfies the MolmoSpaces prompt-cleanup definition of done with a real upstream MuJoCo scene and subprocess backend. Phase 09 completes the visual FPV/same-room follow-up. Phase 10 completes the semantic-substep/report follow-up. Phase 11 completes the held-object carry visual follow-up. Phase 12 proves current-contract agent/OpenClaw tool viability. Phase 13 makes those agent bridge artifacts visually reviewable. Phase 14 implements the ADR-0003 public/private real-world-style cleanup boundary. Phase 15 closes the larger hidden Generated Mess Set lower-bound gap. Phase 16 exposes the ADR-0003 MCP agent surface. Phase 17 completes direct coding-agent dogfood on that stricter surface. Phase 18 completes synthetic OpenClaw Gateway dogfood on the same ADR-0003 MCP surface. Phase 19 completes real visual evidence on the same surface. Phase 20 completes clean-policy semantic-loop enforcement. Phase 21 completes advisory scoring/model-check artifacts. Phase 22 completes raw FPV-only perception evidence. Phase 23 completes the planner-backed manipulation provenance/proof gate. Phase 24 completes runtime diagnostics for strict planner probe blockers. Phase 25 completes the headless renderer blocker and produces a strict Franka planner-backed proof. Phase 26 attaches that proof to cleanup reports without changing cleanup-loop primitive provenance. Phase 27 completes the per-subphase cleanup primitive gate. Phase 28 completes the RBY1M/CuRobo target-runtime gate. Phase 29 completes camera-only model-policy cleanup. Phase 30 completes canonical report visual-core consolidation. Phase 31 completes staged RBY1M/CuRobo warmup evidence. Phase 32 completes isolated CuRobo extension-cache evidence. Phase 33 completes visible Warp compatibility evidence.)

## Performance Metrics

**Velocity:**

- Total plans completed: 45 (18 historical retrofit + 3 completed in Phase 02.4 + Phase 6/7/8/9/10/11/12/13/14 MolmoSpaces plans plus follow-on MolmoSpaces slices through Phase 45)
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

- Last 3 shipped phases: 43, 44, 45
- Trend: MolmoSpaces cleanup path now has ADR-0003 cleanup reports that attach strict planner proof without changing cleanup primitive provenance, a strict per-subphase gate for future planner-backed cleanup primitives, a target RBY1M/CuRobo runtime gate, a camera-only model-policy cleanup path, one canonical report visual core shared across the demos, staged RBY1M/CuRobo warmup-readiness evidence, isolated CuRobo extension-cache evidence, visible Warp compatibility evidence, measured CUDA memory headroom evidence, strict standalone RBY1M/CuRobo planner-backed proof under a visible low-memory profile, one shared semantic cleanup driver, explicit planner cleanup bridge-readiness evidence, a strict per-call executor seam for planner-backed cleanup primitives, object/target binding for that evidence, a probe-backed executor adapter that blocks generic standalone proof, planner probe diagnostics that promote cleanup binding only on exact request/sample match, private observed-handle to planner-alias binding, bounded opt-in executor wiring for one matching cleanup object, proof-bundle coverage for full synthetic cleanup gate readiness, and a shared visual-core checker that rejects stale report shapes.

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
  Timeline, and Cleanup Primitive Gate all reuse the shared `nav/object`,
  `pick/object`, `nav/target`, `open/target`, `place/surface`, and
  `place/inside` labels.
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
  43 wired matching proof into a bounded shared-loop cleanup attempt, and Phase
  44 added proof-bundle coverage for every cleaned object/subphase.
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

Last session: 2026-05-09T00:00:00+08:00
Stopped at: Phase 44 MolmoSpaces planner proof bundle cleanup completed. The
next implementation should produce or rerun real multi-proof artifacts using
the bundle path.
Latest phase artifacts are
`docs/adr/0035-use-bound-planner-proof-bundles-for-cleanup-coverage.md`,
`docs/plans/molmospaces-planner-proof-bundle-cleanup.md`, and
`.planning/phases/44-molmospaces-planner-proof-bundle-cleanup/44-01-planner-proof-bundle-cleanup-PLAN.md`.
Phase 37 evidence lives under
`output/molmospaces-planner-cleanup-bridge-readiness/` and remains bridge-blocked
for full cleanup because it predates proof-bundle coverage.
Resume file: .planning/phases/44-molmospaces-planner-proof-bundle-cleanup/44-01-planner-proof-bundle-cleanup-PLAN.md

## Dual-Stack Workflow

- **gstack** owns pre-plan deliberation: `docs/`, `PLAN.md` (root), research reports.
- **GSD** owns execution: `.planning/` (this directory), STATE.md, ROADMAP.md, phase plans.
- Pre-plan → plan handoff: when a drafted phase in root `PLAN.md` is ready for execution, the owner runs `/gsd-plan-phase <phase>` and this STATE.md is updated.

**Active Phase:** None. Phase 44 MolmoSpaces planner proof bundle cleanup is
complete; next work should plan real multi-proof artifact generation or a local
rerun using the new repeated-proof path.
