---
refactor_scope: python-quality-backend-entropy
status: CONTINUE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-14
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

CONTINUE

## Target

Continue the code-size and complexity cleanup after the completed
`refactor-reduce-entropy-loop` quality ratchet. The existing ratchet prevents
new debt and growth in current debt; this plan pays down the current baseline
by choosing bounded, live seams instead of starting a broad rewrite.

Primary target:

- Make household cleanup backends more consistent through a small backend
  facade/protocol layer.
- Move backend-specific runtime metadata, diagnostics, artifact attachment,
  and worker command plumbing out of `run_realworld_cleanup`.
- Use each completed slice to lower the explicit Python quality baseline and
  run another bounded reduce-entropy discovery round.

## Accepted Severities

- P0: current false-green verification, runtime breakage, or public command
  behavior regression.
- P1: live cleanup contract/gate complexity that hides failure, forces repeated
  rediscovery, or blocks small feature work.
- P2: target-local maintainability cleanup that lowers the ratchet baseline,
  removes duplicate backend handling, or makes the selected seam canonical.

## Zoom-Out Map

Current public route:

```text
just run::surface
  -> roboclaws.launch catalog/runners
  -> roboclaws.household.realworld_cleanup.run_realworld_cleanup
  -> backend instance
       api_semantic_synthetic
       molmospaces_subprocess
       isaaclab_subprocess
  -> CleanupBackendSession
  -> RealWorldCleanupContract
  -> trace / runtime map / private eval / report.html / run_result.json
```

Current backend pressure points:

- `CleanupBackendSession` is a thin direct-call wrapper. It forwards robot
  actions but does not define the backend metadata, diagnostics, artifact, or
  rendering contract.
- `MolmoSpacesSubprocessBackend` and `IsaacLabSubprocessBackend` already share
  many operations, but their worker runners, runtime fields, and diagnostics are
  assembled by convention rather than a common surface.
- `run_realworld_cleanup` currently builds the backend, mutates the cleanup
  contract, writes artifacts, then reaches back into backend internals with
  `getattr` and `backend == ...` branches to populate `run_result`.
- `realworld_mcp_server._backend_name` still infers backend ids from concrete
  class names.

The intended shape is:

```text
run_realworld_cleanup
  -> build_cleanup_backend(...)
  -> HouseholdBackendSession / facade
       actions: observe, navigate, pick, place, done
       optional capabilities: snapshots, robot views, camera control
       metadata: backend id, runtime metadata, diagnostics, artifacts
  -> RealWorldCleanupContract
  -> attach_backend_run_artifacts(run_result, backend_facade)
```

The public launch axes stay unchanged. This is an internal shape cleanup.

## Eng-Review Recommendation

Start with the backend facade because it reduces complexity in the main cleanup
orchestrator and creates a stable seam for later file-size reductions. Do not
try to split the 8k-line worker scripts first: those scripts are heavy backend
implementation detail, and splitting them before the facade would preserve the
same leakage through more files.

Use an incremental strangler approach:

1. Introduce the common backend metadata/artifact surface.
2. Move existing run-result backend branches behind that surface.
3. Refactor worker command runners only after callers use the common facade.
4. Ratchet the baseline down after each slice.

Rejected alternatives:

- Full backend rewrite: too much blast radius and local simulator risk.
- Splitting workers first: reduces file length but does not fix the more
  important orchestration leakage.
- Raising Ruff/Pylint thresholds globally: likely creates noise without making
  the next cleanup more obvious.

## Accepted Cleanup Checklist

- [x] **B1: Define a backend facade/protocol for household cleanup runs.**
  - Add a small typed surface for backend id, scenario, action methods,
    optional render/camera capabilities, runtime metadata, diagnostics, and
    artifact attachment.
  - Keep the public `backend=` launch axis unchanged.
  - Preserve the current agent-facing contract: no private evaluator truth in
    public profile metadata or agent inputs.

- [x] **B2: Move backend construction out of `run_realworld_cleanup`.**
  - Replace the inline `if backend == ...` construction block with a
    `build_cleanup_backend(...)` style factory.
  - Keep MolmoSpaces, Isaac Lab fake mode, and synthetic direct backend
    behavior equivalent.
  - Remove concrete-class-name backend inference from live paths where the new
    facade can provide a backend id.

- [x] **B3: Move backend runtime metadata and artifact attachment behind the
  facade.**
  - Replace the `run_result` block that reaches into `backend_instance` with
    backend-owned metadata/artifact payloads.
  - Preserve existing keys such as `molmospaces_runtime`, `isaac_runtime`,
    `mess_placement_diagnostics`, `placement_diagnostics`, `robot`, and
    `robot_import` unless a narrower follow-up explicitly migrates report
    consumers.
  - Keep `isaac_scene_index.json` creation covered by the backend artifact
    attachment path.

- [x] **B4: Normalize subprocess worker command execution.**
  - Extract shared process-runner concerns used by MolmoSpaces and Isaac Lab:
    command assembly, timeout lookup, JSON parsing, environment preparation,
    and error formatting.
  - Keep MolmoSpaces persistent-worker behavior as a Molmo-specific capability,
    not a mandatory base abstraction.
  - Do not import Isaac packages in the normal Roboclaws process.

- [x] **B5: Move optional backend capabilities behind the facade.**
  - Target `roboclaws/household/backend_contract.py`,
    `roboclaws/household/realworld_cleanup.py`, and
    `roboclaws/household/realworld_mcp_server.py`.
  - Add explicit facade methods/properties for snapshot capture, robot-view
    capture support, robot-view recording, backend close, final locations, and
    requested generated mess count.
  - Replace direct `base_contract.backend` feature probes in direct cleanup and
    live MCP cleanup with those facade methods.
  - Preserve synthetic fallback snapshots, visual-backend robot-view artifacts,
    public artifact schemas, and fake Isaac tests.

- [x] **B6: Normalize MolmoSpaces worker command dispatch.**
  - Target `scripts/molmo_cleanup/molmospaces_subprocess_worker.py`.
  - Replace the duplicated one-shot `main(...)` command branch and persistent
    `run_state_command(...)` branch with one backend command dispatch table or
    shared handler.
  - Keep persistent-worker behavior MolmoSpaces-specific; this is the
    worker-internal parity follow-up after B4 normalized the parent process
    runner.
  - Preserve JSON result shapes, state writeback behavior, and current
    MolmoSpaces subprocess backend tests.

- [x] **B7: Adopt the cleanup backend facade in live MCP server setup and
  MCP smoke setup.**
  - Target `roboclaws/cli/household_agent_server.py` and
    `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py`.
  - Replace duplicated MolmoSpaces / Isaac Lab / synthetic backend construction
    and private-target scenario fallback with `build_cleanup_backend_session(...)`
    and the shared run-option validators where the path is not Agibot-specific.
  - Keep Agibot GDK setup behind `AgibotCleanupMCPContract`; it is a separate
    backend adapter family, not a reason to broaden the generic facade.
  - Preserve current MCP server CLI flags, smoke behavior, and active `just`
    verification recipes.

- [x] **Q1: Add a quality-debt selection report to the ratchet.**
  - Extend `scripts/dev/check_python_quality_ratchet.py` with a read-only
    summary mode such as `--summary` or `--top-debt`.
  - Show top oversized modules, highest individual complexity entries, and
    complexity grouped by file.
  - Keep default gate output terse so hooks and CI stay readable.

- [x] **Q2: Lower the explicit baseline after each accepted slice.**
  - Run the ratchet in write-baseline mode only after the focused tests pass.
  - Record the before/after counts in this plan's execution log.
  - Do not refresh the baseline to hide new debt.

- [x] **C1: Split the live cleanup checker assertion pipeline.**
  - Target `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`.
  - Extract assertion phases for core run result, public agent view, runtime
    metric map, backend-specific runtime evidence, and waypoint honesty.
  - Preserve CLI flags and current `just verify` / `just harness` behavior.

- [x] **C1.1: Split remaining live checker Agibot and minimal-map families.**
  - Target `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
    and focused helper modules under `scripts/molmo_cleanup/`.
  - Extract Agibot semantic-map build, Agibot G2 hardware, and minimal-map
    assertion families while keeping current private checker entrypoints as
    imports or aliases for tests.
  - Keep `parse_args` as a parked CLI-shape row unless it can be bundled with a
    material checker split.
  - Preserve current `just verify` / `just harness` behavior and checker
    contract tests.

- [x] **C1.5: Split direct cleanup orchestration from artifact/result assembly.**
  - Target `roboclaws/household/realworld_cleanup.py`.
  - Extract the post-loop artifact writer, run-result payload builder, profile
    metadata attachment, planner-proof attachment, and report/writeback stages
    from `run_realworld_cleanup`.
  - Keep public `run_result.json`, `agent_view.json`, `runtime_metric_map.json`,
    `private_evaluation.json`, `advisory_evaluation.json`, and `report.html`
    schemas stable.

- [x] **C1.55: Split residual direct cleanup loop orchestration.**
  - Target `roboclaws/household/realworld_cleanup.py`.
  - Extract route/setup normalization, policy selection, waypoint scan loop,
    minimal-map deferred cleanup, done fallback, and snapshot/robot-view stages
    from `run_realworld_cleanup` only where the helper names make the flow more
    obvious.
  - Keep `run_realworld_cleanup(...)` as the public direct-run API and preserve
    artifact schemas.

- [x] **C1.6: Split live MCP cleanup done finalization from server orchestration.**
  - Target `roboclaws/household/realworld_mcp_server.py`.
  - Extract MCP `done` artifact writing, `run_result` construction, profile/map/
    backend metadata attachment, planner-proof attachment, report rendering, and
    writeback into a focused finalizer module.
  - Use the backend facade's `backend_name()` and `attach_runtime_metadata(...)`
    path directly instead of retaining local backend-name/runtime wrappers.
  - Preserve live-agent fields such as `mcp_server`, `intent_status`,
    `goal_status`, `cleanup_status_role`, `runtime_timing`,
    `agent_diagnostics`, `cleanup_plan`, and `robot_view_capture_policy`.

- [x] **C2: Extract RealWorldCleanupContract construction and payload builders.**
  - Target `roboclaws/household/realworld_contract.py`.
  - Constructor option normalization and map/runtime initialization are split
    into `roboclaws/household/realworld_contract_init.py`.
  - Runtime metric map and cleanup worklist payload assembly are split into
    `roboclaws/household/realworld_contract_payloads.py`.
  - Keep public payload schemas stable.

- [x] **C2.5: Split cleanup policy trace event classification and summary.**
  - Target `roboclaws/household/realworld_contract.py` and a focused policy
    trace helper module.
  - Extract event iteration, waypoint accounting, post-place observation
    accounting, loop-style classification, and final summary payload assembly.
  - Preserve the `cleanup_policy_trace_from_events(...)` public helper and the
    `CLEANUP_POLICY_TRACE_SCHEMA` payload shape.

- [x] **C3: Split cleanup report sections from shared HTML wrapper.**
  - Target `roboclaws/household/report.py`.
  - Extract coherent report sections without rewriting visual output.
  - First extracted section modules:
    `roboclaws/household/report_sections_map.py` and
    `roboclaws/household/report_sections_timing.py`; action-evidence badges now
    live in `roboclaws/household/report_sections_action.py`; grasp-cache
    preflight sections now live in
    `roboclaws/household/report_sections_grasp_cache.py`; proof-bundle runner
    command, preflight, mitigation, warmup, and rerun artifact sections now live
    in `roboclaws/household/report_sections_proof_bundle.py`; Agent View,
    runtime-map/worklist, cleanup-policy trace, and real-robot readiness
    sections now live in `roboclaws/household/report_sections_agent.py`; Robot
    View Timeline, FPV bbox verification, camera-contract badges, and
    visual-core step filtering now live in
    `roboclaws/household/report_sections_robot.py`.
    Manipulation provenance, attached planner proof(s), cleanup primitive gate,
    planner cleanup bridge, and planner proof request sections now live in
    `roboclaws/household/report_sections_proof.py`.
  - Planner-probe and proof-bundle runner result renderers are intentionally
    left in `report.py`; they are different report families and should move
    only under a separate material slice.
  - Keep `report.html` visual core tests green.

- [x] **P1: Split planner-proof bundle checker assertion phases.**
  - Target `scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py`.
  - Extract staged checks for manifest/core counts, report rendering,
    local-runtime preflight, proof request selection, proof result summary,
    proof quality, grasp-cache mitigation, and cleanup rerun output.
  - Preserve CLI flags and current `just verify::molmo-planner-proof-*` /
    `just harness::molmo-planner-proof-*` behavior.

- [x] **P2: Split planner manipulation probe checker assertion phases.**
  - Target `scripts/molmo_cleanup/check_molmo_planner_manipulation_probe.py`.
  - Extract staged checker assertions for artifact/report core, runtime
    diagnostics, task-sampler diagnostics, cleanup binding, required capability
    gates, proof quality, and final blocked/planner-backed status.
  - Preserve CLI flags, direct `_assert_probe_result(...)` test hook, and
    current `just verify::molmo-planner-manipulation-probe` behavior.

- [ ] **P3: Split planner manipulation probe runtime and result packaging.**
  - Target `scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` and
    focused helper modules under `scripts/molmo_cleanup/`.
  - Extract runtime diagnostics, task-sampler adapters, worker invocation, and
    result/report packaging.
  - Keep blocked-capability evidence valid by default; strict planner-backed
    proof remains a local-runtime gate.
  - Status after 2026-06-14 loop: parent-process result packaging,
    task-sampler diagnostics, and `_execute_policy_probe(...)` stage splitting
    are complete. The remaining C901 11 rows for exact cleanup-task
    configuration and grasp-collision diagnostics are parked as micro residual
    unless bundled with a larger runtime-diagnostics slice.

- [x] **M1: Split map bundle validation and snapshot contract checks.**
  - Target `roboclaws/maps/bundle.py` and
    `roboclaws/maps/actionable_snapshot.py`.
  - Turn `validate_nav2_map_bundle(...)` into an ordered validation pipeline
    for required files, YAML/PGM parsing, private-truth guards, semantic
    structure, waypoint reachability, fixture references, and route checks.
  - Keep `runtime_metric_map.json` and
    `actionable_semantic_map_snapshot.json` schemas stable.

- [x] **I1: Split Isaac Lab worker backend details after facade stabilization.**
  - Target `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` and focused
    helper modules under `scripts/isaac_lab_cleanup/`.
  - Extract camera capture, scene-index scenario generation, semantic-pose
    stage mutation, segmentation diagnostics, and fake/real runtime packaging
    into modules that keep Isaac imports inside the worker process.
  - Treat this as a post-facade backend-internal cleanup; do not change normal
    Roboclaws process imports or require real Isaac Lab for default verification.
  - Status after 2026-06-14 loop: the main robot-view camera capture pipeline,
    standalone scene-camera probe capture, worker CLI/command dispatch,
    capture-quality overrides, USD xform authoring, USD semantic-label helpers,
    support-surface union helpers, and semantic-pose robot-view rerender
    helpers are split into focused modules. The Isaac worker no longer has
    grouped complexity rows in the ratchet summary.

- [x] **R1: Continue reduce-entropy discovery after each completed group.**
  - Run the bounded high-noise summary and the quality-debt summary.
  - Add only candidates that pass the materiality contract: false confidence,
    live source drift, stale surface, real workflow friction, or recurring
    rediscovery.
  - Mark saturation instead of inventing lower-value cleanup.

## Current Candidate Packet

Discovery round: 2026-06-14 post-I1 Isaac camera-capture splits.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py` passes at 142 Ruff
  complexity violations and 59 oversized modules.
- `python scripts/dev/check_python_quality_ratchet.py --summary --top 30`
  shows the largest implementation hotspots are
  `roboclaws/household/report.py` (6930 lines, 0 complexity rows),
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635 lines, 0
  complexity rows),
  `roboclaws/household/scene_camera_comparison.py` (6796 lines, 8 rows),
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` (3701 lines, 7
  rows), `roboclaws/operator_console/launcher.py` plus
  `roboclaws/operator_console/server.py` (11 combined rows), and
  `roboclaws/household/visual_grounding.py` (6 rows).
- The already-shipped direct cleanup loop split removed
  `run_realworld_cleanup(...)` from the complexity baseline. Further direct
  cleanup shrinkage is parked unless tied to a new behavior-bearing slice.

Materiality gate:

- Candidate probe file: temporary `mktemp` JSON during discovery only.
- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: seven eligible candidates, no rejected candidates, no warnings.
- Requested group count was treated as a maximum, not a quota.

### Candidate 1: Isaac Worker Command/Runtime Family Split

Severity: P1

Entropy source: backend implementation depth and real workflow friction.

Materiality: `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` remains
large, but after the camera-capture, CLI/dispatch, capture-quality, USD xform,
semantic-label, support-surface, and semantic-pose robot-view splits, it no
longer has grouped complexity rows in the ratchet summary. Further worker
splitting is parked unless a new backend behavior slice makes it material.

Impact radius: workflow.

Maintainer test: backend fixes should not require rediscovering the worker's
command dispatch, delayed Isaac imports, USD mutation, render-setting mutation,
and state-writeback rules in one 8k-line file.

Affected paths:

- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`
- likely focused helpers under `scripts/isaac_lab_cleanup/`
- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend implementation details explicit and local.

Pattern hint: Command dispatch table plus adapter/module boundaries; keep Isaac
imports inside worker-owned helpers and preserve normal Roboclaws import safety.

Progress:

- 2026-06-14: parser construction moved to
  `scripts/isaac_lab_cleanup/isaac_worker_cli.py`; `main(...)` now uses one
  explicit state-command dispatch table. The `parse_args(...)` worker entrypoint
  remains stable for tests and callers. This removed the `parse_args` PLR0915
  row and the `main` C901/PLR0912 rows.
- 2026-06-14: capture-quality setting mutation, restoration, requested-setting
  row construction, and JSON-safe setting value normalization moved to
  `scripts/isaac_lab_cleanup/isaac_capture_quality.py`. The worker keeps its
  `_apply_isaac_capture_quality_overrides(...)` wrapper so existing hook and
  test seams stay stable. This removed the `_apply_isaac_capture_quality_overrides`
  C901/PLR0912 rows.
- 2026-06-14: USD translate op authoring moved to
  `scripts/isaac_lab_cleanup/isaac_usd_xform.py`. The worker imports
  `_set_usd_xform_translate` as the same private hook used by semantic-pose
  stage application tests. This removed the `_set_usd_xform_translate` C901 row.
- 2026-06-14: Scene-index semantic-label application moved to
  `scripts/isaac_lab_cleanup/isaac_semantic_labels.py`. The worker keeps
  `_apply_scene_index_semantic_labels(...)` as a stable wrapper and still passes
  the worker-local `_semantic_label_target_prims` hook so existing monkeypatch
  tests stay valid. This removed the `_apply_scene_index_semantic_labels` C901
  row.
- 2026-06-14: USD descendant support-surface union calculation moved to
  `scripts/isaac_lab_cleanup/isaac_support_surfaces.py`. The worker keeps
  `_usd_support_surface_union(...)` as a stable wrapper that binds the existing
  Isaac source constants. This removed the `_usd_support_surface_union` C901
  row.
- 2026-06-14: Semantic-pose robot-view rerender state handling moved to
  `scripts/isaac_lab_cleanup/isaac_semantic_pose_robot_view.py`. The worker
  keeps `_real_semantic_pose_robot_view_images(...)` as a stable wrapper that
  injects the monkeypatchable capture function, provenance helper, image
  completeness check, and state writeback hook. This removed the remaining
  `_real_semantic_pose_robot_view_images` C901 and PLR0915 rows.

Suggested proof:

- `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py <new helper files>`
- `ruff format --check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py <new helper files>`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for fake-worker slices; real Isaac rendering claims remain
local-simulator-sensitive and need explicit local proof when behavior changes.

### Candidate 2: Cleanup Report Section Extraction

Severity: P1

Entropy source: report review friction and recurring rediscovery.

Materiality: `roboclaws/household/report.py` is still 6930 lines after map,
timing, action-evidence, grasp-cache preflight, light proof-bundle runner, and
agent-view section extraction. It now has zero grouped complexity rows, while
proof selection/results, robot, Agibot, and SDK runner sections still share the
same namespace.

Impact radius: module.

Maintainer test: proof or robot evidence rendering should be reviewable by
section family instead of forcing reviewers through the shared HTML wrapper.

Affected paths:

- `roboclaws/household/report.py`
- likely `roboclaws/household/report_sections_proof.py`
- likely `roboclaws/household/report_sections_robot.py`
- likely `roboclaws/household/report_sections_agent.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`

Owner skill: `intuitive-refactor`

Zen hint: keep repeated report sections in modules that name the review
surface.

Pattern hint: simple section modules, continuing the existing map/timing
section pattern.

Suggested proof:

- `ruff check roboclaws/household/report.py roboclaws/household/report_sections_*.py tests/contract/reports/test_molmo_cleanup_report.py`
- `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_*.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe if rendered HTML assertions stay behavior-focused and no
visual redesign is attempted.

### Candidate 3: Scene-Camera Comparison Lane/Diagnostics Split

Severity: P1

Entropy source: backend visual-parity workflow friction.

Materiality: `roboclaws/household/scene_camera_comparison.py` is 6796 lines
with eight complexity rows. It mixes lane capture orchestration, canonical
camera-control manifests, MuJoCo/Isaac render-contract extraction, room-scale
diagnostics, source-code citation diagnostics, and HTML rendering.
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` imports
private render-contract helpers from it, so visual parity scripts are already
coupled through private functions.

Impact radius: workflow.

Maintainer test: backend visual-parity fixes should land in lane/diagnostic
helpers without changing the entire scene-camera report runner.

Affected paths:

- `roboclaws/household/scene_camera_comparison.py`
- likely focused scene-camera lane/report/diagnostic helper modules
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `tests/contract/molmo_cleanup/test_scene_camera_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: separate capture evidence from report presentation.

Pattern hint: pipeline modules for capture lanes and diagnostics; avoid adding a
framework around one-off report HTML.

Suggested proof:

- `ruff check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `ruff format --check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_scene_camera_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for render-only report splits; real render parity claims
remain local-renderer-sensitive.

### Candidate 4: OpenAI Agents Live Runtime Boundary

Severity: P1

Entropy source: live-agent runtime workflow friction.

Materiality: `roboclaws/agents/drivers/openai_agents_live.py` is 2774 lines
with SDK adapter complexity, while
`scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` is 3701 lines with
server lifecycle, visual backend slot locking, retry/continuation policy,
timing metrics, checker execution, and model observability metrics. The two
files share the live Agent SDK path but split responsibilities by historical
script boundary rather than one clear runtime contract.

Impact radius: workflow.

Maintainer test: provider/profile or retry changes should not require tracing
both SDK adapter setup and cleanup-runner lifecycle logic in oversized modules.

Affected paths:

- `roboclaws/agents/drivers/openai_agents_live.py`
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `tests/unit/agents/test_live_runtime.py`
- likely `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: make live-agent runtime boundaries explicit.

Pattern hint: adapter plus runner lifecycle modules; avoid hiding task-specific
cleanup behavior inside the generic SDK driver.

Suggested proof:

- `ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep live provider calls mocked; do not claim real
provider behavior without a local live-agent run.

### Candidate 5: Operator Console API Routing And Readiness Gates

Severity: P1

Entropy source: operator workflow false-confidence risk.

Materiality: `route_readiness(...)` has C901/PLR0912/PLR0915 rows
(`20 > 10`, `22 > 12`, `75 > 50`) and owns provider-key checks, Isaac
preflight state, MCP port checks, operator real-movement gates, lock state, and
attachable-run handling. `ConsoleRequestHandler.do_GET` and `do_POST` add five
more rows by routing many API endpoints through branch ladders.

Impact radius: workflow.

Maintainer test: console readiness should not mislead an operator because
route gates, env overrides, lock state, and HTTP handlers are hard to audit.

Affected paths:

- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/server.py`
- likely `roboclaws/operator_console/api_routes.py`
- likely `roboclaws/operator_console/readiness.py`
- `tests/unit/operator_console/test_launcher.py`
- `tests/unit/operator_console/test_state.py`

Owner skill: `intuitive-refactor`

Zen hint: make every operator gate name its own reason.

Pattern hint: command/router table for HTTP endpoints and a readiness gate
pipeline for launch blockers.

Suggested proof:

- `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py tests/unit/operator_console/test_launcher.py tests/unit/operator_console/test_state.py`
- `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Preserve existing API payload shapes; browser QA is
useful if frontend routing changes.

### Candidate 6: Visual-Grounding Contract Validation And Adapter Catalog

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active visual-grounding sidecar is detector-only, so request
and response validation are the trust boundary. `roboclaws/household/visual_grounding.py`
has six complexity rows around HTTP client retry/failure handling and
request/response validation, while `scripts/visual_grounding/adapters.py` owns
the fake/real adapter catalog and response routing in a 1793-line script.

Impact radius: workflow.

Maintainer test: malformed detector responses should fail through a small,
auditable validation surface rather than hidden branches in the HTTP client and
adapter script.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- likely `roboclaws/household/visual_grounding_contract.py`
- `scripts/visual_grounding/adapters.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: make the external sidecar contract explicit.

Pattern hint: contract validator module plus adapter registry; no broader
provider framework unless more real adapters are promoted.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for validation refactors if response schemas remain
stable; real detector model behavior is outside the default gate.

### Candidate 7: Robot-Camera Apple-To-Apple Parity Diagnostics

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality:
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` is 5844
lines with six complexity rows and imports private render-contract helpers from
`scene_camera_comparison.py`. The script combines object-gate classification,
material response probes, tone/color probes, USD PreviewSurface checks, report
rendering, and command orchestration.

Impact radius: workflow.

Maintainer test: parity investigations should not require rediscovering object,
material, tone/color, and report diagnostics in one render-only script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `roboclaws/household/scene_camera_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable without private imports.

Pattern hint: shared render-contract/diagnostic helper module; direct extraction
is clearer than a full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; run local renderer proof
only when claiming visual parity behavior changed.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Agent-Report Split

This loop rechecked the repo after the Agent View report extraction. It does
not supersede the earlier evidence; it records the current ordering for the
next selection.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 80`
  reports 142 Ruff complexity violations and 59 oversized modules.
- Largest current modules are
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635 lines, 0
  grouped rows), `roboclaws/household/report.py` (6930 lines, 0 rows),
  `roboclaws/household/scene_camera_comparison.py` (6796 lines, 8 rows),
  `roboclaws/household/realworld_contract.py` (6424 lines, 3 rows), and
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` (5844
  lines, 6 rows).
- The main backend facade is established, but live MCP server setup and the MCP
  smoke runner still duplicate backend construction instead of using
  `build_cleanup_backend_session(...)`.

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: seven eligible candidates, no rejected candidates.
- Gate warning: requested eight groups, but only seven candidates passed
  materiality; treat the count as a maximum, not a quota.
- Saturation check: another pass found only test-size debt, historical docs, or
  already planned specialized surfaces. No additional candidate was added.

### Current Candidate A: Live MCP Backend Facade Adoption

Severity: P1

Entropy source: backend facade live-source drift.

Materiality: direct cleanup now uses `build_cleanup_backend_session(...)` and
shared run-option validation, while `roboclaws/cli/household_agent_server.py`
and `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py` still build
MolmoSpaces / Isaac Lab / synthetic backend sessions inline and duplicate
private-target scenario fallback. Both are active through `just` recipes and
contract tests.

Impact radius: workflow.

Maintainer test: adding a backend option or capability should not require
updating direct cleanup, live MCP server setup, and MCP smoke setup separately.

Affected paths:

- `roboclaws/cli/household_agent_server.py`
- `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py`
- `roboclaws/household/backend_contract.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`

Owner skill: `intuitive-refactor`

Zen hint: make the one canonical backend construction path obvious.

Pattern hint: facade adoption; do not add another abstraction layer around
Agibot-specific contract setup.

Suggested proof:

- `ruff check roboclaws/cli/household_agent_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py roboclaws/household/backend_contract.py`
- `ruff format --check roboclaws/cli/household_agent_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py roboclaws/household/backend_contract.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe if CLI flags and artifact schemas stay stable. Do not
route Agibot GDK setup through the generic facade in this slice.

### Current Candidate B: Cleanup Report Section Extraction

Severity: P1

Entropy source: report review friction and recurring rediscovery.

Materiality: `roboclaws/household/report.py` is still 6930 lines after the map,
timing, action-evidence, grasp-cache, light proof-bundle, and agent-view splits.
Robot timeline and proof result families remain in the shared renderer even
though section modules are now the local pattern.

Impact radius: module.

Maintainer test: robot-view or proof-result rendering should be reviewable by
section family instead of forcing every change through the shared HTML wrapper.

Affected paths:

- `roboclaws/household/report.py`
- likely `roboclaws/household/report_sections_robot.py`
- likely `roboclaws/household/report_sections_proof.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`

Owner skill: `intuitive-refactor`

Zen hint: keep each report review surface in a module named after that surface.

Pattern hint: simple section modules, continuing the existing
`report_sections_*` pattern.

Suggested proof:

- `ruff check roboclaws/household/report.py roboclaws/household/report_sections_*.py tests/contract/reports/test_molmo_cleanup_report.py`
- `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_*.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe if this remains an extraction-only slice with no visual
redesign.

### Current Candidate C: Scene-Camera Comparison Pipeline Split

Severity: P1

Entropy source: backend visual-parity workflow friction.

Materiality: `roboclaws/household/scene_camera_comparison.py` is 6796 lines
with eight complexity rows. It mixes capture lane orchestration, render
contracts, diagnostics, source-code citation diagnostics, and HTML rendering.
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` already
imports private render-contract helpers from it.

Impact radius: workflow.

Maintainer test: backend visual-parity fixes should land in lane/diagnostic
helpers without changing the entire scene-camera report runner.

Affected paths:

- `roboclaws/household/scene_camera_comparison.py`
- likely focused scene-camera lane/report/diagnostic helper modules
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `tests/contract/molmo_cleanup/test_scene_camera_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: separate capture evidence from report presentation.

Pattern hint: small pipeline modules for capture lanes and diagnostics; avoid a
new framework.

Suggested proof:

- `ruff check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `ruff format --check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_scene_camera_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for extraction; real render parity claims remain
local-renderer-sensitive.

### Current Candidate D: OpenAI Agents Live Runtime Boundary

Severity: P1

Entropy source: live-agent runtime workflow friction.

Materiality: `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` is 3701
lines with server lifecycle, visual slot locking, retry/continuation policy,
checker execution, and model observability metrics. The SDK adapter in
`roboclaws/agents/drivers/openai_agents_live.py` is another 2774 lines. The
test suite imports many private metrics helpers from the runner, which signals
that runner-lifecycle and observability concerns are not yet local.

Impact radius: workflow.

Maintainer test: provider/profile, retry, or context-metric changes should not
require tracing both SDK adapter setup and cleanup-runner lifecycle logic.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- likely `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: make live-agent runtime boundaries explicit.

Pattern hint: adapter plus runner lifecycle modules; keep cleanup task behavior
out of the generic SDK driver.

Suggested proof:

- `ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate E: Operator Console API Routing And Readiness Gates

Severity: P1

Entropy source: operator workflow false-confidence risk.

Materiality: `route_readiness(...)` owns provider-key checks, evidence-lane
capability blockers, MCP port checks, Isaac/Agibot route gates, lock state, and
attachable-run handling while carrying C901 / PLR0912 / PLR0915 rows.
`ConsoleRequestHandler.do_GET` and `do_POST` add five more branch-ladder rows.

Impact radius: workflow.

Maintainer test: console readiness should not mislead an operator because
route gates, env overrides, lock state, and HTTP handlers are hard to audit.

Affected paths:

- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/server.py`
- likely `roboclaws/operator_console/readiness.py`
- likely `roboclaws/operator_console/api_routes.py`
- `tests/unit/operator_console/`

Owner skill: `intuitive-refactor`

Zen hint: make every operator gate name its own reason.

Pattern hint: readiness gate pipeline plus HTTP router table.

Suggested proof:

- `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py tests/unit/operator_console`
- `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Preserve API payload shapes; browser QA is useful if
frontend routing changes.

### Current Candidate F: Visual-Grounding Contract Validation And Adapter Catalog

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active sidecar is detector-only, so request/response
validation is the trust boundary. `roboclaws/household/visual_grounding.py`
has six complexity rows around validation and HTTP failure handling, while
`scripts/visual_grounding/adapters.py` owns fake/real adapter routing in a
1793-line script.

Impact radius: workflow.

Maintainer test: malformed detector responses should fail through a small,
auditable validation surface rather than hidden branches in the HTTP client and
adapter script.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- likely `roboclaws/household/visual_grounding_contract.py`
- `scripts/visual_grounding/adapters.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: make the external sidecar contract explicit.

Pattern hint: contract validator module plus adapter registry.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving validation refactors. Real detector
model behavior is outside the default gate.

### Current Candidate G: Robot-Camera Apple-To-Apple Parity Diagnostics

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality: `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
is 5844 lines with six complexity rows and imports private render-contract
helpers from `scene_camera_comparison.py`. It combines object-gate
classification, material response probes, tone/color probes, USD
PreviewSurface checks, report rendering, and command orchestration.

Impact radius: workflow.

Maintainer test: parity investigations should not require rediscovering object,
material, tone/color, camera, and report diagnostics in one render-only script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `roboclaws/household/scene_camera_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable without private imports.

Pattern hint: shared render-contract/diagnostic helper module; direct
extraction is clearer than a full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; run local renderer proof
only when claiming visual parity behavior changed.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Robot-Report Split

This loop rechecked the repo after the Robot View Timeline extraction and B7
backend-facade adoption. It supersedes the old "Post-Agent-Report Split"
ordering for current next-work selection; the old section remains as historical
evidence.

After the subsequent proof-section extraction, C3 is closed. The next active
ordering is in "Post-Proof-Report Split" below.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 30`
  reports 142 Ruff complexity violations and 59 oversized modules.
- Largest current implementation hotspots are
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635 lines, 0
  grouped rows), `roboclaws/household/scene_camera_comparison.py` (6796 lines,
  8 rows), `roboclaws/household/report.py` (6558 lines, 0 rows),
  `roboclaws/household/realworld_contract.py` (6424 lines, 3 rows), and
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` (5844
  lines, 6 rows).
- B7 removed the duplicated live MCP backend-construction path, so the old
  "Live MCP Backend Facade Adoption" current candidate is now complete.
- `report.py` remains oversized but has zero grouped complexity rows. The only
  material C3 continuation is proof request/result extraction; further generic
  report splitting is parked unless tied to a named report family.

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: six eligible candidates, no rejected candidates, no warnings.
- Saturation check: the loop has not saturated yet because P1 workflow
  friction remains in scene-camera comparison, live OpenAI Agents runtime, and
  operator-console readiness/routing. Test-only oversized modules and
  historical planning surfaces remain parked.

### Current Candidate A: Cleanup Report Proof Result Section Extraction

Severity: P1

Entropy source: report review friction and recurring rediscovery.

Materiality: `roboclaws/household/report.py` is still 6558 lines after map,
timing, action-evidence, grasp-cache, light proof-bundle, agent-view, and robot
section extraction. Proof request/result rendering remains in the shared
wrapper even though section modules are now the local pattern.

Impact radius: module.

Maintainer test: planner-proof request/result rendering should be reviewable by
proof section family instead of forcing changes through the shared HTML
wrapper.

Affected paths:

- `roboclaws/household/report.py`
- likely `roboclaws/household/report_sections_proof.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`

Owner skill: `intuitive-refactor`

Zen hint: keep each report review surface in a module named after that surface.

Pattern hint: simple section module; continue the existing
`report_sections_*` pattern.

Suggested proof:

- `ruff check roboclaws/household/report.py roboclaws/household/report_sections_proof.py tests/contract/reports/test_molmo_cleanup_report.py`
- `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_proof.py`
- `python -m py_compile roboclaws/household/report.py roboclaws/household/report_sections_proof.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe if extraction-only and no report visual redesign is
attempted.

### Current Candidate B: Scene-Camera Comparison Pipeline Split

Severity: P1

Entropy source: backend visual-parity workflow friction.

Materiality: `roboclaws/household/scene_camera_comparison.py` is 6796 lines
with eight complexity rows. It mixes capture lane orchestration, render
contracts, diagnostics, source-code citation diagnostics, and HTML rendering.
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` already
imports private render-contract helpers from it.

Impact radius: workflow.

Maintainer test: backend visual-parity fixes should land in lane/diagnostic
helpers without changing the entire scene-camera report runner.

Affected paths:

- `roboclaws/household/scene_camera_comparison.py`
- likely focused scene-camera lane/report/diagnostic helper modules
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `tests/contract/molmo_cleanup/test_scene_camera_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: separate capture evidence from report presentation.

Pattern hint: small pipeline modules for capture lanes and diagnostics; avoid a
new framework.

Suggested proof:

- `ruff check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `ruff format --check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_scene_camera_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for extraction; real render parity claims remain
local-renderer-sensitive.

### Current Candidate C: OpenAI Agents Live Runtime Boundary

Severity: P1

Entropy source: live-agent runtime workflow friction.

Materiality: `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` is 3701
lines with seven grouped complexity rows around server lifecycle, visual slot
locking, retry/continuation policy, checker execution, and model observability
metrics. `roboclaws/agents/drivers/openai_agents_live.py` is another 2774 lines
with three grouped complexity rows.

Impact radius: workflow.

Maintainer test: provider/profile, retry, or context-metric changes should not
require tracing both SDK adapter setup and cleanup-runner lifecycle logic.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- likely `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: make live-agent runtime boundaries explicit.

Pattern hint: adapter plus runner lifecycle modules; keep cleanup task behavior
out of the generic SDK driver.

Suggested proof:

- `ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate D: Operator Console API Routing And Readiness Gates

Severity: P1

Entropy source: operator workflow false-confidence risk.

Materiality: `roboclaws/operator_console/launcher.py` has six grouped
complexity rows including `route_readiness(...)` at 75 > 50, and
`roboclaws/operator_console/server.py` has five grouped rows across HTTP
handlers. These paths own provider-key checks, evidence-lane blockers, MCP port
checks, route gates, lock state, and attachable-run handling.

Impact radius: workflow.

Maintainer test: console readiness should not mislead operators because route
gates, env overrides, lock state, and HTTP handlers are hard to audit.

Affected paths:

- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/server.py`
- likely `roboclaws/operator_console/readiness.py`
- likely `roboclaws/operator_console/api_routes.py`
- `tests/unit/operator_console/`

Owner skill: `intuitive-refactor`

Zen hint: make every operator gate name its own reason.

Pattern hint: readiness gate pipeline plus HTTP router table.

Suggested proof:

- `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py tests/unit/operator_console`
- `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Preserve API payload shapes; browser QA is useful if
frontend routing changes.

### Current Candidate E: Visual-Grounding Contract Validation And Adapter Catalog

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active sidecar is detector-only, so request/response
validation is the trust boundary. `roboclaws/household/visual_grounding.py`
has six grouped complexity rows around validation and HTTP failure handling,
while `scripts/visual_grounding/adapters.py` owns fake/real adapter routing in
a 1793-line script.

Impact radius: workflow.

Maintainer test: malformed detector responses should fail through a small,
auditable validation surface rather than hidden branches in the HTTP client and
adapter script.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- likely `roboclaws/household/visual_grounding_contract.py`
- `scripts/visual_grounding/adapters.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: make the external sidecar contract explicit.

Pattern hint: contract validator module plus adapter registry.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving validation refactors. Real detector
model behavior is outside the default gate.

### Current Candidate F: Robot-Camera Apple-To-Apple Parity Diagnostics

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality: `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
is 5844 lines with six grouped complexity rows and imports private
render-contract helpers from `scene_camera_comparison.py`. It combines
object-gate classification, material response probes, tone/color probes, USD
PreviewSurface checks, report rendering, and command orchestration.

Impact radius: workflow.

Maintainer test: parity investigations should not require rediscovering object,
material, tone/color, camera, and report diagnostics in one render-only script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `roboclaws/household/scene_camera_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable without private imports.

Pattern hint: shared render-contract/diagnostic helper module; direct
extraction is clearer than a full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; run local renderer proof
only when claiming visual parity behavior changed.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Proof-Report Split

This loop rechecked the repo after closing C3. It is the current candidate
ordering for continuing the reduce-entropy run.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 20`
  reports 142 Ruff complexity violations and 59 oversized modules.
- Largest current implementation hotspots are
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635 lines, 0
  grouped rows), `roboclaws/household/scene_camera_comparison.py` (6796 lines,
  8 rows), `roboclaws/household/realworld_contract.py` (6424 lines, 3 rows),
  `roboclaws/household/report.py` (6195 lines, 0 rows), and
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` (5844
  lines, 6 rows).
- Report-section cleanup is complete for the currently material cleanup-report
  families. Further report extraction is parked unless a named planner-probe or
  proof-bundle result family becomes the selected target.

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: five eligible candidates, no rejected candidates, no warnings.
- Saturation check: the loop has not saturated because P1 workflow friction
  remains in scene-camera comparison, live OpenAI Agents runtime, and operator
  console readiness/routing.

### Current Candidate A: Scene-Camera Comparison Pipeline Split

Severity: P1

Entropy source: backend visual-parity workflow friction.

Materiality: `roboclaws/household/scene_camera_comparison.py` is 6796 lines
with eight complexity rows. It mixes capture lane orchestration, render
contracts, diagnostics, source-code citation diagnostics, and HTML rendering.
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` already
imports private render-contract helpers from it.

Impact radius: workflow.

Maintainer test: backend visual-parity fixes should land in lane/diagnostic
helpers without changing the entire scene-camera report runner.

Affected paths:

- `roboclaws/household/scene_camera_comparison.py`
- likely focused scene-camera lane/report/diagnostic helper modules
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `tests/contract/molmo_cleanup/test_scene_camera_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: separate capture evidence from report presentation.

Pattern hint: small pipeline modules for capture lanes and diagnostics; avoid a
new framework.

Suggested proof:

- `ruff check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `ruff format --check roboclaws/household/scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_scene_camera_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for extraction; real render parity claims remain
local-renderer-sensitive.

### Current Candidate B: OpenAI Agents Live Runtime Boundary

Severity: P1

Entropy source: live-agent runtime workflow friction.

Materiality: `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` is 3701
lines with seven grouped complexity rows around server lifecycle, visual slot
locking, retry/continuation policy, checker execution, and model observability
metrics. `roboclaws/agents/drivers/openai_agents_live.py` is another 2774 lines
with three grouped complexity rows.

Impact radius: workflow.

Maintainer test: provider/profile, retry, or context-metric changes should not
require tracing both SDK adapter setup and cleanup-runner lifecycle logic.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- likely `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: make live-agent runtime boundaries explicit.

Pattern hint: adapter plus runner lifecycle modules; keep cleanup task behavior
out of the generic SDK driver.

Suggested proof:

- `ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate C: Operator Console API Routing And Readiness Gates

Severity: P1

Entropy source: operator workflow false-confidence risk.

Materiality: `roboclaws/operator_console/launcher.py` has six grouped
complexity rows including `route_readiness(...)` at 75 > 50, and
`roboclaws/operator_console/server.py` has five grouped rows across HTTP
handlers. These paths own provider-key checks, evidence-lane blockers, MCP port
checks, route gates, lock state, and attachable-run handling.

Impact radius: workflow.

Maintainer test: console readiness should not mislead operators because route
gates, env overrides, lock state, and HTTP handlers are hard to audit.

Affected paths:

- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/server.py`
- likely `roboclaws/operator_console/readiness.py`
- likely `roboclaws/operator_console/api_routes.py`
- `tests/unit/operator_console/`

Owner skill: `intuitive-refactor`

Zen hint: make every operator gate name its own reason.

Pattern hint: readiness gate pipeline plus HTTP router table.

Suggested proof:

- `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py tests/unit/operator_console`
- `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Preserve API payload shapes; browser QA is useful if
frontend routing changes.

### Current Candidate D: Visual-Grounding Contract Validation And Adapter Catalog

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active sidecar is detector-only, so request/response
validation is the trust boundary. `roboclaws/household/visual_grounding.py`
has six grouped complexity rows around validation and HTTP failure handling,
while `scripts/visual_grounding/adapters.py` owns fake/real adapter routing in
a 1793-line script.

Impact radius: workflow.

Maintainer test: malformed detector responses should fail through a small,
auditable validation surface rather than hidden branches in the HTTP client and
adapter script.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- likely `roboclaws/household/visual_grounding_contract.py`
- `scripts/visual_grounding/adapters.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: make the external sidecar contract explicit.

Pattern hint: contract validator module plus adapter registry.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving validation refactors. Real detector
model behavior is outside the default gate.

### Current Candidate E: Robot-Camera Apple-To-Apple Parity Diagnostics

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality: `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
is 5844 lines with six grouped complexity rows and imports private
render-contract helpers from `scene_camera_comparison.py`. It combines
object-gate classification, material response probes, tone/color probes, USD
PreviewSurface checks, report rendering, and command orchestration.

Impact radius: workflow.

Maintainer test: parity investigations should not require rediscovering object,
material, tone/color, camera, and report diagnostics in one render-only script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `roboclaws/household/scene_camera_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable without private imports.

Pattern hint: shared render-contract/diagnostic helper module; direct
extraction is clearer than a full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; run local renderer proof
only when claiming visual parity behavior changed.

## Parked Cross-Seam / Future Ideas

- Scene-camera report manifest hydration is complete. The remaining
  scene-camera work is narrower render-contract / source-diagnostics cleanup,
  not a reason to keep reopening the already extracted report hydration path.
- Test-only oversized modules are real ratchet debt, but broad test-suite
  fixture/layout cleanup belongs to `intuitive-tests` unless a selected code
  slice needs a targeted helper extraction.
- `roboclaws/household/realworld_contract.py` still has three small complexity
  rows after C2/C2.5. Park them until map/candidate behavior work gives a
  material parent slice.
- `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py` has three rows around
  `score_variant(...)`; bundle it with visual-grounding contract work only if
  detector-sidecar scoring behavior is being touched.
- The remaining planner manipulation probe rows are micro residual:
  `_configure_exact_cleanup_task` C901 11 and
  `_install_grasp_collision_diagnostics` C901 11. Do not count them as a
  standalone loop group unless bundled with a larger runtime-diagnostics slice.
- Human docs cleanup is outside this plan unless public command or backend
  contract text changes. Route broad docs work to `intuitive-doc`.
- Real Isaac Lab simulator validation remains local/environment-sensitive.
  This plan can use fake Isaac worker tests by default and should record real
  simulator gates as skipped unless explicitly authorized.
- Agibot GDK backend parity can reuse the facade later, but this plan should
  first stabilize the current synthetic, MolmoSpaces, and Isaac Lab cleanup
  path.
- OpenAI Agents SDK runner cleanup and `run_live_openai_agents_cleanup.py`
  complexity are material but already covered by
  `docs/plans/2026-06-12-open-ended-household-default-architecture.md`,
  `docs/plans/refactor-coding-agent-provider-registry.md`, and the report
  performance plan. Do not duplicate it here unless a future loop finds
  SDK-specific drift outside those plans.
- Operator-console readiness/state splitting is material but already covered by
  `docs/plans/operator-console-orthogonal-launch-refactor.md` plus the recent
  legacy-route-wrapper removal. Do not count it again unless new route-gate
  drift appears.
- Scene-camera/render-parity, visual-grounding sidecar/benchmark, Agibot
  rehearsal/pilot, raw-FPV probe, and apple2apple comparison surfaces remain
  large and live, but current evidence points to their existing specialized
  plans rather than this backend-quality batch.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Scene-Camera Render Split

This loop rechecked the repo after the scene-camera report manifest hydration
and render-diagnostics slices. It is the current candidate ordering for
continuing the reduce-entropy run.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 30`
  reports 134 Ruff complexity violations and 59 oversized modules.
- `roboclaws/household/scene_camera_comparison.py` dropped from 6796 to 6480
  lines across the two scene-camera slices and no longer appears in the
  complexity-by-file summary. The removed rows cover
  `render_scene_camera_comparison_report`, `run_scene_camera_comparison`,
  `_room_scale_contract_from_capture`, `_view_usd_prim_path`,
  `_mujoco_render_contract_from_xml`, and `_render_source_snippet`.
- `scripts/dev/python_quality_baseline.json` was deliberately refreshed after
  targeted checks passed. The current baseline records 134 Ruff complexity
  violations and 59 oversized modules.
- Largest current implementation hotspots are
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635 lines, 0
  grouped rows), `roboclaws/household/scene_camera_comparison.py` (6480 lines,
  0 rows), `roboclaws/household/realworld_contract.py` (6424 lines, 3 rows),
  `roboclaws/household/report.py` (6195 lines, 0 rows), and
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` (5844
  lines, 6 rows).

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: four eligible candidates, no rejected candidates, no warnings.
- Saturation check: the loop has not saturated. P1 workflow friction remains
  in live OpenAI Agents runtime and operator console readiness/routing.
  Visual-grounding contract validation and apple2apple parity diagnostics remain
  material P2 directions.

### Current Candidate A: OpenAI Agents Live Runtime Boundary

Severity: P1

Entropy source: live-agent runtime workflow friction.

Materiality: `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` is 3701
lines with seven grouped complexity rows around server lifecycle, visual slot
locking, retry/continuation policy, checker execution, and model observability
metrics. `roboclaws/agents/drivers/openai_agents_live.py` is another 2774 lines
with three grouped complexity rows.

Impact radius: workflow.

Maintainer test: provider/profile, retry, or context-metric changes should not
require tracing both SDK adapter setup and cleanup-runner lifecycle logic.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- likely `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: make live-agent runtime boundaries explicit.

Pattern hint: adapter plus runner lifecycle modules; keep cleanup task behavior
out of the generic SDK driver.

Suggested proof:

- `ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate B: Operator Console API Routing And Readiness Gates

Severity: P1

Entropy source: operator workflow false-confidence risk.

Materiality: `roboclaws/operator_console/launcher.py` has six grouped
complexity rows including `route_readiness(...)` at 75 > 50, and
`roboclaws/operator_console/server.py` has five grouped rows across HTTP
handlers. These paths own provider-key checks, evidence-lane blockers, MCP port
checks, route gates, lock state, and attachable-run handling.

Impact radius: workflow.

Maintainer test: console readiness should not mislead operators because route
gates, env overrides, lock state, and HTTP handlers are hard to audit.

Affected paths:

- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/server.py`
- likely `roboclaws/operator_console/readiness.py`
- likely `roboclaws/operator_console/api_routes.py`
- `tests/unit/operator_console/`

Owner skill: `intuitive-refactor`

Zen hint: make every operator gate name its own reason.

Pattern hint: readiness gate pipeline plus HTTP router table.

Suggested proof:

- `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py tests/unit/operator_console`
- `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Preserve API payload shapes; browser QA is useful if
frontend routing changes.

### Current Candidate C: Visual-Grounding Contract Validation And Adapter Catalog

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active sidecar is detector-only, so request/response
validation is the trust boundary. `roboclaws/household/visual_grounding.py`
has six grouped complexity rows around validation and HTTP failure handling,
while `scripts/visual_grounding/adapters.py` owns fake/real adapter routing in
a 1793-line script.

Impact radius: workflow.

Maintainer test: malformed detector responses should fail through a small,
auditable validation surface rather than hidden branches in the HTTP client and
adapter script.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- likely `roboclaws/household/visual_grounding_contract.py`
- `scripts/visual_grounding/adapters.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: make the external sidecar contract explicit.

Pattern hint: contract validator module plus adapter registry.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving validation refactors. Real detector
model behavior is outside the default gate.

### Current Candidate D: Robot-Camera Apple-To-Apple Parity Diagnostics

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality: `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
is 5844 lines with six grouped complexity rows and imports private
render-contract helpers from `scene_camera_comparison.py`. It combines
object-gate classification, material response probes, tone/color probes, USD
PreviewSurface checks, report rendering, and command orchestration.

Impact radius: workflow.

Maintainer test: parity investigations should not require rediscovering object,
material, tone/color, camera, and report diagnostics in one render-only script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `roboclaws/household/scene_camera_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable without private imports.

Pattern hint: shared render-contract/diagnostic helper module; direct
extraction is clearer than a full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; run local renderer proof
only when claiming visual parity behavior changed.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-OpenAI Metrics Split

This loop rechecked the repo after the OpenAI Agents metrics aggregation
extraction. It is the current candidate ordering for continuing the
reduce-entropy run.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 40`
  reports 129 Ruff complexity violations and 59 oversized modules.
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` dropped from 3701
  to 3297 lines and now has two grouped complexity rows after the metrics
  extraction.
- The remaining largest implementation hotspots with current grouped
  complexity are `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
  (5844 lines, 6 rows), `roboclaws/operator_console/launcher.py` (1113 lines,
  6 rows), `roboclaws/household/visual_grounding.py` (6 rows),
  `roboclaws/operator_console/server.py` (5 rows), and
  `roboclaws/agents/drivers/openai_agents_live.py` (2774 lines, 3 rows).

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: four eligible candidates, no rejected candidates, no warnings.
- Saturation check: the loop has not saturated. P1 workflow friction remains in
  operator-console readiness/routing. The remaining visual-grounding,
  apple2apple, and OpenAI Agents residual lifecycle directions are material P2
  candidates and should be selected only as bounded follow-up slices.

### Current Candidate A: Operator Console API Routing And Readiness Gates

Severity: P1

Entropy source: operator workflow false-confidence risk.

Materiality: `roboclaws/operator_console/launcher.py` has six grouped
complexity rows, including `route_readiness(...)` at 75 > 50 and 22 > 12.
`roboclaws/operator_console/server.py` has five grouped rows across HTTP
handlers. These paths own provider-key checks, evidence-lane blockers, MCP port
checks, route gates, lock state, attachable-run handling, and API routing.

Impact radius: workflow.

Maintainer test: console readiness should not mislead operators because route
gates, env overrides, lock state, and HTTP handlers are hard to audit.

Affected paths:

- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/server.py`
- likely `roboclaws/operator_console/readiness.py`
- likely `roboclaws/operator_console/api_routes.py`
- `tests/unit/operator_console/`

Owner skill: `intuitive-refactor`

Zen hint: make every operator gate name its own reason.

Pattern hint: readiness gate pipeline plus HTTP router table.

Suggested proof:

- `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py tests/unit/operator_console`
- `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/server.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Preserve API payload shapes; browser QA is useful if
frontend routing changes.

### Current Candidate B: Visual-Grounding Contract Validation And Adapter Catalog

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active sidecar is detector-only, so request/response
validation is the trust boundary. `roboclaws/household/visual_grounding.py`
has six grouped complexity rows around validation and HTTP failure handling,
while `scripts/visual_grounding/adapters.py` owns fake/real adapter routing in
a 1793-line script.

Impact radius: workflow.

Maintainer test: malformed detector responses should fail through a small,
auditable validation surface rather than hidden branches in the HTTP client and
adapter script.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- likely `roboclaws/household/visual_grounding_contract.py`
- `scripts/visual_grounding/adapters.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: make the external sidecar contract explicit.

Pattern hint: contract validator module plus adapter registry.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving validation refactors. Real detector
model behavior is outside the default gate.

### Current Candidate C: Robot-Camera Apple-To-Apple Parity Diagnostics

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality: `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
is 5844 lines with six grouped complexity rows and imports private
render-contract helpers from `scene_camera_comparison.py`. It combines
object-gate classification, material response probes, tone/color probes, USD
PreviewSurface checks, report rendering, and command orchestration.

Impact radius: workflow.

Maintainer test: parity investigations should not require rediscovering object,
material, tone/color, camera, and report diagnostics in one render-only script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `roboclaws/household/scene_camera_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable without private imports.

Pattern hint: shared render-contract/diagnostic helper module; direct
extraction is clearer than a full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py roboclaws/household/scene_camera_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; run local renderer proof
only when claiming visual parity behavior changed.

### Current Candidate D: OpenAI Agents Residual Lifecycle And Budget Policy

Severity: P2

Entropy source: live-agent runtime workflow friction.

Materiality: after the metrics extraction,
`scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` still has two grouped
C901 rows in `_run_sdk_agent` and `_raw_fpv_budget_failure`, and
`roboclaws/agents/drivers/openai_agents_live.py` still has three grouped rows.
The metrics aggregation slice is complete, so any next OpenAI Agents cleanup
should be a narrower lifecycle or raw-FPV budget-policy slice, not another
metrics move.

Impact radius: workflow.

Maintainer test: the remaining runner lifecycle and raw-FPV budget policy rows
should be split only if the next provider/profile change still requires editing
the large runner.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: keep live-agent lifecycle state and task-specific budget policy
separate from metrics aggregation.

Pattern hint: small lifecycle/budget helper extraction; avoid a broader SDK
driver rewrite unless provider behavior is being changed.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `ruff format --check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Backend/Console Saturation

This loop rechecked the repo after the visual-grounding contract split, live
MCP agent-server setup split, operator-console launch-support split, and
operator-console state-summary split. It is the saturation checkpoint for this
backend-quality batch.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 60`
  reports 106 Ruff complexity violations and 59 oversized modules.
- The current loop lowered the explicit Ruff baseline from 121 to 106 across
  the final visual-grounding, agent-server, and operator-console slices.
- `roboclaws/cli/household_agent_server.py`,
  `roboclaws/operator_console/server.py`,
  `roboclaws/operator_console/launcher.py`, and
  `roboclaws/operator_console/state.py` no longer appear in the
  complexity-by-file summary.
- The remaining largest implementation hotspots with grouped complexity are
  specialized surfaces: robot-camera apple-to-apple parity, visual-parity
  summary, Agibot rehearsal/proof fallback, RAW-FPV probe scoring, visual
  grounding adapter/benchmark scoring, and residual OpenAI Agents lifecycle.
- The high-noise summary did not show new live doc/source-of-truth drift in
  `.planning`, `docs/plans`, generated output, tests, or profile surfaces.

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: six P2 candidates passed materiality; no candidates were
  rejected.
- Gate warning: requested eight groups, but only six candidates passed
  materiality. Treat the requested count as a maximum, not a quota.
- Saturation check: no new P0/P1 backend-quality or operator-console
  consistency candidate remains. The backend/server/operator-console mainline
  is parked; continuing from here should select a specialized P2 packet rather
  than keep this batch open.

### Current Candidate A: Robot-Camera Parity Diagnostics

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality: `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
is 5844 lines with six grouped complexity rows, and
`scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py` is 3381 lines
with five grouped rows. Current visual-parity plans and tests still use these
scripts as live renderer gates.

Impact radius: workflow.

Maintainer test: parity investigations should not require rediscovering object
gates, material probes, tone/color gates, summary gates, and report assembly
across two oversized scripts before reviewing a renderer fix.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable without private-report
rediscovery.

Pattern hint: direct diagnostic-helper extraction; avoid a full parity
framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; run local renderer proof
only when claiming visual parity behavior changed.

### Current Candidate B: Visual-Grounding Adapter And Benchmark Scoring

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active visual-grounding sidecar is detector-only, so adapter
response parsing and benchmark scoring are promotion boundaries.
`scripts/visual_grounding/adapters.py::_yolo_candidates_from_model(...)` still
has a C901 row, and
`scripts/visual_grounding/run_visual_grounding_benchmark.py::_score_predictions(...)`
has a PLR0915 row after the shared schema validation moved into
`roboclaws/household/visual_grounding_contract.py`.

Impact radius: workflow.

Maintainer test: detector benchmark promotion should fail through auditable
adapter and scoring helpers instead of hiding YOLO response parsing and
aggregate scoring in oversized scripts.

Affected paths:

- `scripts/visual_grounding/adapters.py`
- `scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `roboclaws/household/visual_grounding.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: keep the external detector trust boundary explicit.

Pattern hint: adapter parser plus scoring pipeline helpers; no broader provider
framework.

Suggested proof:

- `ruff check scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py roboclaws/household/visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving parser/scoring extraction. Real
detector-model behavior remains outside the default gate.

### Current Candidate C: OpenAI Agents Residual Lifecycle And Budget Policy

Severity: P2

Entropy source: live-agent runtime workflow friction.

Materiality: after metrics aggregation moved to
`scripts/molmo_cleanup/openai_agents_metrics.py`,
`scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` still has
`_run_sdk_agent(...)` and `_raw_fpv_budget_failure(...)` C901 rows, while
`roboclaws/agents/drivers/openai_agents_live.py` still has rows for SDK run
setup, camera-grounded history extraction, and MCP text-content unwrapping.

Impact radius: workflow.

Maintainer test: provider/profile or raw-FPV budget changes should not require
tracing runner lifecycle, SDK adapter payload unwrapping, and camera-grounded
history handling across two large live-agent modules.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: keep live-agent lifecycle state and task-specific budget policy
separate from metrics aggregation.

Pattern hint: small lifecycle/budget helper extraction; avoid a broader SDK
driver rewrite unless provider behavior is being changed.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `ruff format --check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate D: RAW-FPV Perception Probe Scoring

Severity: P2

Entropy source: camera-evidence false-confidence risk.

Materiality: `camera-raw-fpv` remains a public evidence lane, and
`scripts/molmo_cleanup/run_raw_fpv_perception_probe.py::score_variant(...)`
still carries C901, PLR0912, and PLR0915 rows. That scorer mixes variant
metrics, evidence quality, and gate status decisions.

Impact radius: workflow.

Maintainer test: RAW-FPV probe scoring should not publish a pass/fail summary
from one branch-heavy scorer that mixes variant metrics, evidence quality, and
gate status decisions.

Affected paths:

- `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py`
- `tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`

Owner skill: `intuitive-refactor`

Zen hint: make camera-evidence gates explicit and reviewable.

Pattern hint: scoring-stage helpers; direct extraction is clearer than a new
probe framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `ruff format --check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for scoring extraction; live camera/provider claims need a
separate local run.

### Current Candidate E: Agibot Rehearsal And Planner-Proof Fallbacks

Severity: P2

Entropy source: Agibot/backend proof workflow rediscovery.

Materiality: `roboclaws/household/agibot_contract_rehearsal.py` still has four
grouped rows, including
`run_molmospaces_agibot_contract_rehearsal(...)` at PLR0915 96 > 50.
`roboclaws/household/planner_proof_requests.py` has four grouped rows around
prior fallback and alias selection. Agibot map-build, physical pilot, and
planner-proof routes remain live through current docs/tests.

Impact radius: workflow.

Maintainer test: Agibot map/rehearsal and planner-proof fallback changes
should not force reviewers through long mixed orchestration functions before
they can verify backend-specific blocked-capability evidence.

Affected paths:

- `roboclaws/household/agibot_contract_rehearsal.py`
- `roboclaws/household/planner_proof_requests.py`
- `tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py`
- `tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py`

Owner skill: `intuitive-refactor`

Zen hint: keep backend rehearsal evidence and proof fallback selection
separate.

Pattern hint: stage helper extraction for rehearsal orchestration and fallback
candidate filters.

Suggested proof:

- `ruff check roboclaws/household/agibot_contract_rehearsal.py roboclaws/household/planner_proof_requests.py tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py`
- `ruff format --check roboclaws/household/agibot_contract_rehearsal.py roboclaws/household/planner_proof_requests.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Real Agibot GDK behavior remains local/backend-gated;
default proof should stay on mock/contract tests.

### Current Candidate F: Behavior-Test Fixture Decomposition

Severity: P2

Entropy source: test-suite recurring rediscovery.

Materiality: the top oversized tests are now larger than many implementation
modules: `tests/unit/molmo_cleanup/test_isaac_lab_backend.py` is 4707 lines
with six grouped rows, `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
is 4671 lines, `tests/unit/agents/test_live_runtime.py` is 4570 lines with two
grouped rows, and `tests/contract/reports/test_molmo_cleanup_report.py` is
3369 lines with three top PLR0915 rows.

Impact radius: workflow.

Maintainer test: behavior changes should not require re-reading
multi-thousand-line tests just to identify fixture setup, exercised behavior,
and asserted contract fields.

Affected paths:

- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`

Owner skill: `intuitive-tests`

Zen hint: make tests tell one behavior story per fixture family.

Pattern hint: fixture/factory extraction and behavior-grouped test modules;
avoid splitting tests only to satisfy line-count aesthetics.

Suggested proof:

- `./scripts/dev/run_pytest_standalone.sh <selected test file> -q`
- `ruff check <selected test file and helper modules>`
- `ruff format --check <selected test file and helper modules>`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Route through `intuitive-tests`; prune or split only
when behavior grouping remains obvious.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Robot-Camera Summary Gates

This loop rechecked the repo after the robot-camera visual-parity summary-gate
extraction lowered the quality ratchet to 101 Ruff complexity violations. It
supersedes the "Post-Backend/Console Saturation" packet for current selection.
The previous packet remains historical evidence for why backend/server/report
mainline slices are complete.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py` passes at 101 Ruff
  complexity violations and 59 oversized modules.
- `python scripts/dev/check_python_quality_ratchet.py --summary --top 25`
  shows the current largest implementation hotspots are
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635 lines, 0
  grouped rows), `roboclaws/household/scene_camera_comparison.py` (6480 lines,
  0 grouped rows), `roboclaws/household/realworld_contract.py` (6424 lines, 3
  grouped rows), `roboclaws/household/report.py` (6195 lines, 0 grouped rows),
  and `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` (5844
  lines, 6 grouped rows).
- The fresh backend abstraction probe found that Python cleanup backend facade
  adoption is real, but command-layer backend semantics still repeat across
  `roboclaws/launch/backends.py`, `roboclaws/household/backend_contract.py`,
  `just/agent.just`, and `just/molmo.just`.
- The fresh agent-guidance probe found a live doc/tool drift:
  `AGENTS.md` and `CLAUDE.md` still point to `hybrid-phase-pipeline`, while
  the installed local skill set exposes `intuitive-flow` and no
  `hybrid-phase-pipeline` skill.

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: eight candidates accepted, no candidates rejected, no warnings.
- Saturation check: a second high-noise/docs/tests/legacy scan found no
  additional P0/P1 or materially useful P2 candidate beyond the packet below.
  Historical plans, generated output, and most legacy references are either
  already guarded or too speculative to count as new cleanup groups.

### Current Candidate A: Finish Current Robot-Camera Summary-Gate Extraction

Severity: P1

Entropy source: current workspace truth drift.

Materiality: this slice is implemented but not yet committed. The plan and
quality baseline now describe a lowered ratchet, while the helper module is
still untracked and the working tree also contains unrelated research-doc
changes that must not be mixed into the refactor commit.

Impact radius: workflow.

Maintainer test: leaving this slice half-landed makes the next agent
rediscover already-finished visual-parity gate work and risks committing
unrelated research files with the refactor.

Affected paths:

- `docs/plans/refactor-python-quality-backend-entropy.md`
- `scripts/dev/python_quality_baseline.json`
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `scripts/molmo_cleanup/robot_camera_visual_parity_gates.py`

Owner skill: `intuitive-refactor`

Zen hint: make the repository state obvious before starting the next slice.

Pattern hint: no new pattern; close the already-extracted helper boundary.

Suggested proof:

- `ruff check scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py scripts/molmo_cleanup/robot_camera_visual_parity_gates.py tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py`
- `ruff format --check scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py scripts/molmo_cleanup/robot_camera_visual_parity_gates.py tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe. Stage only the refactor-owned paths; do not stage
`docs/research/**`.

### Current Candidate B: Backend Command-Layer Catalog Adoption

Severity: P1

Entropy source: backend abstraction live-source drift.

Materiality: public backend metadata now lives in
`roboclaws/launch/backends.py`, and Python cleanup sessions are built through
`build_cleanup_backend_session(...)`; however, `just/agent.just` and
`just/molmo.just` still branch on implementation backend strings and duplicate
supported-backend validation.

Impact radius: workflow.

Maintainer test: adding or changing a backend option should not require
updating launch catalog metadata, Python facade construction, and multiple
Bash branch ladders separately.

Affected paths:

- `roboclaws/launch/backends.py`
- `roboclaws/launch/catalog.py`
- `roboclaws/household/backend_contract.py`
- `just/agent.just`
- `just/molmo.just`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`

Owner skill: `intuitive-refactor`

Zen hint: make one canonical backend mapping obvious from public id to
implementation id.

Pattern hint: catalog/facade adoption; avoid another compatibility layer.

Suggested proof:

- `ruff check roboclaws/launch/backends.py roboclaws/launch/catalog.py roboclaws/household/backend_contract.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `ruff format --check roboclaws/launch/backends.py roboclaws/launch/catalog.py roboclaws/household/backend_contract.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/molmo_cleanup/test_cleanup_backend_contract.py -q`
- `just --dry-run run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-oracle-labels`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Preserve public `backend=` ids and current
implementation backend values; do not broaden Agibot GDK behavior in the same
slice.

### Current Candidate C: Apple-To-Apple Parity Diagnostics Split

Severity: P1

Entropy source: visual backend parity rediscovery.

Materiality:
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` is 5844
lines with six grouped complexity rows. It combines run orchestration,
object-gate classification, material response probes, tone/color probe history,
USD PreviewSurface checks, report rendering, and private render-contract
imports.

Impact radius: workflow.

Maintainer test: renderer parity investigations should not require reviewers
to rediscover object, material, tone/color, camera, and report diagnostics in
one render-only script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- likely focused helpers under `scripts/molmo_cleanup/`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable by concern.

Pattern hint: direct diagnostic-helper extraction; no full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for report/diagnostic extraction; real renderer parity
claims need separate local proof.

### Current Candidate D: OpenAI Agents Live Runtime Residual Boundary

Severity: P1

Entropy source: live-agent runtime workflow friction.

Materiality: after metrics aggregation moved to
`scripts/molmo_cleanup/openai_agents_metrics.py`,
`scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` still has residual
SDK-run lifecycle and RAW-FPV budget-policy rows, while
`roboclaws/agents/drivers/openai_agents_live.py` keeps SDK setup,
camera-grounded history, and MCP text-content unwrapping complexity.

Impact radius: workflow.

Maintainer test: provider/profile, retry, context-metric, or RAW-FPV budget
changes should not require tracing both the cleanup runner and generic SDK
driver internals.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: keep task lifecycle policy separate from generic SDK adapter logic.

Pattern hint: lifecycle/budget helpers plus adapter parsing helpers.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `ruff format --check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate E: Detector-Sidecar Adapter Contract Residual

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active visual-grounding sidecar is detector-only, so client
failure handling, adapter response parsing, and benchmark scoring are the
promotion boundary. The request/response schema split is done, but
`HttpVisualGroundingClient.request_candidates(...)`,
`_yolo_candidates_from_model(...)`, and benchmark scoring remain branch-heavy.

Impact radius: workflow.

Maintainer test: malformed or weak detector responses should fail through
small auditable client, adapter, and scoring helpers instead of scattered HTTP
and benchmark branches.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- `scripts/visual_grounding/adapters.py`
- `scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: keep the external detector trust boundary explicit.

Pattern hint: adapter parser plus scoring pipeline helpers.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving parser/scoring extraction. Real
detector behavior remains outside the default gate.

### Current Candidate F: MCP Server Initialization And Done Finalization Residual

Severity: P2

Entropy source: live MCP workflow friction.

Materiality: `RealWorldMolmoCleanupMCPServer.__init__` still has a PLR0915 row
after done-finalization and runtime artifact helpers were split. The server
initialization path still binds session setup, capability policy, artifact
paths, operator messages, and backend metadata in one constructor.

Impact radius: workflow.

Maintainer test: live MCP cleanup changes should not hide server setup,
capability policy, and artifact-finalization behavior in one branch-heavy
constructor.

Affected paths:

- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/household/realworld_mcp_run_artifacts.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`

Owner skill: `intuitive-refactor`

Zen hint: make live MCP server setup stages explicit.

Pattern hint: setup options object or constructor helper stages; avoid a
second server abstraction.

Suggested proof:

- `ruff check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `ruff format --check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe if MCP tool payloads and report artifacts remain stable.

### Current Candidate G: Behavior-Test Fixture Builders

Severity: P2

Entropy source: test-suite recurring rediscovery.

Materiality: the biggest test files repeatedly hand-build `run_result`,
`report.html`, Isaac scene-index, robot-camera state, and live-runtime event
fixtures. The issue is not line count alone; the repeated fixture construction
makes schema changes hard to audit.

Impact radius: workflow.

Maintainer test: behavior changes should not require re-reading
multi-thousand-line tests just to identify fixture setup, exercised behavior,
and asserted contract fields.

Affected paths:

- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/unit/agents/test_live_runtime.py`
- likely helpers under `tests/support/`

Owner skill: `intuitive-tests`

Zen hint: make tests tell one behavior story per fixture family.

Pattern hint: fixture/factory extraction and behavior-grouped modules; avoid
splitting only for aesthetics.

Suggested proof:

- `./scripts/dev/run_pytest_standalone.sh <selected test file> -q`
- `ruff check <selected test file and helper modules>`
- `ruff format --check <selected test file and helper modules>`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Route through `intuitive-tests`; keep behavior
assertions visible after fixture extraction.

### Current Candidate H: Agent Guidance Skill-Router Drift

Severity: P2

Entropy source: agent guidance live-source drift.

Materiality: `AGENTS.md` and `CLAUDE.md` tell agents to use
`hybrid-phase-pipeline` when available, but the installed skill set in this
environment exposes `intuitive-flow` and no `hybrid-phase-pipeline` skill.
This creates avoidable startup rediscovery for exactly the cleanup workflow
this plan uses.

Impact radius: workflow.

Maintainer test: new agents should be routed to the actual installed workflow
entrypoint instead of probing for a missing skill before starting repo work.

Affected paths:

- `AGENTS.md`
- `CLAUDE.md`
- possibly `docs/agents/**` if the repo wants a durable skill-routing note

Owner skill: `intuitive-init`

Zen hint: keep agent startup truth explicit and current.

Pattern hint: no pattern; direct guidance alignment is clearer.

Suggested proof:

- `rg -n "hybrid-phase-pipeline|intuitive-flow" AGENTS.md CLAUDE.md docs/agents docs/human`
- `rg --files "$HOME/.codex/skills" "$HOME/.agents/skills" | rg 'hybrid-phase|intuitive-flow/SKILL\\.md$'`

Execution risk: safe if scoped to agent guidance. Do not rewrite broader repo
orientation in the same slice.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Backend-Catalog Adoption

This loop rechecked the repo after the robot-camera visual-parity summary-gate
extraction and the first backend command-layer catalog adoption landed as clean
commits. It supersedes the "Post-Robot-Camera Summary Gates" packet for current
selection. The old Candidate A and Candidate B from that packet are complete:
the summary-gate helper is committed, and `just/molmo.just` plus the
map-build Codex backend gate now route the first command-layer implementation
backend choices through `roboclaws.launch.backends`.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 60`
  reports 101 Ruff complexity violations and 59 oversized modules.
- The largest implementation hotspots remain specialized, not the main backend
  facade path: `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635
  lines, 0 grouped rows), `roboclaws/household/scene_camera_comparison.py`
  (6480 lines, 0 grouped rows),
  `roboclaws/household/realworld_contract.py` (6424 lines, 3 grouped rows),
  `roboclaws/household/report.py` (6195 lines, 0 grouped rows), and
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` (5844
  lines, 6 grouped rows).
- The backend catalog probe found no new P1 backend command-layer drift after
  the first catalog adoption. Remaining `just/agent.just` branches are
  Agibot-specific execution behavior, context gates, and live-runner assembly,
  not another generic backend mapping slice.
- The high-noise summary still shows `.planning/**`, `docs/plans/**`, output,
  tests, and profile surfaces as large/live, but the fresh probes did not find
  a new P0/P1 docs or generated-output source-of-truth break beyond the agent
  guidance skill-router drift recorded below.

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: eight eligible candidates, no rejected candidates, no warnings.
- Saturation check: the backend/server/operator-console mainline is saturated
  for this batch. Continuing should select one of the specialized candidates
  below, or route test and agent-guidance work to their specialist owner
  skills. Do not reopen completed report, backend facade, scene-camera, or
  operator-console mainline slices unless fresh drift appears.

### Current Candidate A: Apple-To-Apple Parity Diagnostics Split

Severity: P1

Entropy source: visual backend parity rediscovery.

Materiality: `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
is 5844 lines with six grouped complexity rows:
`run_comparison(...)`, `_object_gate_classification(...)`,
`_material_response_probe_history(...)`, `_tone_color_probe_history(...)`,
`_texture_material_target_summary(...)`, and
`_usd_preview_surface_material_model_check(...)`. Current visual-parity status
and plans still use apple-to-apple reports as live renderer evidence.

Impact radius: workflow.

Maintainer test: renderer parity fixes should not force reviewers to
rediscover object gates, material probes, tone/color checks, USD checks, and
report orchestration in one script.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- likely focused helpers under `scripts/molmo_cleanup/`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `docs/status/active/mujoco-isaac-camera-visual-parity.md` only if run
  evidence changes

Owner skill: `intuitive-refactor`

Zen hint: make backend visual diagnostics reusable by concern.

Pattern hint: direct diagnostic-helper extraction; no full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for extraction-only diagnostic/report helpers. Real
renderer parity claims still need a separate local renderer proof.

### Current Candidate B: OpenAI Agents Residual Lifecycle And Budget Policy

Severity: P2

Entropy source: live-agent runtime workflow friction.

Materiality: after metrics aggregation moved to
`scripts/molmo_cleanup/openai_agents_metrics.py`,
`scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` still has
`_run_sdk_agent(...)` and `_raw_fpv_budget_failure(...)` C901 rows, while
`roboclaws/agents/drivers/openai_agents_live.py` still has
`_run_openai_agents(...)` PLR0915 plus camera-grounded history and MCP text
payload unwrapping C901 rows.

Impact radius: workflow.

Maintainer test: provider/profile or RAW-FPV budget changes should not require
tracing SDK lifecycle, budget failure classification, camera history
extraction, and MCP payload unwrapping across two large modules.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: keep task lifecycle policy separate from generic SDK adapter logic.

Pattern hint: lifecycle/budget helpers plus adapter parsing helpers.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `ruff format --check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate C: Detector-Sidecar Adapter And Benchmark Scoring Residual

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: the active visual-grounding sidecar is detector-only, so client
failure handling, adapter response parsing, and benchmark scoring are promotion
boundaries. The schema split is done, but
`HttpVisualGroundingClient.request_candidates(...)`,
`scripts/visual_grounding/adapters.py::_yolo_candidates_from_model(...)`, and
`scripts/visual_grounding/run_visual_grounding_benchmark.py::_score_predictions(...)`
remain branch-heavy.

Impact radius: workflow.

Maintainer test: malformed or weak detector responses should fail through
auditable client, adapter, and scoring helpers before detector benchmark
promotion is trusted.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- `scripts/visual_grounding/adapters.py`
- `scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `tests/unit/molmo_cleanup/test_visual_grounding.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: keep the external detector trust boundary explicit.

Pattern hint: adapter parser plus scoring pipeline helpers.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving parser/scoring extraction. Real
detector behavior remains outside the default gate.

### Current Candidate D: MCP Server Initialization Residual

Severity: P2

Entropy source: live MCP workflow friction.

Materiality: `RealWorldMolmoCleanupMCPServer.__init__` still has a PLR0915 row
at 57 > 50 after done-finalization, backend facade, and run-artifact helpers
were split. The constructor still binds session setup, capability policy,
artifact paths, operator messages, and backend metadata.

Impact radius: workflow.

Maintainer test: live MCP cleanup changes should not hide server setup,
capability policy, artifact paths, operator messages, and backend metadata
inside one long constructor.

Affected paths:

- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/household/realworld_mcp_run_artifacts.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`

Owner skill: `intuitive-refactor`

Zen hint: make live MCP server setup stages explicit.

Pattern hint: setup options object or constructor helper stages; avoid a
second server abstraction.

Suggested proof:

- `ruff check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `ruff format --check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe if MCP tool payloads and report artifacts remain stable.

### Current Candidate E: Agibot Context, Rehearsal, And Proof Fallback Stages

Severity: P2

Entropy source: Agibot/backend proof workflow rediscovery.

Materiality: `docs/human/agibot-g2-cleanup-pilot.md` uses completed
`context_json` and `scripts/agibot/generate_metric_map_from_context.py` as live
operator steps. The current grouped rows are
`roboclaws/household/agibot_contract_rehearsal.py` (four rows),
`roboclaws/household/planner_proof_requests.py` (four rows), and
`scripts/agibot/generate_metric_map_from_context.py` (three rows).

Impact radius: workflow.

Maintainer test: Agibot map-context, rehearsal, and proof-fallback changes
should not force reviewers through mixed validation and orchestration functions
before backend-specific evidence can be trusted.

Affected paths:

- `scripts/agibot/generate_metric_map_from_context.py`
- `roboclaws/household/agibot_contract_rehearsal.py`
- `roboclaws/household/planner_proof_requests.py`
- `tests/contract/agibot/test_agibot_map_context_scripts.py`
- `tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py`
- `tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py`

Owner skill: `intuitive-refactor`

Zen hint: keep operator map-context validation, rehearsal evidence, and proof
fallback selection separate.

Pattern hint: validation pipeline plus stage helper extraction; keep real
Agibot GDK behavior behind existing local/backend gates.

Suggested proof:

- `ruff check scripts/agibot/generate_metric_map_from_context.py roboclaws/household/agibot_contract_rehearsal.py roboclaws/household/planner_proof_requests.py tests/contract/agibot/test_agibot_map_context_scripts.py tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py`
- `ruff format --check scripts/agibot/generate_metric_map_from_context.py roboclaws/household/agibot_contract_rehearsal.py roboclaws/household/planner_proof_requests.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/agibot/test_agibot_map_context_scripts.py tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Real Agibot GDK behavior remains local/backend-gated;
default proof should stay on mock/contract tests.

### Current Candidate F: RAW-FPV Perception Probe Scoring

Severity: P2

Entropy source: camera-evidence false-confidence risk.

Materiality: `camera-raw-fpv` remains a current public evidence lane in
`ARCHITECTURE.md`, `just/README.md`, and `just/molmo.just`.
`scripts/molmo_cleanup/run_raw_fpv_perception_probe.py::score_variant(...)`
still carries C901 19, PLR0912 18, and PLR0915 72 while mixing variant
metrics, evidence quality, and gate status decisions.

Impact radius: workflow.

Maintainer test: RAW-FPV probe reports should not publish pass/fail summaries
from one scorer that mixes variant metrics, evidence quality, and gate status
decisions.

Affected paths:

- `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py`
- `tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`

Owner skill: `intuitive-refactor`

Zen hint: make camera-evidence gates explicit and reviewable.

Pattern hint: scoring-stage helpers; direct extraction is clearer than a new
probe framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `ruff format --check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for scoring extraction; live camera/provider claims need
a separate local run.

### Current Candidate G: Behavior-Test Fixture Builders

Severity: P2

Entropy source: test-suite recurring rediscovery.

Materiality: the top oversized tests repeatedly hand-build `run_result`,
`report.html`, Isaac scene-index, robot-camera state, and live-runtime event
fixtures. This is not a line-count-only issue: repeated fixture construction
makes schema changes harder to audit, and several test files are now larger
than implementation modules.

Impact radius: workflow.

Maintainer test: behavior changes should not require re-reading
multi-thousand-line tests to identify fixture setup, exercised behavior, and
asserted contract fields.

Affected paths:

- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- likely helpers under `tests/support/`

Owner skill: `intuitive-tests`

Zen hint: make tests tell one behavior story per fixture family.

Pattern hint: fixture/factory extraction and behavior-grouped modules; avoid
splitting only for aesthetics.

Suggested proof:

- `./scripts/dev/run_pytest_standalone.sh <selected test file> -q`
- `ruff check <selected test file and helper modules>`
- `ruff format --check <selected test file and helper modules>`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Route through `intuitive-tests`; keep behavior
assertions visible after fixture extraction.

### Current Candidate H: Agent Guidance Skill-Router Drift

Severity: P2

Entropy source: agent guidance live-source drift.

Materiality: `AGENTS.md` and `CLAUDE.md` still tell agents to use
`hybrid-phase-pipeline` when available, but the installed skill set in this
environment exposes `/home/mi/.codex/skills/intuitive-flow/SKILL.md` and no
`hybrid-phase-pipeline` skill. This creates startup rediscovery for exactly
the workflow used by this plan.

Impact radius: workflow.

Maintainer test: new agents should be routed to the installed workflow
entrypoint instead of probing for a missing hybrid-phase skill before starting
repo work.

Affected paths:

- `AGENTS.md`
- `CLAUDE.md`
- possibly `docs/agents/**` if the repo wants a durable skill-routing note

Owner skill: `intuitive-init`

Zen hint: keep agent startup truth explicit and current.

Pattern hint: no pattern; direct guidance alignment is clearer.

Suggested proof:

- `rg -n "hybrid-phase-pipeline|intuitive-flow" AGENTS.md CLAUDE.md docs/agents docs/human`
- `rg --files "$HOME/.codex/skills" "$HOME/.agents/skills" | rg 'hybrid-phase|intuitive-flow/SKILL\\.md$'`

Execution risk: safe if scoped to agent guidance. Do not rewrite broader repo
orientation in the same slice.

## Latest Reduce-Entropy Loop: 2026-06-14 Post-Object-Gate Split

This loop rechecked the repo after the apple-to-apple object-gate extraction
landed as commit `589c4591`. It supersedes the "Post-Backend-Catalog
Adoption" packet for current selection. The old Candidate A has been narrowed:
material, tone/color, USD PreviewSurface, and object-gate diagnostics are now
split; only the apple-to-apple comparison run orchestration remains as a
grouped row. Backend facade, backend command-layer catalog, report,
scene-camera, and operator-console mainline slices remain saturated for this
batch unless fresh drift appears.

Quality signal:

- `python scripts/dev/check_python_quality_ratchet.py --summary --top 40`
  reports 96 Ruff complexity violations and 59 oversized modules.
- Largest current implementation hotspots are
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` (7635 lines, 0
  grouped rows), `roboclaws/household/scene_camera_comparison.py` (6480 lines,
  0 grouped rows), `roboclaws/household/realworld_contract.py` (6424 lines, 3
  grouped rows), `roboclaws/household/report.py` (6195 lines, 0 grouped rows),
  and `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` (5279
  lines, 1 grouped row).
- Current grouped implementation rows cluster around live-agent runtime
  boundaries, RAW-FPV scoring, Agibot map/rehearsal/proof workflow, live MCP
  initialization, detector-sidecar residual parsing/scoring, and a few
  residual specialized helpers. Top oversized behavior tests remain a separate
  test-fixture cleanup direction, not a reason to churn production modules.

Materiality gate:

- Gate command:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/materiality-gate.mjs" <tmpfile>`.
- Gate result: eight eligible candidates, no rejected candidates, no warnings.
- Saturation check: the loop should continue only through one of the candidates
  below. Do not reopen completed backend facade, report, scene-camera,
  operator-console, visual-parity summary-gate, material diagnostics, or
  object-gate slices without new evidence.

### Current Candidate A: OpenAI Agents Residual Runtime Boundary

Severity: P1

Entropy source: live-agent runtime workflow friction.

Status: complete as of the 2026-06-14 OpenAI Agents setup split. Keep this
section as evidence for the completed P1 slice; do not reopen it unless fresh
live-agent runtime drift appears.

Materiality: false confidence and real workflow friction. Metrics aggregation
moved to `scripts/molmo_cleanup/openai_agents_metrics.py`, RAW-FPV
budget-guard classification moved to
`scripts/molmo_cleanup/openai_agents_budget.py`, and the remaining SDK adapter
setup/parser branches are split inside
`roboclaws/agents/drivers/openai_agents_live.py`. These files no longer appear
in the complexity-by-file summary for production rows.

Impact radius: workflow.

Maintainer test: provider/profile, continuation, RAW-FPV budget, and MCP
payload changes now fail in smaller audited helpers rather than across the
cleanup runner and generic SDK driver.

Affected paths:

- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `roboclaws/agents/drivers/openai_agents_live.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`

Owner skill: `intuitive-refactor`

Zen hint: keep task lifecycle policy separate from generic SDK adapter parsing.

Pattern hint: lifecycle/budget helpers plus adapter parsing helpers.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `ruff format --check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Keep provider calls mocked; do not claim live provider
behavior without a local live-agent run.

### Current Candidate B: RAW-FPV Perception Probe Scoring

Severity: P2

Entropy source: camera-evidence false-confidence risk.

Status: complete as of the 2026-06-14 RAW-FPV scoring split. Keep this
section as evidence for the completed P2 slice; reopen only if fresh
`camera-raw-fpv` scoring/report drift appears.

Materiality: false confidence and real workflow friction.
`camera-raw-fpv` remains a current public evidence lane in `ARCHITECTURE.md`
and `just/README.md`.
`scripts/molmo_cleanup/run_raw_fpv_perception_probe.py::score_variant(...)`
now delegates to `scripts/molmo_cleanup/raw_fpv_perception_scoring.py`, where
hidden-target recovery, visible-movable quality, duplicate accounting, schema
failures, and gate-status assembly are isolated behind a focused scoring
accumulator. The original C901 19, PLR0912 18, and PLR0915 72 rows are gone
from the complexity summary.

Impact radius: workflow.

Maintainer test: RAW-FPV reports should not publish pass/fail summaries from
one branch-heavy scorer that mixes evidence quality and gate decisions.

Affected paths:

- `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py`
- `scripts/molmo_cleanup/raw_fpv_perception_scoring.py`
- `tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`

Owner skill: `intuitive-refactor`

Zen hint: make camera-evidence gates explicit and reviewable.

Pattern hint: scoring-stage helpers; direct extraction is clearer than a new
probe framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `ruff format --check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for scoring extraction. The completed proof is static and
unit-level; live camera/provider claims still need a separate local run.

### Current Candidate C: Agibot Context, Rehearsal, MCP Tools, And Proof Fallbacks

Severity: P2

Entropy source: Agibot/backend proof workflow rediscovery.

Status: in progress. The 2026-06-14 map-context validation/projection slice is
complete; rehearsal orchestration, MCP tool registration, and planner-proof
fallback rows remain for later Candidate C slices.

Materiality: real workflow friction and recurring rediscovery.
`docs/human/agibot-g2-cleanup-pilot.md` uses completed `context_json` and
`scripts/agibot/generate_metric_map_from_context.py` as live operator steps.
The current grouped rows span `roboclaws/household/agibot_contract_rehearsal.py`,
`roboclaws/household/agibot_map_build_mcp_server.py`,
`roboclaws/household/planner_proof_requests.py`, and
`scripts/agibot/generate_metric_map_from_context.py`.
`scripts/agibot/generate_metric_map_from_context.py` no longer has Ruff
complexity rows after the validation and coordinate-bounds split. The
`vendors/agibot_sdk` pointer now includes submodule commit `910a76d` so the SDK
runner accepts the same minimal map-context contract as the main generator,
including public room labels while keeping fixtures and authored inspection
waypoints hidden.

Impact radius: workflow.

Maintainer test: Agibot map-context and prehardware rehearsal changes should
not require re-reading mixed validation, MCP registration, rehearsal
orchestration, and proof fallback functions before trusting backend evidence.

Affected paths:

- `scripts/agibot/generate_metric_map_from_context.py`
- `vendors/agibot_sdk`
- `roboclaws/household/agibot_contract_rehearsal.py`
- `roboclaws/household/agibot_map_build_mcp_server.py`
- `roboclaws/household/planner_proof_requests.py`
- `tests/contract/agibot/test_agibot_map_context_scripts.py`
- `tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py`
- `tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py`

Owner skill: `intuitive-refactor`

Zen hint: keep operator map-context validation, MCP tool registration,
rehearsal evidence, and proof fallback selection separate.

Pattern hint: validation pipeline plus stage helper extraction; keep real
Agibot GDK behavior behind existing local/backend gates.

Suggested proof:

- `ruff check scripts/agibot/generate_metric_map_from_context.py roboclaws/household/agibot_contract_rehearsal.py roboclaws/household/agibot_map_build_mcp_server.py roboclaws/household/planner_proof_requests.py tests/contract/agibot/test_agibot_map_context_scripts.py tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py`
- `ruff format --check scripts/agibot/generate_metric_map_from_context.py roboclaws/household/agibot_contract_rehearsal.py roboclaws/household/agibot_map_build_mcp_server.py roboclaws/household/planner_proof_requests.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/agibot/test_agibot_map_context_scripts.py tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Real Agibot GDK behavior remains local/backend-gated;
default proof should stay on mock/contract tests.

### Current Candidate D: Live MCP Server Initialization Residual

Severity: P2

Entropy source: live MCP workflow friction.

Materiality: real workflow friction and recurring rediscovery.
`RealWorldMolmoCleanupMCPServer.__init__` remains PLR0915 57 > 50 after
done-finalization and backend artifact helpers landed. The constructor still
binds run directory setup, agent policy, task intent, map/runtime priors,
backend contract construction, visual grounding, operator messages, and
robot-view capture policy.

Impact radius: workflow.

Maintainer test: live MCP cleanup setup changes should not hide capability
policy, artifact paths, operator messages, and backend metadata in one long
constructor.

Affected paths:

- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/household/realworld_mcp_run_artifacts.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`

Owner skill: `intuitive-refactor`

Zen hint: make live MCP server setup stages explicit.

Pattern hint: setup options object or constructor helper stages; avoid a
second server abstraction.

Suggested proof:

- `ruff check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `ruff format --check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe if MCP tool payloads and report artifacts remain stable.

### Current Candidate E: Detector-Sidecar Residual Parsing And Scoring

Severity: P2

Entropy source: detector-sidecar false-confidence risk.

Materiality: false confidence and real workflow friction. The active sidecar
is detector-only, so client failure handling, adapter response parsing, and
benchmark scoring are promotion boundaries. The schema split is done, but
`HttpVisualGroundingClient.request_candidates(...)`,
`scripts/visual_grounding/adapters.py::_yolo_candidates_from_model(...)`, and
`scripts/visual_grounding/run_visual_grounding_benchmark.py::_score_predictions(...)`
remain branch-heavy.

Impact radius: workflow.

Maintainer test: malformed or weak detector responses should be parsed and
scored through auditable helpers before benchmark promotion is trusted.

Affected paths:

- `roboclaws/household/visual_grounding.py`
- `scripts/visual_grounding/adapters.py`
- `scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `tests/unit/molmo_cleanup/test_visual_grounding.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`

Owner skill: `intuitive-refactor`

Zen hint: keep the external detector trust boundary explicit.

Pattern hint: adapter parser plus scoring pipeline helpers.

Suggested proof:

- `ruff check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
- `ruff format --check roboclaws/household/visual_grounding.py scripts/visual_grounding/adapters.py scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for schema-preserving parser/scoring extraction. Real
detector behavior remains outside the default gate.

### Current Candidate F: Apple-To-Apple Run Orchestration Split

Severity: P2

Entropy source: visual backend parity rediscovery.

Materiality: real workflow friction and recurring rediscovery.
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` is now 5279
lines with one grouped complexity row:
`run_comparison(...)` PLR0915 76 > 50. The completed helper splits removed
material-response, tone/color, USD material-model, and object-gate
classification rows; the remaining friction is command/run orchestration and
manifest/artifact setup.

Impact radius: workflow.

Maintainer test: renderer parity investigations should not require reviewers
to rediscover MuJoCo/Isaac initialization, canonical manifest generation,
artifact path setup, and report flow inside one long runner entrypoint.

Affected paths:

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- likely focused helper under `scripts/molmo_cleanup/`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`

Owner skill: `intuitive-refactor`

Zen hint: make the remaining comparison pipeline read as ordered stages.

Pattern hint: run-stage helper extraction; no full parity framework.

Suggested proof:

- `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: safe for extraction-only runner stages. Real renderer parity
claims still need separate local renderer proof.

### Current Candidate G: Agent Guidance Skill-Router Drift

Severity: P2

Entropy source: agent guidance live-source drift.

Materiality: live source drift and recurring rediscovery. `AGENTS.md` and
`CLAUDE.md` still tell agents to use `hybrid-phase-pipeline` when available,
but the installed skill set in this environment exposes
`/home/mi/.codex/skills/intuitive-flow/SKILL.md` and no
`hybrid-phase-pipeline` skill. This creates startup rediscovery for exactly the
workflow used by this plan.

Impact radius: workflow.

Maintainer test: new agents should be routed to the installed workflow
entrypoint instead of probing for a missing hybrid-phase skill before starting
repo work.

Affected paths:

- `AGENTS.md`
- `CLAUDE.md`
- possibly `docs/agents/**` if the repo wants a durable skill-routing note

Owner skill: `intuitive-init`

Zen hint: keep agent startup truth explicit and current.

Pattern hint: no pattern; direct guidance alignment is clearer.

Suggested proof:

- `rg -n "hybrid-phase-pipeline|intuitive-flow" AGENTS.md CLAUDE.md docs/agents docs/human`
- `rg --files "$HOME/.codex/skills" "$HOME/.agents/skills" | rg 'hybrid-phase|intuitive-flow/SKILL\\.md$'`

Execution risk: safe if scoped to agent guidance. Do not rewrite broader repo
orientation in the same slice.

### Current Candidate H: Behavior-Test Fixture Builders

Severity: P2

Entropy source: test-suite recurring rediscovery.

Materiality: recurring rediscovery and real workflow friction. The top
oversized tests repeatedly hand-build `run_result`, `report.html`, Isaac
scene-index, robot-camera state, and live-runtime event fixtures. This is not
line-count-only: repeated fixture construction makes schema changes harder to
audit, and several test files are now larger than implementation modules.

Impact radius: workflow.

Maintainer test: schema changes should not require re-reading
multi-thousand-line tests to identify fixture setup, exercised behavior, and
asserted contract fields.

Affected paths:

- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- likely helpers under `tests/support/`

Owner skill: `intuitive-tests`

Zen hint: make tests tell one behavior story per fixture family.

Pattern hint: fixture/factory extraction and behavior-grouped modules; avoid
splitting only for aesthetics.

Suggested proof:

- `./scripts/dev/run_pytest_standalone.sh <selected test file> -q`
- `ruff check <selected test file and helper modules>`
- `ruff format --check <selected test file and helper modules>`
- `python scripts/dev/check_python_quality_ratchet.py`

Execution risk: medium. Route through `intuitive-tests`; keep behavior
assertions visible after fixture extraction.

## Evidence Ladder

- L0 static:
  - `ruff check <touched files>`
  - `python scripts/dev/check_python_quality_ratchet.py`
  - quality-debt summary mode after Q1 exists
- L1 unit/mock:
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_cleanup_backend_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py -q`
    when optional backend facade capabilities change
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  - targeted unit tests for new backend facade/factory modules
- L2 contract:
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/scripts/test_run_molmo_planner_proof_bundle_from_requests.py tests/contract/checkers/test_check_molmo_planner_proof_bundle_runner_result.py tests/contract/checkers/test_check_molmo_planner_manipulation_probe.py -q` when planner-proof checker/probe code changes
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/maps/test_actionable_semantic_map_snapshot.py tests/contract/maps/test_agibot_map_bundle_export.py -q` when map bundle or snapshot code changes
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/test_verify_just_recipes.py -q` when launch or verify plumbing changes
  - report tests when `report.py` is touched
- L4 local simulator:
  - Real MolmoSpaces/Isaac runs only when the selected slice claims real
    simulator behavior changed and the local environment is ready.

## Stop Condition

Stop this refactor loop when:

- `run_realworld_cleanup` no longer contains backend-specific metadata/artifact
  assembly for MolmoSpaces and Isaac Lab.
- Direct cleanup and live MCP cleanup use `CleanupBackendSession` for optional
  backend capabilities such as snapshots, robot views, close, final locations,
  and requested run size, instead of rediscovering backend internals separately.
- `run_realworld_cleanup` is mostly an orchestration reader: setup, loop
  execution, artifact assembly, report rendering, and result writeback are named
  stages with focused tests.
- Backend id selection no longer depends on concrete class-name checks in live
  paths that can use the facade.
- Isaac worker internals either have a focused split plan or the final
  saturation round records why the worker remains parked.
- The quality ratchet is still green and the baseline was deliberately lowered
  for every completed slice.
- The live checker, contract, and report candidates are either completed or
  explicitly parked with a current no-change reason.
- A final bounded reduce-entropy round finds no P0/P1 or materially useful P2
  direction in this code-size/backend-complexity class.

## Execution Log

- 2026-06-14: Created plan from the post-ratchet reduce-entropy audit. Current
  baseline is 217 Ruff complexity violations and 61 oversized modules, with
  `python scripts/dev/check_python_quality_ratchet.py` passing. The top live
  cleanup targets are backend orchestration leakage, live checker assertions,
  `RealWorldCleanupContract` payload construction, and report section
  rendering.
- 2026-06-14: Continued the reduce-entropy loop against adjacent live
  quality-gate surfaces. `python scripts/dev/check_python_quality_ratchet.py`
  still passes with 217 Ruff complexity violations and 61 oversized modules.
  The materiality gate accepted three new checklist candidates:
  planner-proof bundle checker splitting, planner manipulation probe/checker
  splitting, and map bundle / actionable snapshot validation splitting. The
  accepted-candidate gate reported `eligible_count=3` and
  `quota_saturated=true` for a requested maximum of five, so the loop should
  not invent more groups. OpenAI Agents SDK, operator console, scene-camera,
  Agibot, raw-FPV, and apple2apple surfaces were parked because current
  specialized plans already carry their distinct entropy.
- 2026-06-14: Implemented the first backend facade slice. `CleanupBackendSession`
  now exposes a backend id and runtime-artifact attachment surface,
  `build_cleanup_backend_session(...)` owns synthetic / MolmoSpaces / Isaac Lab
  backend construction, and direct cleanup plus MCP server finalization share
  the same backend metadata attachment path. Added focused facade tests and
  updated the MCP visual test double to expose an explicit backend id instead
  of relying on class-name inference. Evidence:
  `ruff check roboclaws/household/backend_contract.py roboclaws/household/realworld_cleanup.py roboclaws/household/realworld_mcp_server.py tests/unit/molmo_cleanup/test_cleanup_backend_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_cleanup_backend_contract.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed with 217
  Ruff violations and 61 oversized modules at or below baseline.
- 2026-06-14: Added the read-only quality-debt summary mode to
  `scripts/dev/check_python_quality_ratchet.py`. `--summary` now reports total
  Ruff complexity and oversized-module counts, top oversized modules, highest
  individual complexity entries, and complexity grouped by file while keeping
  the default gate output unchanged. Current top-five summary begins with
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`,
  `roboclaws/household/report.py`,
  `roboclaws/household/realworld_contract.py`,
  `roboclaws/household/scene_camera_comparison.py`, and
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` for file
  size, and
  `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py` remains the
  highest grouped complexity file. Evidence:
  `./scripts/dev/run_pytest_standalone.sh tests/unit/scripts/test_python_quality_ratchet.py -q`
  passed; `ruff check scripts/dev/check_python_quality_ratchet.py tests/unit/scripts/test_python_quality_ratchet.py`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed with 217
  Ruff violations and 61 oversized modules at or below baseline;
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 5`
  passed. No baseline refresh was run because this slice adds selection
  visibility but does not pay down existing debt.
- 2026-06-14: Normalized the one-shot subprocess worker runner shared by
  MolmoSpaces and Isaac Lab. Added `roboclaws/household/worker_runner.py` for
  worker command assembly, missing-runtime errors, timeout/env helpers,
  non-zero exit formatting, stderr reading, and last-JSON parsing. The
  MolmoSpaces one-shot path and Isaac Lab wrapper now call the shared runner,
  while MolmoSpaces persistent-worker behavior remains Molmo-specific by
  design. Evidence:
  `ruff check roboclaws/household/worker_runner.py roboclaws/household/subprocess_backend.py roboclaws/household/isaac_lab_backend.py tests/unit/molmo_cleanup/test_worker_runner.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_worker_runner.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with one existing Pillow deprecation warning from the Isaac worker
  tests; `python scripts/dev/check_python_quality_ratchet.py` passed with 217
  Ruff violations and 61 oversized modules at or below baseline;
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 5`
  passed. No baseline refresh was run because the ratcheted debt counts did not
  decrease.
- 2026-06-14: Split the live cleanup checker assertion pipeline. The main
  checker now routes `_assert_result` through staged helpers for core run
  result, public agent/runtime-map checks, private evaluation and semantic
  success, artifact/report checks, optional agent/planner/backend gates, and
  backend-specific Isaac runtime evidence. Isaac runtime and semantic-pose
  evidence checks moved to focused checker modules under
  `scripts/molmo_cleanup/`, keeping each new module below the 800-line
  oversized-module threshold. Evidence:
  `python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py --help`
  passed; `ruff check scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py scripts/molmo_cleanup/isaac_runtime_checker.py scripts/molmo_cleanup/isaac_semantic_pose_checker.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 217 to 211 Ruff complexity
  violations, with oversized modules unchanged at 61. The live cleanup checker
  grouped complexity count dropped from 20 to 14 violations.
- 2026-06-14: Ran another bounded reduce-entropy discovery loop after C1.
  Evidence: `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs"`;
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 30`;
  targeted probes across `realworld_cleanup.py`, `realworld_contract.py`,
  `report.py`, planner-proof checker/probe scripts, map bundle validation,
  `TODOs.md`, `tests/README.md`, and current `docs/plans/**` references. The
  current quality signal is 211 Ruff complexity violations and 61 oversized
  modules. The materiality gate accepted seven P1 candidates and reported
  `eligible_count=7`, `quota_saturated=true` for a requested maximum of eight:
  C1.5 direct cleanup orchestration/result assembly splitting; C2 contract
  construction/payload builders; C3 report section splitting; P1 planner-proof
  bundle checker phases; P2 planner manipulation probe/runtime packaging; M1
  map bundle validation/snapshot checks; and I1 Isaac worker backend-detail
  splitting. The new signal after backend facade work is that
  `run_realworld_cleanup` remains the highest individual complexity entry
  (`140>50 PLR0915`) because it now mixes execution loop, artifact writing,
  `run_result` construction, proof/profile/map attachment, report rendering,
  and writeback. OpenAI Agents SDK, operator-console, scene-camera/render
  parity, Agibot rehearsal/pilot, raw-FPV, apple2apple, and broad test-suite
  cleanup remain parked because current specialized plans or `intuitive-tests`
  own those surfaces; this loop should not count them again unless fresh drift
  appears.
- 2026-06-14: Implemented C1.5 direct cleanup orchestration/result assembly
  splitting. Added `roboclaws/household/realworld_run_artifacts.py` as the
  focused artifact finalizer for trace writing, public/private JSON artifacts,
  goal-contract artifacts, primitive/proof/profile/map/backend metadata
  attachment, report rendering, and final `run_result.json` writeback.
  `run_realworld_cleanup` now ends by passing explicit
  `RealWorldRunArtifactInputs` to that finalizer instead of assembling the
  report payload inline. A stale contract-test reference to the moved Isaac
  runtime checker helper was updated to import
  `scripts.molmo_cleanup.isaac_runtime_checker`. Evidence:
  `ruff check roboclaws/household/realworld_cleanup.py roboclaws/household/realworld_run_artifacts.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered for
  `roboclaws/household/realworld_cleanup.py`: file size 1429 -> 1171 lines,
  `run_realworld_cleanup` C901 30 -> 22, PLR0912 32 -> 23, and PLR0915
  140 -> 74. Overall debt count remains 211 Ruff violations and 61 oversized
  modules because this slice lowered existing debt without removing all
  violation rows.
- 2026-06-14: Post-C1.5 discovery found one new material P1 candidate:
  direct cleanup and live MCP cleanup now published the same artifact family
  through diverging finalization code. The materiality gate accepted C1.6 for
  live source drift, real workflow friction, and recurring rediscovery.
  Implemented C1.6 by adding
  `roboclaws/household/realworld_mcp_run_artifacts.py` as the live MCP `done`
  finalizer for agent-view/runtime-map/private/advisory artifacts,
  goal-contract artifacts, scratchpad/proof request artifacts, `run_result`
  assembly, profile/map/backend metadata, planner-proof metadata, report
  rendering, and final writeback. `RealWorldMolmoCleanupMCPServer._finalize_done`
  now coordinates after-snapshot capture, trace reading, finalizer invocation,
  done-event state, and runtime trace emission. The server-local backend-name,
  backend-runtime, and run-metadata wrappers were removed in favor of
  contract-level backend overrides plus the backend facade's
  `attach_runtime_metadata(...)` path. Evidence:
  `ruff check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_adapter_integrates_with_shared_cleanup_mcp_contract tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 211 to 210 Ruff complexity
  violations, with oversized modules unchanged at 61. The
  `RealWorldMolmoCleanupMCPServer._finalize_done` PLR0915 row was removed from
  the explicit baseline; the server still carries the existing `__init__`
  PLR0915 row for a future bounded slice.
- 2026-06-14: Implemented the first C2 constructor-structure slice. Added
  `roboclaws/household/realworld_contract_init.py` for constructor option
  validation, profile/acceptance normalization, visual-grounding setup,
  map-bundle/scenario map projection setup, public minimal-map projection, and
  runtime state initialization. `RealWorldCleanupContract.__init__` now reads as
  a sequence of named initialization stages while public payload methods remain
  unchanged. Evidence:
  `ruff check roboclaws/household/realworld_contract.py roboclaws/household/realworld_contract_init.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
  passed; `ruff format --check roboclaws/household/realworld_contract.py roboclaws/household/realworld_contract_init.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 210 to 209 Ruff complexity
  violations, with oversized modules unchanged at 61. The
  `RealWorldCleanupContract.__init__` PLR0915 row was removed from the baseline,
  and `roboclaws/household/realworld_contract.py` dropped from 6942 to 6829
  lines at the time of the summary run because constructor helpers moved out of
  the oversized module.
- 2026-06-14: Ran another bounded reduce-entropy discovery loop after the C2
  constructor slice. Evidence:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs" --examples 12`;
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 60`;
  targeted probes across `realworld_contract.py`, `realworld_cleanup.py`,
  `realworld_mcp_server.py`, `backend_contract.py`, `report.py`, planner-proof
  checker/probe scripts, map bundle validation, current docs/plans references,
  and legacy/retired token searches. The current quality signal is 209 Ruff
  complexity violations and 61 oversized modules. No new P0 or public-doc
  command drift was found. The materiality gate accepted one new P1 candidate,
  B5 optional backend capability facade, because direct cleanup and live MCP
  cleanup still separately probe `base_contract.backend` for snapshots,
  robot-view support, close, final locations, and requested run size after the
  facade already centralized backend id and runtime metadata. The gate reported
  `eligible_count=1` and `quota_saturated=true` for five requested groups, so
  this loop should not invent more groups. Existing uncompleted candidates
  C2/C3/P1/P2/M1/I1 remain live and are still the main queue; OpenAI Agents SDK,
  operator console, scene-camera/render parity, Agibot, raw-FPV, apple2apple,
  broad test-suite cleanup, and historical docs/plans remain parked under their
  specialized plans or specialist skills unless fresh drift appears.
- 2026-06-14: Completed C2 by extracting runtime metric map and cleanup
  worklist payload assembly into
  `roboclaws/household/realworld_contract_payloads.py`. The public
  `RealWorldCleanupContract.runtime_metric_map_payload(...)` and
  `cleanup_worklist_payload(...)` methods remain in place as schema-preserving
  delegates, with a narrow protocol documenting the contract surface that the
  payload module consumes. Evidence:
  `ruff check roboclaws/household/realworld_contract.py roboclaws/household/realworld_contract_payloads.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
  passed; `ruff format --check roboclaws/household/realworld_contract.py roboclaws/household/realworld_contract_payloads.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered for
  `roboclaws/household/realworld_contract.py` file size from 6829 to 6602
  lines, with Ruff complexity unchanged at 209 violations and oversized
  modules unchanged at 61.
- 2026-06-14: Implemented B5 optional backend capability facade. `CleanupBackendSession`
  now owns scenario access, visual snapshot capability/proxying, robot-view
  support and recording, final/object locations, requested generated mess
  count, backend close, and run-option capability validation. Direct cleanup
  and live MCP cleanup now use the facade for snapshots, robot views, final
  locations, close, and requested run size instead of probing
  `base_contract.backend` separately. Evidence:
  `ruff check roboclaws/household/backend_contract.py roboclaws/household/realworld_cleanup.py roboclaws/household/realworld_mcp_server.py tests/unit/molmo_cleanup/test_cleanup_backend_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py`
  passed; `ruff format --check roboclaws/household/backend_contract.py roboclaws/household/realworld_cleanup.py roboclaws/household/realworld_mcp_server.py tests/unit/molmo_cleanup/test_cleanup_backend_contract.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_cleanup_backend_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered for
  `roboclaws/household/realworld_cleanup.py` file size 1171 -> 1159,
  `roboclaws/household/realworld_mcp_server.py` file size 1190 -> 1180, and
  `run_realworld_cleanup` complexity rows C901 22 -> 18, PLR0912 23 -> 19,
  PLR0915 74 -> 68. Overall Ruff complexity count remains 209 and oversized
  module count remains 61.
- 2026-06-14: Implemented the first C3 cleanup-report section split.
  Map-evidence refresh summary rendering moved to
  `roboclaws/household/report_sections_map.py`; runtime timing rendering and
  `runtime_timing_from_trace(...)` moved to
  `roboclaws/household/report_sections_timing.py`. Live cleanup runners,
  MCP artifact finalization, and report-performance extraction now import the
  timing helper from the section module instead of the monolithic report
  renderer. Evidence:
  `ruff check roboclaws/household/report.py roboclaws/household/report_sections_map.py roboclaws/household/report_sections_timing.py roboclaws/household/realworld_mcp_run_artifacts.py roboclaws/reports/live_performance.py scripts/molmo_cleanup/run_live_claude_cleanup.py scripts/molmo_cleanup/run_live_codex_cleanup.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/summarize_live_run.py`
  passed; `ruff format --check` for the same touched files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py tests/contract/molmo_cleanup/test_agibot_map_evidence_refresh_report.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 209 to 207 Ruff complexity
  violations, with oversized modules unchanged at 61. `report.py` file size
  dropped from 8607 to 7889 lines, and the `runtime_timing_from_trace` C901 and
  PLR0915 rows were removed from the report-module baseline.
- 2026-06-14: Ran the post-C3 bounded reduce-entropy discovery loop from clean
  `HEAD`. Evidence:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs" --examples 10`;
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 40`;
  targeted probes across planner-proof checker/probe scripts,
  `roboclaws/maps/bundle.py`, `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`,
  and the remaining `report.py` function families. Current quality signal is
  209 Ruff complexity violations and 61 oversized modules because the timing
  helper still carries its complexity in the new module, while `report.py`
  itself has dropped to three complexity rows. The materiality gate accepted
  the still-live queue: P1 planner-proof bundle checker phases, P2 planner
  manipulation probe/runtime packaging, M1 map bundle validation pipeline,
  I1 Isaac worker backend-detail splitting, and the remaining C3 proof/robot/
  agent report section families. No new unrelated P0/P1 public command or doc
  drift was found; OpenAI Agents SDK, operator console, scene-camera/render
  parity, Agibot, raw-FPV, apple2apple, and broad test-suite cleanup remain
  parked under their specialized plans or specialist skills.
- 2026-06-14: Implemented M1's Nav2 map-bundle validation pipeline. Added
  `roboclaws/maps/bundle_validation.py` for staged required-file,
  map.yaml/PGM, private-truth, semantics, waypoint, fixture, and route
  validation while keeping `validate_nav2_map_bundle(...)` and
  `parse_map_yaml(...)` import compatibility through `roboclaws/maps/bundle.py`.
  During this slice the quality ratchet exposed a C3 blind spot: the prior
  baseline write ran before the new report section files were tracked, so
  `report_sections_timing.runtime_timing_from_trace(...)` was split into
  smaller timing helpers instead of refreshing the baseline over newly visible
  debt. Evidence:
  `ruff check roboclaws/maps/bundle.py roboclaws/maps/bundle_validation.py roboclaws/household/report_sections_timing.py`
  passed; `ruff format --check` for the same touched files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/maps/test_actionable_semantic_map_snapshot.py tests/contract/maps/test_agibot_map_bundle_export.py tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_runtime_timing_breakdown tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_per_object_timing_cycles -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 207 to 204 Ruff complexity
  violations and from 61 to 60 oversized modules. `roboclaws/maps/bundle.py`
  is no longer oversized, and the `validate_nav2_map_bundle` C901, PLR0912,
  and PLR0915 rows were removed from the baseline.
- 2026-06-14: Implemented P1's highest-risk planner-proof bundle checker
  phase split. Added
  `scripts/molmo_cleanup/planner_proof_bundle_selection_checker.py` for proof
  request selection, request filtering, feasibility blockers, fallback
  generation, and selection requirement checks. Added
  `scripts/molmo_cleanup/planner_proof_bundle_result_checker.py` for proof
  result summary, prior proof summary, proof quality, grasp signature matrix,
  worker stage, sampler adapter, robot placement, and view-source checks. The
  main checker still owns CLI parsing, manifest core assertions, report
  rendering, runtime preflight, warmup, command, and cleanup-rerun gates; the
  remaining six checker complexity rows are smaller follow-up candidates, not
  part of this phase split. Evidence:
  `ruff check scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py scripts/molmo_cleanup/planner_proof_bundle_selection_checker.py scripts/molmo_cleanup/planner_proof_bundle_result_checker.py`
  passed; `ruff format` for the same touched files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_planner_proof_bundle_runner_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 204 to 198 Ruff complexity
  violations and from 60 to 59 oversized modules. The checker file dropped
  from 12 to 6 grouped complexity rows, and the `_assert_proof_request_selection`
  plus `_assert_proof_result_summary` PLR0915 rows were removed from the main
  checker baseline.
- 2026-06-14: Implemented P2's planner manipulation probe checker split.
  Added `scripts/molmo_cleanup/planner_manipulation_probe_checker.py` for
  artifact/report core checks, runtime diagnostics, task-sampler failure
  diagnostics, cleanup binding report assertions, required capability gates,
  proof quality, RBY1M CuRobo gate checks, and final blocked/planner-backed
  status checks. `check_molmo_planner_manipulation_probe.py` keeps the CLI and
  the direct `_assert_probe_result(...)` test hook as a thin delegate. Evidence:
  `ruff check scripts/molmo_cleanup/check_molmo_planner_manipulation_probe.py scripts/molmo_cleanup/planner_manipulation_probe_checker.py`
  passed; `ruff format` for the same touched files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_planner_manipulation_probe.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 198 to 195 Ruff complexity
  violations, with oversized modules unchanged at 59. The previous top
  individual complexity row,
  `check_molmo_planner_manipulation_probe.py::_assert_probe_result` PLR0915
  140>50, was removed from the baseline. The runtime worker/probe script
  remains a separate P3 candidate.
- 2026-06-14: Started P3 with the parent-process result packaging split.
  Added `scripts/molmo_cleanup/planner_manipulation_probe_result.py` for
  worker stdout event parsing, worker returncode/blocker normalization,
  manipulation evidence assembly, RBY1M CuRobo gate attachment, shared report
  rendering, and `run_result.json` writing. The public runner keeps its CLI,
  worker path, and existing private test hook names as imported delegates, so
  current `just harness::molmo-planner-manipulation-probe` and direct checker
  tests keep the same behavior. Evidence:
  `ruff check scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py scripts/molmo_cleanup/planner_manipulation_probe_result.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_planner_manipulation_probe.py tests/unit/molmo_cleanup/test_molmo_planner_headless_renderer.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 195 to 192 Ruff complexity
  violations, with oversized modules unchanged at 59. The runner file dropped
  from 3014 to 2798 lines, and `_write_probe_result` C901, PLR0912, and
  PLR0915 rows were removed from the baseline. Remaining P3 work is the
  worker-runtime side: task-sampler adapters, runtime diagnostics, and
  worker invocation.
- 2026-06-14: Continued P3 by splitting the task-sampler failure diagnostics
  hook installer inside `run_molmo_planner_manipulation_probe.py`. The
  monolithic `_apply_task_sampler_failure_diagnostics_adapter(...)` now
  delegates to focused robot-placement, asset-failure, grasp-collision,
  grasp-failure, and candidate-removal hook installers, while preserving the
  exact diagnostics payload shape and private test hooks. Evidence:
  `ruff check scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py`
  passed; `ruff format --check` for the same file passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_planner_manipulation_probe.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 192 to 190 Ruff complexity
  violations, with oversized modules unchanged at 59. The runner's grouped
  complexity rows dropped from 5 to 3; remaining P3 runtime work is
  `_execute_policy_probe(...)`, exact cleanup-task configuration, and worker
  invocation/runtime diagnostics.
- 2026-06-14: Continued P3 by splitting `_execute_policy_probe(...)` into
  ordered execute-stage helpers: renderer preparation, task-sampler setup,
  task sampling/binding, policy execution, policy exception recording, and
  planner-view image artifact collection. The event names, exception context,
  cleanup binding payloads, and returned evidence keys are preserved. Evidence:
  `ruff check scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py`
  passed; `ruff format --check` for the same file passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_planner_manipulation_probe.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 190 to 189 Ruff complexity
  violations, with oversized modules unchanged at 59. The
  `_execute_policy_probe` PLR0915 row was removed from the baseline. Remaining
  P3 runner rows are small C901 entries for exact cleanup-task configuration
  and grasp-collision diagnostics; runtime diagnostics / worker invocation
  can be considered in a later loop if they still pass materiality after the
  broader checker/backend candidates are weighed.
- 2026-06-14: Continued the live cleanup checker split by extracting public
  agent-view and runtime-metric-map assertions into
  `scripts/molmo_cleanup/realworld_agent_view_checker.py`. The main checker
  keeps `_assert_public_agent_view(...)` and `_assert_runtime_metric_map(...)`
  as imported private aliases so direct checker tests and internal call sites
  keep the same entrypoints while the assertion details live in focused helper
  phases. Evidence:
  `ruff check scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py scripts/molmo_cleanup/realworld_agent_view_checker.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 189 to 184 Ruff complexity
  violations, with oversized modules unchanged at 59. The live cleanup checker
  grouped complexity count dropped from 14 to 9 violations, and the
  `_assert_public_agent_view` / `_assert_runtime_metric_map` rows were removed
  from the main checker baseline.
- 2026-06-14: Continued P1 by splitting the remaining planner-proof bundle
  runner checker core into
  `scripts/molmo_cleanup/planner_proof_bundle_runner_checker.py`. The CLI
  script now keeps `main(...)` plus the `_assert_runner_result(...)` private
  test hook as an imported alias, while runner manifest core checks, proof
  execution horizon, local runtime preflight, warmup, grasp mitigation/cache
  preflights, proof summaries, probe commands, and cleanup rerun checks live in
  focused helper phases. Evidence:
  `ruff check scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py scripts/molmo_cleanup/planner_proof_bundle_runner_checker.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_planner_proof_bundle_runner_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 184 to 178 Ruff complexity
  violations, with oversized modules unchanged at 59. The remaining six
  grouped complexity rows for
  `check_molmo_planner_proof_bundle_runner_result.py` were removed from the
  baseline.
- 2026-06-14: Continued the live cleanup checker split by extracting waypoint
  honesty checks into
  `scripts/molmo_cleanup/realworld_waypoint_honesty_checker.py`. The main
  checker keeps `_assert_waypoint_honesty(...)` and
  `_post_place_observe_count_allowing_public_state_queries(...)` as private
  compatibility hooks for existing tests, while the helper owns public
  waypoint-source validation, scan-only worklist allowance, minimal/static
  cleanup-loop trace checks, and post-place observation accounting. Evidence:
  `ruff check scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py scripts/molmo_cleanup/realworld_waypoint_honesty_checker.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 178 to 175 Ruff complexity
  violations, with oversized modules unchanged at 59. The live cleanup checker
  grouped complexity count dropped from 9 to 6 violations, and the
  `_assert_waypoint_honesty` C901 / PLR0912 / PLR0915 rows were removed from
  the main checker baseline.
- 2026-06-14: Implemented C2.5 by extracting cleanup policy trace construction
  into `roboclaws/household/realworld_policy_trace.py`. The public
  `realworld_contract.cleanup_policy_trace_from_events(...)` entrypoint now
  delegates to a focused event accumulator and pure payload helpers while
  preserving `CLEANUP_POLICY_TRACE_SCHEMA` and existing trace fields. Evidence:
  `ruff check roboclaws/household/realworld_contract.py roboclaws/household/realworld_policy_trace.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
  passed; `ruff format --check roboclaws/household/realworld_contract.py roboclaws/household/realworld_policy_trace.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 175 to 172 Ruff complexity
  violations, with oversized modules unchanged at 59. The
  `cleanup_policy_trace_from_events` C901 / PLR0912 / PLR0915 rows were removed
  from `roboclaws/household/realworld_contract.py`, and that module dropped
  from 6602 to 6424 lines at the time of the baseline refresh.
- 2026-06-14: Implemented C1.1 by extracting Agibot semantic-map build and
  minimal-map assertion families out of
  `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py` into
  `scripts/molmo_cleanup/realworld_agibot_map_build_checker.py` and
  `scripts/molmo_cleanup/realworld_minimal_map_checker.py`. The main checker
  keeps the private `_assert_agibot_semantic_map_build_result(...)` and
  `_assert_minimal_map(...)` hooks as imported aliases, and keeps
  `RUNTIME_METRIC_MAP_SCHEMA` as an explicit checker-module hook for existing
  contract tests. Evidence:
  `ruff check scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py scripts/molmo_cleanup/realworld_agibot_map_build_checker.py scripts/molmo_cleanup/realworld_minimal_map_checker.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 172 to 167 Ruff complexity
  violations, with oversized modules unchanged at 59. The live cleanup checker
  dropped from 2258 to 1914 lines, and the Agibot/minimal-map C901/PLR0912/
  PLR0915 rows were removed from the main checker baseline.
- 2026-06-14: Implemented B6 by centralizing MolmoSpaces worker command
  dispatch. The worker now uses a single state-command handler table for both
  one-shot CLI execution and persistent `serve` / `run_state_command(...)`
  requests, with state writeback controlled by one explicit mutating-command
  set. Pure argparse setup moved to
  `scripts/molmo_cleanup/molmospaces_worker_cli.py`, keeping MuJoCo/state
  behavior in `molmospaces_subprocess_worker.py`. Evidence:
  `ruff check scripts/molmo_cleanup/molmospaces_subprocess_worker.py scripts/molmo_cleanup/molmospaces_worker_cli.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 167 to 162 Ruff complexity
  violations, with oversized modules unchanged at 59. The MolmoSpaces worker
  dropped from five grouped complexity rows to zero and from 4018 to 3996 lines
  in the oversized-module baseline.
- 2026-06-14: Implemented C1.55 by extracting the direct cleanup scan loop,
  policy selection, semantic-sweep camera schedule, minimal-map deferred
  cleanup pass, robot-view before/after recording, and direct done fallback
  into `roboclaws/household/realworld_direct_cleanup_loop.py`. The public
  `run_realworld_cleanup(...)` API and artifact finalization remain in
  `realworld_cleanup.py`; private cleanup helpers are injected through
  `DirectCleanupLoopHooks` to avoid a circular import while keeping the loop
  behavior explicit. Evidence:
  `ruff check roboclaws/household/realworld_cleanup.py roboclaws/household/realworld_direct_cleanup_loop.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 162 to 159 Ruff complexity
  violations, with oversized modules unchanged at 59.
  `run_realworld_cleanup` no longer has C901, PLR0912, or PLR0915 rows in the
  baseline, and `realworld_cleanup.py` dropped from 1159 to 1067 lines in the
  oversized-module baseline.
- 2026-06-14: Ran the post-C1.55 bounded reduce-entropy loop. Evidence:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs" --examples 10`;
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 80`;
  targeted probes across the accepted C3/P3/I1 checklist items, quality
  baseline rows, Isaac worker tests, and the report renderer section map. The
  current quality signal after C1.55 was 159 Ruff complexity violations and 59
  oversized modules. The materiality gate accepted the I1 Isaac camera-capture
  split as P1 because `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`
  remained the top in-plan backend hotspot with 14 grouped complexity rows and
  `_capture_isaac_lab_camera_views` carried C901, PLR0912, and PLR0915 85>50.
  C3 remains a useful P2 report-section follow-up, while the P3 planner-probe
  residual rows are parked as micro residuals unless bundled with a larger
  runtime-diagnostics slice.
- 2026-06-14: Continued I1 by extracting the Isaac robot-view camera capture
  pipeline into `scripts/isaac_lab_cleanup/isaac_camera_capture.py`. The worker
  keeps `_capture_isaac_lab_camera_views(...)` as a stable wrapper that passes
  worker-private USD/render helpers through `IsaacCameraCaptureHooks`, so Isaac
  imports still occur only inside the worker capture path and normal Roboclaws
  imports stay clean. Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_camera_capture.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 159 to 156 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 8685 to 8490 lines and from 14 to 11 grouped complexity rows; the
  `_capture_isaac_lab_camera_views` C901 / PLR0912 / PLR0915 rows were removed.
- 2026-06-14: Continued I1 by extracting the standalone Isaac scene-camera
  probe capture path into `scripts/isaac_lab_cleanup/isaac_scene_camera_capture.py`.
  The worker keeps `_capture_isaac_lab_scene_camera_views(...)` as the stable
  wrapper and passes the existing camera-control, USD-stage, RGB tensor, and
  native-render diagnostics helpers through `IsaacSceneCameraCaptureHooks`.
  Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_scene_camera_capture.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 156 to 155 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 8490 to 8391 lines and from 11 to 10 grouped complexity rows; the
  `_capture_isaac_lab_scene_camera_views` PLR0915 row was removed.
- 2026-06-14: Continued I1 by extracting Isaac worker CLI construction into
  `scripts/isaac_lab_cleanup/isaac_worker_cli.py` and replacing the worker
  `main(...)` branch ladder with an explicit state-command dispatch table. The
  public `isaac_lab_backend_worker.parse_args(...)` helper remains as a stable
  wrapper for existing tests and callers, and no Isaac runtime imports moved
  into the normal Roboclaws process. Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_worker_cli.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
  passed; `ruff format --check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_worker_cli.py`
  passed; `python -m py_compile scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_worker_cli.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 155 to 152 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 8391 to 8232 lines and from 10 to 7 grouped complexity rows; the
  `parse_args` PLR0915 and `main` C901/PLR0912 rows were removed.
- 2026-06-14: Continued I1 by extracting Isaac capture-quality renderer-setting
  mutation helpers into `scripts/isaac_lab_cleanup/isaac_capture_quality.py`.
  The worker keeps `_apply_isaac_capture_quality_overrides(...)` as the stable
  worker-local wrapper that binds Isaac setting path constants; restoration,
  requested-setting row construction, and JSON-safe setting serialization now
  live in the helper module. Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_capture_quality.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
  passed; `ruff format --check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_capture_quality.py`
  passed; `python -m py_compile scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_capture_quality.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 152 to 150 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 8232 to 8021 lines and from 7 to 5 grouped complexity rows; the
  `_apply_isaac_capture_quality_overrides` C901/PLR0912 rows were removed.
- 2026-06-14: Continued I1 by extracting USD xform translate authoring into
  `scripts/isaac_lab_cleanup/isaac_usd_xform.py`. The worker still exposes the
  `_set_usd_xform_translate` private hook via import for semantic-pose stage
  application tests while the helper owns existing translate op, typed
  translate op, added translate op, and XformCommonAPI fallbacks. Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_usd_xform.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
  passed; `ruff format --check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_usd_xform.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py::test_isaac_semantic_pose_stage_application_uses_exact_pose tests/unit/molmo_cleanup/test_isaac_lab_backend.py::test_isaac_semantic_pose_stage_application_converts_world_pose_to_parent_local tests/unit/molmo_cleanup/test_isaac_lab_backend.py::test_isaac_semantic_pose_stage_application_updates_existing_translate_op tests/unit/molmo_cleanup/test_isaac_lab_backend.py::test_isaac_semantic_pose_stage_application_blocks_parent_transform_failure tests/unit/molmo_cleanup/test_isaac_lab_backend.py::test_isaac_semantic_pose_stage_application_does_not_mark_partial_as_rendered -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 150 to 149 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 8021 to 7966 lines and from 5 to 4 grouped complexity rows; the
  `_set_usd_xform_translate` C901 row was removed.
- 2026-06-14: Continued I1 by extracting scene-index semantic-label
  application into `scripts/isaac_lab_cleanup/isaac_semantic_labels.py`. The
  worker keeps `_apply_scene_index_semantic_labels(...)` as the stable wrapper
  and passes its private `_semantic_label_target_prims` hook into the helper,
  preserving existing tests that monkeypatch target-prim resolution. Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_semantic_labels.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
  passed; `ruff format --check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_semantic_labels.py`
  passed; `python -m py_compile scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_semantic_labels.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 149 to 148 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 7966 to 7792 lines and from 4 to 3 grouped complexity rows; the
  `_apply_scene_index_semantic_labels` C901 row was removed.
- 2026-06-14: Continued I1 by extracting USD descendant support-surface union
  calculation into `scripts/isaac_lab_cleanup/isaac_support_surfaces.py`. The
  worker keeps `_usd_support_surface_union(...)` as the stable wrapper that
  binds the Isaac descendant/union source constants, while the helper owns
  broad-surface filtering, rectangle bounds, and union payload construction.
  Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_support_surfaces.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
  passed; `ruff format --check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_support_surfaces.py`
  passed; `python -m py_compile scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_support_surfaces.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 148 to 147 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 7792 to 7745 lines and from 3 to 2 grouped complexity rows; the
  `_usd_support_surface_union` C901 row was removed.
- 2026-06-14: Finished I1 by extracting semantic-pose robot-view rerender
  capture/state handling into
  `scripts/isaac_lab_cleanup/isaac_semantic_pose_robot_view.py`. The worker
  keeps `_real_semantic_pose_robot_view_images(...)` as the stable wrapper that
  injects the monkeypatchable `capture_semantic_pose_robot_views(...)`, required
  robot-view image check, provenance helper, and state writeback hook. Evidence:
  `ruff check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_semantic_pose_robot_view.py tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
  passed; `ruff format --check scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_semantic_pose_robot_view.py`
  passed; `python -m py_compile scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py scripts/isaac_lab_cleanup/isaac_semantic_pose_robot_view.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_isaac_lab_backend.py -q`
  passed with the existing Pillow deprecation warning from scene-camera image
  saving; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py::test_realworld_cleanup_demo_can_run_isaaclab_fake_backend -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 147 to 145 Ruff complexity
  violations, with oversized modules unchanged at 59. The Isaac worker dropped
  from 7745 to 7635 lines and from 2 to 0 grouped complexity rows; the
  `_real_semantic_pose_robot_view_images` C901 and PLR0915 rows were removed.
- 2026-06-14: Continued C3 by extracting robot-timeline action-evidence badge
  rendering into `roboclaws/household/report_sections_action.py`.
  `report.py` now imports `action_evidence_summary(...)` instead of carrying
  bbox, grounding, and primitive badge formatting inline. Evidence:
  `ruff check roboclaws/household/report.py roboclaws/household/report_sections_action.py tests/contract/reports/test_molmo_cleanup_report.py`
  passed; `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_action.py`
  passed; `python -m py_compile roboclaws/household/report.py roboclaws/household/report_sections_action.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_keeps_raw_fpv_scans_out_of_primary_robot_timeline tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_world_label_navigation_evidence -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 145 to 143 Ruff complexity
  violations, with oversized modules unchanged at 59. `report.py` dropped from
  7889 to 7838 lines and from 3 to 1 grouped complexity row; the
  `_action_evidence_summary` C901/PLR0912 rows were removed.
- 2026-06-14: Continued C3 by extracting grasp-cache availability and
  generation preflight rendering into
  `roboclaws/household/report_sections_grasp_cache.py`. `report.py` now imports
  `grasp_cache_availability_preflight_section(...)` and
  `grasp_cache_generation_preflight_section(...)` instead of carrying the
  asset, loader-probe, object-probe, generation-check, and blocker tables
  inline. Evidence:
  `ruff check roboclaws/household/report.py roboclaws/household/report_sections_grasp_cache.py tests/contract/reports/test_molmo_cleanup_report.py`
  passed; `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_grasp_cache.py`
  passed; `python -m py_compile roboclaws/household/report.py roboclaws/household/report_sections_grasp_cache.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline was deliberately lowered from 143 to 142 Ruff complexity
  violations, with oversized modules unchanged at 59. `report.py` dropped from
  7838 to 7637 lines and from 1 to 0 grouped complexity rows; the
  `_grasp_cache_availability_preflight_section` C901 row was removed.
- 2026-06-14: Continued C3 by extracting light proof-bundle runner report
  sections into `roboclaws/household/report_sections_proof_bundle.py`.
  `report.py` now imports command, proof-execution horizon, grasp-mitigation
  decision, local-runtime preflight, warmup, cleanup-rerun command, and
  cleanup-rerun artifact renderers instead of carrying those tables inline.
  Selection/results tables remain in `report.py` for a separate proof-results
  slice. Evidence:
  `ruff check roboclaws/household/report.py roboclaws/household/report_sections_proof_bundle.py tests/contract/reports/test_molmo_cleanup_report.py`
  passed; `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_proof_bundle.py`
  passed; `python -m py_compile roboclaws/household/report.py roboclaws/household/report_sections_proof_bundle.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline stayed at 142 Ruff complexity violations and 59 oversized
  modules, while `report.py` dropped from 7637 to 7351 lines.
- 2026-06-14: Continued C3 by extracting Agent View, runtime metric map,
  cleanup worklist, skill scratchpad, cleanup policy trace, and real-robot
  readiness rendering into `roboclaws/household/report_sections_agent.py`.
  `report.py` now imports `agent_view_section(...)`,
  `cleanup_policy_trace_section(...)`, and
  `real_robot_readiness_section(...)` instead of carrying those public
  evidence tables inline. Evidence:
  `ruff check roboclaws/household/report.py roboclaws/household/report_sections_agent.py tests/contract/reports/test_molmo_cleanup_report.py`
  passed; `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_agent.py`
  passed; `python -m py_compile roboclaws/household/report.py roboclaws/household/report_sections_agent.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline stayed at 142 Ruff complexity violations and 59 oversized
  modules, while `report.py` dropped from 7351 to 6930 lines.
- 2026-06-14: Implemented B7 by routing non-Agibot live MCP server setup and
  MCP smoke setup through the shared cleanup backend facade.
  `roboclaws/cli/household_agent_server.py` and
  `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py` now use
  `build_cleanup_backend_session(...)` plus shared run-option validation instead
  of constructing MolmoSpaces / Isaac Lab / synthetic backend sessions inline.
  Agibot GDK setup remains behind `AgibotCleanupMCPContract` as a separate
  adapter-family exception. Evidence:
  `ruff check roboclaws/cli/household_agent_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py roboclaws/household/backend_contract.py`
  passed; `ruff format --check roboclaws/cli/household_agent_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py roboclaws/household/backend_contract.py`
  passed; `python -m py_compile roboclaws/cli/household_agent_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline remains 142 Ruff complexity violations and 59 oversized
  modules because this slice removed duplicated construction paths without
  lowering existing ratcheted rows.
- 2026-06-14: Continued C3 by extracting Robot View Timeline rendering into
  `roboclaws/household/report_sections_robot.py`. The new module owns
  visual-core step filtering, static/refreshed Isaac provenance badges,
  camera-contract badges, FPV bbox verification image writing, observe-role
  badges, focus/visibility badges, and robot-step cards. `report.py` keeps the
  shared HTML wrapper, image-link renderer, and report asset path resolver, and
  passes those shared helpers into the robot section. Evidence:
  `ruff check roboclaws/household/report.py roboclaws/household/report_sections_robot.py tests/contract/reports/test_molmo_cleanup_report.py`
  passed; `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_robot.py`
  passed; `python -m py_compile roboclaws/household/report.py roboclaws/household/report_sections_robot.py`
  passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_robot_visual_timeline tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_marks_refreshed_isaac_semantic_pose_views tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_labels_observe_roles_and_zero_pixel_focus tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_raw_fpv_observations tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_keeps_raw_fpv_scans_out_of_primary_robot_timeline -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline remains 142 Ruff complexity violations and 59 oversized
  modules; `report.py` dropped from 6930 to 6558 lines.
- 2026-06-14: Ran the post-robot reduce-entropy saturation check. Evidence:
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 30`
  passed and reported 142 Ruff complexity violations plus 59 oversized
  modules; `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs" --examples 5`
  bounded high-noise surfaces; the materiality gate accepted six remaining
  candidates and rejected none. The loop is not saturated yet: current P1
  directions are proof result report extraction, scene-camera comparison
  pipeline splitting, OpenAI Agents live runtime boundary cleanup, and operator
  console readiness/routing cleanup. Visual-grounding contract/adapters and
  apple2apple diagnostics remain material P2 directions.
- 2026-06-14: Closed C3 by extracting cleanup proof-tab rendering into
  `roboclaws/household/report_sections_proof.py`. The new module owns
  manipulation provenance, attached planner proof(s), cleanup primitive gate,
  planner cleanup bridge, and planner proof request sections. `report.py` keeps
  planner-probe and proof-bundle runner result renderers because they are
  separate report families, not part of the cleanup proof-tab slice. Evidence:
  `ruff check roboclaws/household/report.py roboclaws/household/report_sections_proof.py tests/contract/reports/test_molmo_cleanup_report.py`
  passed; `ruff format --check roboclaws/household/report.py roboclaws/household/report_sections_proof.py`
  passed; `python -m py_compile roboclaws/household/report.py roboclaws/household/report_sections_proof.py`
  passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_planner_proof_requests_before_agent_view tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof tests/contract/reports/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof_bundle -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed. The
  quality baseline remains 142 Ruff complexity violations and 59 oversized
  modules; `report.py` dropped from 6558 to 6195 lines.
- 2026-06-14: Ran the post-proof reduce-entropy saturation check. Evidence:
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 20`
  passed and reported 142 Ruff complexity violations plus 59 oversized
  modules; the materiality gate accepted five remaining candidates and rejected
  none. C3 is complete for currently material cleanup-report families. The loop
  is still not saturated because P1 workflow friction remains in scene-camera
  comparison, live OpenAI Agents runtime, and operator-console readiness/routing.
- 2026-06-14: Continued the scene-camera pipeline candidate by extracting report
  manifest hydration into `roboclaws/household/scene_camera_report_hydration.py`.
  Both the full comparison run and the report-only renderer now use one ordered
  hydration helper for candidate visual, projection, room-wall/light,
  render-domain, lighting, shadow, and backend-swap diagnostics. Evidence:
  `ruff check roboclaws/household/scene_camera_comparison.py roboclaws/household/scene_camera_report_hydration.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py`
  passed; `ruff format --check roboclaws/household/scene_camera_comparison.py roboclaws/household/scene_camera_report_hydration.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py`
  passed; `python -m py_compile roboclaws/household/scene_camera_comparison.py roboclaws/household/scene_camera_report_hydration.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_scene_camera_comparison.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 142 to
  140 Ruff complexity violations, with oversized modules unchanged at 59.
  `scene_camera_comparison.py` dropped from 6796 to 6781 lines and from eight
  to six grouped complexity rows; the
  `render_scene_camera_comparison_report` C901 and
  `run_scene_camera_comparison` PLR0915 rows were removed.
- 2026-06-14: Ran the post-scene-camera hydration reduce-entropy saturation
  check. Evidence:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs" --examples 5`;
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 30`;
  and the materiality gate over the current candidate packet. The gate accepted
  five remaining candidates and rejected none: scene-camera render diagnostics,
  OpenAI Agents live runtime boundary, operator-console readiness/routing,
  visual-grounding contract validation, and apple2apple parity diagnostics.
  The loop is not saturated yet, but the completed report hydration path is now
  parked unless future report-only behavior changes.
- 2026-06-14: Completed the scene-camera render diagnostics split by adding
  `roboclaws/household/scene_camera_render_diagnostics.py` for room-scale
  contract assembly, USD prim path lookup, MuJoCo XML render-contract parsing,
  source-snippet selection, float-list parsing, and vector normalization.
  `scene_camera_comparison.py` keeps the existing private helper names as thin
  imported delegates so contract tests and apple2apple imports remain stable,
  while the parsing/diagnostic implementation is split into low-complexity
  helpers. Evidence:
  `ruff check roboclaws/household/scene_camera_comparison.py roboclaws/household/scene_camera_render_diagnostics.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
  passed; `ruff format --check roboclaws/household/scene_camera_comparison.py roboclaws/household/scene_camera_render_diagnostics.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
  passed; `python -m py_compile roboclaws/household/scene_camera_comparison.py roboclaws/household/scene_camera_render_diagnostics.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_scene_camera_comparison.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 140 to
  134 Ruff complexity violations, with oversized modules unchanged at 59.
  `scene_camera_comparison.py` dropped from 6781 to 6480 lines and no longer
  appears in the complexity-by-file summary; the six remaining scene-camera
  grouped complexity rows were removed.
- 2026-06-14: Ran the post-scene-camera render split saturation check. Evidence:
  `python scripts/dev/check_python_quality_ratchet.py --summary --top 20` and
  the materiality gate over the current candidate packet. The gate accepted
  four remaining candidates and rejected none: OpenAI Agents live runtime
  boundary, operator-console readiness/routing, visual-grounding contract
  validation, and apple2apple parity diagnostics. The loop is not saturated
  yet, but scene-camera comparison itself is parked unless future visual parity
  work needs behavior changes beyond the extracted helper boundary.
- 2026-06-14: Continued the OpenAI Agents live runtime boundary candidate by
  extracting model-service fallback, model-racing observability, and model-input
  filter metrics aggregation from
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` into
  `scripts/molmo_cleanup/openai_agents_metrics.py`. The runner keeps the
  existing private `_model_*_metrics` names as import aliases so current tests
  and report-performance callers keep the same payload shape, while the JSONL
  event parsing and aggregate state updates now live in a focused helper
  module. Evidence:
  `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/openai_agents_metrics.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
  passed; `ruff format --check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/openai_agents_metrics.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 134 to
  129 Ruff complexity violations, with oversized modules unchanged at 59.
  `run_live_openai_agents_cleanup.py` dropped from 3701 to 3297 lines and from
  seven to two grouped complexity rows. The remaining OpenAI Agents rows are
  `_run_sdk_agent` and `_raw_fpv_budget_failure`; treat them as residual
  lifecycle/budget-policy cleanup, not part of the completed metrics split.
- 2026-06-14: Continued the operator-console readiness/routing candidate by
  splitting `ConsoleRequestHandler.do_GET` and `do_POST` into explicit static
  file, JSON API, artifact file, exact POST, run-action POST, readiness-query,
  launch-payload, and follow-up autostart helpers inside
  `roboclaws/operator_console/server.py`. This keeps the HTTP endpoint payloads
  and the stdlib server boundary unchanged while removing the branch ladders
  from the request handler entrypoints. Evidence:
  `ruff check roboclaws/operator_console/server.py tests/unit/operator_console/test_operator_console.py tests/unit/operator_console/test_launcher.py`
  passed; `ruff format --check roboclaws/operator_console/server.py tests/unit/operator_console/test_operator_console.py tests/unit/operator_console/test_launcher.py`
  passed; `ruff check roboclaws/operator_console/server.py --select C901,PLR0912,PLR0915`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 129 to
  124 Ruff complexity violations, with oversized modules unchanged at 59.
  `roboclaws/operator_console/server.py` no longer appears in the
  complexity-by-file summary; the operator-console readiness candidate remains
  open for `route_readiness(...)` and adjacent route/state helpers.
- 2026-06-14: Continued the operator-console readiness/routing candidate by
  extracting readiness gate evaluation into
  `roboclaws/operator_console/readiness.py`. The new module owns provider-key,
  Isaac preflight, MCP port, request-field, and operator real-movement gate row
  evaluation; `roboclaws/operator_console/launcher.py` keeps the public
  `route_readiness(...)` function and lock/provider orchestration so existing
  imports and API payloads remain stable. Evidence:
  `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/readiness.py tests/unit/operator_console/test_launcher.py tests/unit/operator_console/test_operator_console.py`
  passed; `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/readiness.py tests/unit/operator_console/test_launcher.py tests/unit/operator_console/test_operator_console.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
  passed; `python -m py_compile roboclaws/operator_console/launcher.py roboclaws/operator_console/readiness.py`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 124 to
  121 Ruff complexity violations, with oversized modules unchanged at 59.
  `route_readiness(...)` no longer appears in the quality summary; `launcher.py`
  keeps three residual C901 rows for `build_launch_argv(...)`,
  `_validate_env_overrides(...)`, and `_docker_container_ids_with_mount(...)`.
- 2026-06-14: Continued the visual-grounding contract candidate by extracting
  request/response schema validation into
  `roboclaws/household/visual_grounding_contract.py`. The HTTP client module
  keeps the public schema constants, `VisualGroundingContractError`, and
  validator names as imported exports, while base64 validation, request image
  checks, pipeline/stage checks, candidate region validation, and numeric list
  validation now live in the focused contract module. Evidence:
  `ruff check roboclaws/household/visual_grounding.py roboclaws/household/visual_grounding_contract.py scripts/visual_grounding/adapters.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_service.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
  passed; `ruff format --check roboclaws/household/visual_grounding.py roboclaws/household/visual_grounding_contract.py scripts/visual_grounding/adapters.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_service.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
  passed; `python -m py_compile roboclaws/household/visual_grounding.py roboclaws/household/visual_grounding_contract.py`
  passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_service.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 121 to
  116 Ruff complexity violations, with oversized modules unchanged at 59.
  The request/response/candidate validation rows were removed from
  `visual_grounding.py`; the remaining visual-grounding rows are
  `HttpVisualGroundingClient.request_candidates(...)` and
  `scripts/visual_grounding/adapters.py::_yolo_candidates_from_model(...)`.
- 2026-06-14: Continued backend/server consistency cleanup by splitting the
  household MCP agent-server setup and lifecycle path in
  `roboclaws/cli/household_agent_server.py`. Backend preparation now has
  named generic-facade and Agibot-specific setup helpers, and server
  start/wait/error/finalize handling is isolated from public CLI option
  orchestration. The public
  `run_molmo_realworld_cleanup_agent_server(...)` signature, CLI flags,
  result fields, Agibot contract setup, and cleanup backend facade behavior are
  unchanged. Evidence:
  `ruff check roboclaws/cli/household_agent_server.py --select C901,PLR0912,PLR0915`
  passed; `ruff check roboclaws/cli/household_agent_server.py tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
  passed; `ruff format --check roboclaws/cli/household_agent_server.py tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
  passed; `python -m py_compile roboclaws/cli/household_agent_server.py`
  passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
  passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 116 to
  113 Ruff complexity violations, with oversized modules unchanged at 59.
  `roboclaws/cli/household_agent_server.py` no longer appears in the
  complexity-by-file summary.
- 2026-06-14: Continued the operator-console residual launch/state candidate by
  extracting route launch argument assembly, provider env override validation,
  and Docker workspace mount inspection from
  `roboclaws/operator_console/launcher.py`. Provider override and Docker mount
  details now live in `roboclaws/operator_console/launch_support.py`, while
  `launcher.py` keeps the existing API-facing wrappers and the same
  `ConsoleLaunchError` surface. Evidence:
  `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/launch_support.py --select C901,PLR0912,PLR0915`
  passed; `ruff check roboclaws/operator_console/launcher.py roboclaws/operator_console/launch_support.py tests/unit/operator_console/test_launcher.py tests/unit/operator_console/test_operator_console.py tests/unit/operator_console/test_state.py`
  passed; `ruff format --check roboclaws/operator_console/launcher.py roboclaws/operator_console/launch_support.py tests/unit/operator_console/test_launcher.py tests/unit/operator_console/test_operator_console.py tests/unit/operator_console/test_state.py`
  passed; `python -m py_compile roboclaws/operator_console/launcher.py roboclaws/operator_console/launch_support.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 113 to
  110 Ruff complexity violations, with oversized modules unchanged at 59.
  `roboclaws/operator_console/launcher.py` no longer appears in the
  complexity-by-file summary; the remaining operator-console grouped rows are
  in `roboclaws/operator_console/state.py`.
- 2026-06-14: Completed the currently material operator-console state residual
  split by moving camera-angle trace summarization and run-result success /
  failure predicates into `roboclaws/operator_console/state_summary.py`.
  `state.py` keeps compatibility wrappers for the existing private helper
  names while the branch-heavy parsing and status logic lives in a focused
  state-summary module. Evidence:
  `ruff check roboclaws/operator_console/state.py roboclaws/operator_console/state_summary.py --select C901,PLR0912,PLR0915`
  passed; `ruff check roboclaws/operator_console/state.py roboclaws/operator_console/state_summary.py tests/unit/operator_console/test_state.py tests/unit/operator_console/test_static_assets.py tests/unit/operator_console/test_operator_console.py`
  passed; `ruff format --check roboclaws/operator_console/state.py roboclaws/operator_console/state_summary.py tests/unit/operator_console/test_state.py tests/unit/operator_console/test_static_assets.py tests/unit/operator_console/test_operator_console.py`
  passed; `python -m py_compile roboclaws/operator_console/state.py roboclaws/operator_console/state_summary.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 110 to
  106 Ruff complexity violations, with oversized modules unchanged at 59.
  `roboclaws/operator_console/state.py` no longer appears in the
  complexity-by-file summary.
- 2026-06-14: Began implementing the parked Candidate A robot-camera parity
  diagnostics packet by extracting the visual-parity default/report-side gate
  logic from `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
  into `scripts/molmo_cleanup/robot_camera_visual_parity_gates.py`. The
  summary runner still produces the same manifest fields for
  `prepared_scale_square_default_gate`,
  `combined_material_light_default_gate`, and
  `view_specific_prepared_scale_square_tone_gate`, while the probe selection,
  blocker assembly, status decisions, chase-regression diagnostics, and
  view-specific RGB-gain checks now live in focused helpers. Evidence:
  `ruff check scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py scripts/molmo_cleanup/robot_camera_visual_parity_gates.py tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py -q`
  passed with 25 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 106 to 101 Ruff complexity violations, with oversized modules unchanged
  at 59. `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
  dropped from 3381 to 2808 lines and no longer appears in the
  complexity-by-file summary.
- 2026-06-14: Continued Candidate B backend command-layer catalog adoption by
  adding launch-catalog helpers in `roboclaws/launch/backends.py` for cleanup
  and map-build Codex implementation backend choices. `just/molmo.just` now
  validates private cleanup backend overrides through
  `python -m roboclaws.launch.backends cleanup-implementation-backend`, and
  `just/agent.just` uses the same catalog module for the
  household-world.map-build Codex backend gate. This removes the first
  duplicated command-layer backend allowlists while keeping public
  `backend=mujoco|isaaclab|agibot-gdk` lowering and Agibot-specific execution
  behavior unchanged. Evidence:
  `ruff check roboclaws/launch/backends.py tests/unit/launch/test_environment_setup_catalog.py tests/contract/dev_tools/test_backend_catalog_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_environment_setup_catalog.py tests/contract/dev_tools/test_backend_catalog_just_recipes.py -q`
  passed with 15 tests;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed with 101
  Ruff complexity violations and 59 oversized modules.
- 2026-06-14: Continued Candidate A apple-to-apple parity diagnostics by
  extracting material-response, tone/color probe-history, texture colorspace,
  and USD PreviewSurface material-model diagnostics into
  `scripts/molmo_cleanup/robot_camera_apple2apple_materials.py`.
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` keeps the
  existing private helper names as thin compatibility wrappers for current
  tests and report assembly, while the branch-heavy payload assembly now lives
  in the focused helper module. Evidence:
  `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py scripts/molmo_cleanup/robot_camera_apple2apple_materials.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
  passed with 39 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 101 to 97 Ruff complexity violations, with oversized modules unchanged
  at 59. The apple-to-apple runner dropped from 5844 to 5332 lines and from
  six to two grouped complexity rows; the remaining rows are
  `run_comparison(...)` and `_object_gate_classification(...)`.
- 2026-06-14: Continued Candidate A apple-to-apple parity diagnostics by
  extracting object-gate classification and protected visual-physics RGB /
  coverage / target-visual-state checks into
  `scripts/molmo_cleanup/robot_camera_apple2apple_object_gate.py`.
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` keeps the
  existing private helper names as thin wrappers for current tests and report
  assembly, while the visual-physics protection token is shared from the
  helper to avoid future policy-string drift. Evidence:
  `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py scripts/molmo_cleanup/robot_camera_apple2apple_object_gate.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
  passed with 39 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 97 to 96 Ruff complexity violations, with oversized modules unchanged
  at 59. The apple-to-apple runner dropped from 5332 to 5279 lines and now has
  one remaining grouped complexity row: `run_comparison(...)`.
- 2026-06-14: Continued the OpenAI Agents residual runtime boundary candidate
  by extracting RAW-FPV budget-guard trace parsing, repeated-failure
  fingerprinting, candidate/observe budget reason selection, and terminal
  `LiveAgentFailure` construction into
  `scripts/molmo_cleanup/openai_agents_budget.py`.
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` keeps the existing
  `_raw_fpv_budget_failure` private name as an imported delegate so current
  budget-guard tests and runner code keep the same entrypoint. Evidence:
  `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/openai_agents_budget.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py::test_openai_agents_budget_guard_classifies_raw_fpv_candidate_exhaustion tests/unit/agents/test_live_runtime.py::test_openai_agents_budget_guard_classifies_repeated_raw_fpv_failures tests/unit/agents/test_live_runtime.py::test_openai_agents_budget_guard_uses_current_context_not_cumulative_tokens -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
  passed with 71 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 96 to 95 Ruff complexity violations, with oversized modules unchanged
  at 59. The remaining OpenAI Agents residual rows are runner lifecycle
  `_run_sdk_agent(...)` and the SDK adapter rows `_run_openai_agents(...)`,
  `_camera_grounded_history_info(...)`, and
  `_unwrap_mcp_text_content_payload(...)`.
- 2026-06-14: Completed the runner-local part of the OpenAI Agents residual
  runtime boundary by extracting the pre/post-attempt budget guard raise path
  from `LiveOpenAIAgentsCleanupRunner._run_sdk_agent(...)` into a focused
  class helper. The error message, `agent_sdk_budget_terminal` status field,
  and `LiveAgentRunFailure` surface remain unchanged, while the SDK attempt
  loop now reads as request/run/result/continuation orchestration. Evidence:
  `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/openai_agents_budget.py --select C901,PLR0912,PLR0915,I,F`
  passed; `ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/openai_agents_budget.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
  passed; `ruff format --check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/openai_agents_budget.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
  passed with 71 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 95 to 94 Ruff complexity violations, with oversized modules unchanged
  at 59. `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` no longer
  appears in the complexity-by-file summary. The remaining Candidate A work is
  now limited to SDK adapter rows in
  `roboclaws/agents/drivers/openai_agents_live.py`.
- 2026-06-14: Continued the SDK-adapter part of the OpenAI Agents residual
  runtime boundary by splitting MCP text-content payload unwrapping and
  camera-grounded history tool/eligibility classification inside
  `roboclaws/agents/drivers/openai_agents_live.py`. The recursive MCP
  text-content unwrap semantics, camera-grounded history compaction payloads,
  and model-input filter behavior are unchanged; the parser and history
  classifier now route through focused helpers. Evidence:
  `ruff check roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py::test_model_input_compaction_summarizes_wrapped_mcp_camera_grounded_history tests/unit/agents/test_live_runtime.py::test_model_input_compaction_summarizes_prefixed_mcp_camera_grounded_history tests/unit/agents/test_live_runtime.py::test_model_input_compaction_summarizes_function_call_camera_history_by_call_id -q`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
  passed with 71 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 94 to 92 Ruff complexity violations, with oversized modules unchanged
  at 59. The remaining OpenAI Agents Candidate A row is
  `roboclaws/agents/drivers/openai_agents_live.py::_run_openai_agents(...)`.
- 2026-06-14: Completed Candidate A by extracting OpenAI Agents SDK setup into
  focused run-part, MCP server kwargs, and agent kwargs helpers inside
  `roboclaws/agents/drivers/openai_agents_live.py`. `_run_openai_agents(...)`
  now owns SDK imports, trace processor registration, run dispatch, and trace
  flush/shutdown, while model/run/server/agent setup and skill-context summary
  writing are isolated. Evidence:
  `ruff check roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py -q`
  passed with 71 tests; `ruff check roboclaws/agents/drivers/openai_agents_live.py --select C901,PLR0912,PLR0915`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 92 to
  91 Ruff complexity violations, with oversized modules unchanged at 59.
  `roboclaws/agents/drivers/openai_agents_live.py` no longer appears in the
  complexity-by-file summary, so the OpenAI Agents residual runtime boundary is
  complete for this loop.
- 2026-06-14: Completed Candidate B by moving RAW-FPV perception probe scoring
  into `scripts/molmo_cleanup/raw_fpv_perception_scoring.py`.
  `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py::score_variant(...)`
  is now a thin wrapper around the scoring accumulator, while hidden-target
  recovery, visible-movable label quality, duplicate accounting, schema
  failures, and live-like threshold assembly live in the focused module.
  Evidence:
  `ruff check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py scripts/molmo_cleanup/raw_fpv_perception_scoring.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
  passed; `ruff format --check` for the same files passed;
  `ruff check scripts/molmo_cleanup/run_raw_fpv_perception_probe.py scripts/molmo_cleanup/raw_fpv_perception_scoring.py --select C901,PLR0912,PLR0915`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py -q`
  passed with 21 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 91 to 88 Ruff complexity violations, with oversized modules unchanged
  at 59. The RAW-FPV probe scorer no longer appears in the complexity-by-file
  summary.
- 2026-06-14: Started Candidate C by splitting Agibot map-context validation
  and coordinate-bound collection inside
  `scripts/agibot/generate_metric_map_from_context.py`, and by advancing the
  `vendors/agibot_sdk` submodule to `910a76d` so the standalone SDK runner
  accepts the same minimal map-context contract as the main generator. Minimal
  Agibot contexts may carry public room labels and room-category hints while
  keeping fixtures, authored inspection waypoints, GDK map-source evidence, and
  navigation-check payloads out of the agent-facing view. Evidence:
  `ruff check scripts/agibot/generate_metric_map_from_context.py tests/contract/agibot/test_agibot_map_context_scripts.py`
  passed; `ruff format --check` for the same files passed;
  `ruff check vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py` passed in
  the submodule; `ruff format --check vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py`
  passed in the submodule;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/agibot/test_agibot_map_context_scripts.py -q`
  passed with 19 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 88 to 85 Ruff complexity violations, with oversized modules unchanged
  at 59. `scripts/agibot/generate_metric_map_from_context.py` no longer appears
  in the complexity-by-file summary. Remaining Candidate C work is limited to
  Agibot contract rehearsal, Agibot map-build MCP tool registration, and
  planner-proof fallback rows.
- 2026-06-15: Continued Candidate C by moving Agibot map-build MCP public tool
  registration and dispatch into `roboclaws/household/agibot_map_build_mcp_tools.py`.
  `fixture_hints` is no longer a public Agibot map-build or shared cleanup MCP
  tool; historical map/report artifacts still carry fixture hints where
  compatibility needs them. The Agibot cleanup backend marker now implements
  the shared backend-session optional capability methods used by the MCP server.
  Evidence:
  `ruff check roboclaws/household/agibot_map_build_mcp_server.py roboclaws/household/agibot_map_build_mcp_tools.py roboclaws/household/agibot_cleanup_contract.py tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_semantic_map_build_mcp_records_agent_driven_public_trace tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_adapter_integrates_with_shared_cleanup_mcp_contract -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline was lowered from 85 to
  83 Ruff complexity violations, with oversized modules unchanged at 59.
  Remaining Candidate C work is limited to Agibot contract rehearsal and
  planner-proof fallback rows.
- 2026-06-15: Continued Candidate C by aligning MolmoSpaces Agibot contract
  rehearsal with the current MCP boundary: `fixture_hints` remains a preflight
  artifact/context payload, but is no longer recorded as a public tool event or
  listed in the simulated runner task input's public tool sequence. Evidence:
  `ruff check roboclaws/household/agibot_contract_rehearsal.py tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py::test_molmospaces_agibot_contract_rehearsal_writes_simulated_report -q`
  passed; `python scripts/dev/check_python_quality_ratchet.py` passed after a
  deliberate baseline refresh. The quality baseline stayed at 83 Ruff
  complexity violations and 59 oversized modules, while
  `run_molmospaces_agibot_contract_rehearsal` dropped from 96 to 95 statements
  and the module dropped from 2359 to 2357 lines. Remaining Candidate C work is
  limited to broader Agibot contract rehearsal complexity and planner-proof
  fallback rows.
- 2026-06-15: Continued Candidate C by splitting MolmoSpaces Agibot contract
  rehearsal orchestration into `roboclaws/household/agibot_contract_rehearsal_stages.py`.
  `run_molmospaces_agibot_contract_rehearsal(...)` is now a thin public wrapper;
  validation, backend/session construction, preflight export, observe/navigation,
  blocked-manipulation versus cleanup-action execution, runtime export, and
  report/run-result finalization are named stage helpers. Evidence:
  `ruff check roboclaws/household/agibot_contract_rehearsal.py roboclaws/household/agibot_contract_rehearsal_stages.py tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py -q`
  passed with 4 tests and 2 skips; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 83 to 80 Ruff complexity violations, with oversized modules unchanged at
  59. `roboclaws/household/agibot_contract_rehearsal.py` dropped from 2357 to
  1996 lines and no longer appears in the complexity-by-file summary; the new
  stage helper module is 785 lines, below the oversized-module threshold.
  Remaining Candidate C work is limited to planner-proof fallback rows.
- 2026-06-15: Completed the remaining Candidate C planner-proof fallback rows
  by moving prior fallback alias discovery, carried-filter hydration, prior
  generated-result filtering, and helper parsers into
  `roboclaws/household/planner_proof_fallbacks.py`. The public
  `planner_proof_requests.py` APIs and proof request payloads are unchanged;
  the fallback module preserves prior evidence fields such as `last_worker_stage`
  and proof-quality summaries. Evidence:
  `ruff check roboclaws/household/planner_proof_requests.py roboclaws/household/planner_proof_fallbacks.py tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_molmo_planner_proof_requests.py -q`
  passed with 26 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 80 to 76 Ruff complexity violations, with oversized modules unchanged at
  59. `roboclaws/household/planner_proof_requests.py` dropped from 2187 to 1844
  lines and no longer appears in the complexity-by-file summary. Candidate C is
  complete for this backend-quality loop.
- 2026-06-15: Continued the visual-grounding benchmark residual candidate by
  moving benchmark scoring into `scripts/visual_grounding/benchmark_scoring.py`.
  `scripts/visual_grounding/run_visual_grounding_benchmark.py::_score_predictions`
  remains available as an imported delegate for current tests, while category
  matching, bbox IoU matching, destination-hint/actionability scoring,
  duplicate accounting, and private label detail assembly live in the focused
  helper. Evidence:
  `ruff check scripts/visual_grounding/run_visual_grounding_benchmark.py scripts/visual_grounding/benchmark_scoring.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
  passed; `ruff format --check` for the same files passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
  passed with 18 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 76 to 75 Ruff complexity violations, with oversized modules unchanged at
  59. `scripts/visual_grounding/run_visual_grounding_benchmark.py` dropped from
  1566 to 1253 lines and no longer appears in the complexity-by-file summary.
- 2026-06-15: Completed Candidate D by extracting default live MCP contract
  construction from `RealWorldMolmoCleanupMCPServer.__init__(...)` into
  `_build_realworld_mcp_contract(...)`. The public MCP server factory, server
  class, tool registration, visual-grounding setup, runtime-map prior handling,
  and acceptance-config payloads are unchanged; the constructor now leaves
  backend/session/default contract setup in one named helper. Evidence:
  `ruff check roboclaws/household/realworld_mcp_server.py roboclaws/household/realworld_mcp_run_artifacts.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
  passed; `ruff format --check` for the same files passed;
  `ruff check roboclaws/household/realworld_mcp_server.py --select C901,PLR0912,PLR0915`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
  passed with 26 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 75 to 74 Ruff complexity violations, with oversized modules unchanged at
  59. `RealWorldMolmoCleanupMCPServer.__init__` no longer appears in the
  complexity summary.
- 2026-06-15: Continued the robot-camera apple-to-apple parity residual by
  splitting `run_comparison(...)` setup into path, initial manifest, lane
  initialization, generated-mess summary, and blocked-manifest helpers. The
  MuJoCo and Isaac worker command arguments, canonical generated mess manifest,
  lane summaries, target-selection flow, per-location render loop, and report
  output schema remain unchanged. Evidence:
  `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
  passed; `ruff format --check` for the same files passed;
  `ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py --select C901,PLR0912,PLR0915`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py -q`
  passed with 39 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 74 to 73 Ruff complexity violations, with oversized modules unchanged at
  59. `run_comparison(...)` no longer appears in the complexity summary.
- 2026-06-15: Continued the detector-sidecar residual by splitting YOLO-family
  adapter runtime parsing in `scripts/visual_grounding/adapters.py`.
  `_yolo_candidates_from_model(...)` now delegates runtime-parameter to
  `predict_kwargs` translation and temporary-image model invocation to focused
  helpers, while candidate parsing and response schemas remain unchanged.
  Evidence:
  `ruff check scripts/visual_grounding/adapters.py roboclaws/household/visual_grounding.py scripts/visual_grounding/run_visual_grounding_benchmark.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py tests/contract/visual_grounding/test_visual_grounding_service.py`
  passed; `ruff format --check` for the same files passed;
  `ruff check scripts/visual_grounding/adapters.py --select C901,PLR0912,PLR0915`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_service.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
  passed with 33 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 73 to 72 Ruff complexity violations, with oversized modules unchanged at
  59. `scripts/visual_grounding/adapters.py` no longer appears in the
  complexity-by-file summary.
- 2026-06-15: Continued the detector-sidecar residual by splitting
  `HttpVisualGroundingClient.request_candidates(...)` transport handling in
  `roboclaws/household/visual_grounding.py`. Request URL/header construction,
  retry handling, timeout/connection failure responses, HTTP error JSON parsing,
  and response validation now live in focused helpers while the public client
  API and visual-grounding response contract remain unchanged. A focused test
  now covers HTTP non-2xx responses that still return a valid contract failure
  packet. Evidence:
  `ruff check --select C901,PLR0912,PLR0915 roboclaws/household/visual_grounding.py tests/unit/molmo_cleanup/test_visual_grounding.py`
  passed; `ruff format --check roboclaws/household/visual_grounding.py tests/unit/molmo_cleanup/test_visual_grounding.py`
  passed; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_service.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
  passed with 34 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 72 to 71 Ruff complexity violations, with oversized modules unchanged at
  59. `roboclaws/household/visual_grounding.py` no longer appears in the
  complexity-by-file summary.
- 2026-06-15: Continued the backend/engine consistency residual by making
  `roboclaws/launch/runners.py::export_env_from_overrides(...)` use the
  launch agent-engine catalog for provider-profile environment export.
  Provider env keys now come from `AgentEngineSpec.provider_env_key` instead of
  being repeated as local `codex-cli` / `claude-code` / `openai-agents-sdk`
  branches, while task metadata, goal contract, and scenario setup exports keep
  the same external shape. Evidence:
  `ruff check --select C901,PLR0912,PLR0915 roboclaws/launch/runners.py tests/unit/launch/test_environment_setup_catalog.py`
  passed; `ruff format --check roboclaws/launch/runners.py tests/unit/launch/test_environment_setup_catalog.py`
  passed; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/launch/test_environment_setup_catalog.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
  passed with 154 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 71 to 70 Ruff complexity violations, with oversized modules unchanged at
  59. `roboclaws/launch/runners.py` no longer appears in the complexity summary.
- 2026-06-15: Continued the backend-neutral generated-mess residual by splitting
  `roboclaws/household/generated_mess.py` target selection and manifest
  materialization helpers. Rule eligibility, round-robin target selection,
  manifest target-list validation, single-target materialization, receptacle id
  validation, relation validation, and placement-index validation are now named
  helpers while `select_generated_mess_targets(...)`,
  `build_generated_mess_manifest(...)`, and
  `targets_from_generated_mess_manifest(...)` keep the same public contracts.
  Evidence:
  `ruff check --select C901,PLR0912,PLR0915 roboclaws/household/generated_mess.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py`
  passed; `ruff format --check roboclaws/household/generated_mess.py` passed;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
  passed with 88 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 70 to 68 Ruff complexity violations, with oversized modules unchanged at
  59. `roboclaws/household/generated_mess.py` no longer appears in the
  complexity-by-file summary.
- 2026-06-15: Continued the target-query recovery residual by splitting
  `roboclaws/household/target_query.py::_required_next_tool(...)` into named
  next-tool policy helpers for actionable, destination-navigation, general
  actionable, and non-actionable candidates. The target-query resolution schema,
  required-next-tool strings, actionability priorities, and MCP recovery
  guidance remain unchanged. Evidence:
  `ruff check --select C901,PLR0912,PLR0915 roboclaws/household/target_query.py`
  passed; `ruff check roboclaws/household/target_query.py` passed;
  `ruff format --check roboclaws/household/target_query.py` passed;
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_target_query_recovery_resolves_stale_fixture_id_through_public_anchor tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_target_query_recovery_not_found_includes_public_search_budget tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_resolves_stale_target_query_to_public_anchor tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_rejects_skipped_semantic_pick_with_public_guidance`
  passed with 4 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 68 to 67 Ruff complexity violations, with oversized modules unchanged at
  59. A broader `ruff check --select C901,PLR0912,PLR0915` over the two
  contract test files still reports existing oversized test bodies unrelated to
  this slice.
- 2026-06-15: Continued the launch/backend context residual by splitting
  `roboclaws/launch/catalog.py::_overrides_with_surface_context(...)` into
  table-driven launch-only stripping and missing-context merge helpers. The
  public `run::surface` grammar, normalized surface/world/backend/agent-engine
  overrides, provider-profile export path, dispatch backend lowering, and
  scenario setup behavior remain unchanged. Evidence:
  `ruff check --select C901,PLR0912,PLR0915 roboclaws/launch/catalog.py`
  passed; `ruff check roboclaws/launch/catalog.py` passed;
  `ruff format --check roboclaws/launch/catalog.py tests/unit/launch/test_environment_setup_catalog.py tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/test_backend_catalog_just_recipes.py`
  passed; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/launch/test_environment_setup_catalog.py tests/contract/dev_tools/test_backend_catalog_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
  passed with 156 tests; `python scripts/dev/check_python_quality_ratchet.py`
  passed after a deliberate baseline refresh. The quality baseline was lowered
  from 67 to 66 Ruff complexity violations, with oversized modules unchanged at
  59. A broader `ruff check --select C901,PLR0912,PLR0915` over the launch
  tests still reports the existing `surface_args_from_legacy_task_args` helper
  complexity unrelated to this slice.
