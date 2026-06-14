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

- [ ] **C3: Split cleanup report sections from shared HTML wrapper.**
  - Target `roboclaws/household/report.py`.
  - Extract coherent report sections without rewriting visual output.
  - First extracted section modules:
    `roboclaws/household/report_sections_map.py` and
    `roboclaws/household/report_sections_timing.py`; action-evidence badges now
    live in `roboclaws/household/report_sections_action.py`; grasp-cache
    preflight sections now live in
    `roboclaws/household/report_sections_grasp_cache.py`.
  - Continue with proof/robot/agent report families only as separate verified
    slices; do not mix planner-probe report renderers into this cleanup-report
    slice.
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

- [ ] **R1: Continue reduce-entropy discovery after each completed group.**
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
  `roboclaws/household/report.py` (7637 lines, 0 complexity rows),
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

Materiality: `roboclaws/household/report.py` is still 7637 lines after map,
timing, action-evidence, and grasp-cache preflight extraction. It now has zero
grouped complexity rows, while proof, robot, agent, Agibot, and SDK runner
sections still share the same namespace.

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

## Parked Cross-Seam / Future Ideas

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
