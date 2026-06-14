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

- [x] **C1.5: Split direct cleanup orchestration from artifact/result assembly.**
  - Target `roboclaws/household/realworld_cleanup.py`.
  - Extract the post-loop artifact writer, run-result payload builder, profile
    metadata attachment, planner-proof attachment, and report/writeback stages
    from `run_realworld_cleanup`.
  - Keep public `run_result.json`, `agent_view.json`, `runtime_metric_map.json`,
    `private_evaluation.json`, `advisory_evaluation.json`, and `report.html`
    schemas stable.

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

- [ ] **C3: Split cleanup report sections from shared HTML wrapper.**
  - Target `roboclaws/household/report.py`.
  - Extract coherent report sections without rewriting visual output.
  - Keep `report.html` visual core tests green.

- [ ] **P1: Split planner-proof bundle checker assertion phases.**
  - Target `scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py`.
  - Extract staged checks for manifest/core counts, report rendering,
    local-runtime preflight, proof request selection, proof result summary,
    proof quality, grasp-cache mitigation, and cleanup rerun output.
  - Preserve CLI flags and current `just verify::molmo-planner-proof-*` /
    `just harness::molmo-planner-proof-*` behavior.

- [ ] **P2: Split planner manipulation probe runtime and result packaging.**
  - Target `scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` and
    `scripts/molmo_cleanup/check_molmo_planner_manipulation_probe.py`.
  - Extract runtime diagnostics, task-sampler adapters, worker invocation,
    result/report packaging, and checker proof-quality assertions.
  - Keep blocked-capability evidence valid by default; strict planner-backed
    proof remains a local-runtime gate.

- [ ] **M1: Split map bundle validation and snapshot contract checks.**
  - Target `roboclaws/maps/bundle.py` and
    `roboclaws/maps/actionable_snapshot.py`.
  - Turn `validate_nav2_map_bundle(...)` into an ordered validation pipeline
    for required files, YAML/PGM parsing, private-truth guards, semantic
    structure, waypoint reachability, fixture references, and route checks.
  - Keep `runtime_metric_map.json` and
    `actionable_semantic_map_snapshot.json` schemas stable.

- [ ] **I1: Split Isaac Lab worker backend details after facade stabilization.**
  - Target `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` and focused
    helper modules under `scripts/isaac_lab_cleanup/`.
  - Extract camera capture, scene-index scenario generation, semantic-pose
    stage mutation, segmentation diagnostics, and fake/real runtime packaging
    into modules that keep Isaac imports inside the worker process.
  - Treat this as a post-facade backend-internal cleanup; do not change normal
    Roboclaws process imports or require real Isaac Lab for default verification.

- [ ] **R1: Continue reduce-entropy discovery after each completed group.**
  - Run the bounded high-noise summary and the quality-debt summary.
  - Add only candidates that pass the materiality contract: false confidence,
    live source drift, stale surface, real workflow friction, or recurring
    rediscovery.
  - Mark saturation instead of inventing lower-value cleanup.

## Parked Cross-Seam / Future Ideas

- Test suite layout and fixture pruning are outside this plan unless a selected
  code slice requires a targeted test helper extraction. Route broad test-suite
  cleanup to `intuitive-tests`.
- Human docs cleanup is outside this plan unless public command or backend
  contract text changes. Route broad docs work to `intuitive-doc`.
- Real Isaac Lab simulator validation remains local/environment-sensitive.
  This plan can use fake Isaac worker tests by default and should record real
  simulator gates as skipped unless explicitly authorized.
- Agibot GDK backend parity can reuse the facade later, but this plan should
  first stabilize the current synthetic, MolmoSpaces, and Isaac Lab cleanup
  path.
- OpenAI Agents SDK runner cleanup is material but already covered by
  `docs/plans/2026-06-12-open-ended-household-default-architecture.md` and
  `docs/plans/refactor-coding-agent-provider-registry.md`. Do not duplicate it
  here unless a future loop finds SDK-specific drift outside those plans.
- Operator-console readiness/state splitting is material but already covered by
  `docs/plans/operator-console-orthogonal-launch-refactor.md` plus the recent
  legacy-route-wrapper removal. Do not count it again unless new route-gate
  drift appears.
- Scene-camera/render-parity, Agibot rehearsal/pilot, raw-FPV probe, and
  apple2apple comparison surfaces remain large and live, but current evidence
  points to their existing specialized plans rather than this backend-quality
  batch.

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
