---
plan_scope: base-waypoint-source-contract
status: IMPLEMENTED
created: 2026-06-19
last_reviewed: 2026-06-19
implemented: 2026-06-19
implementation_allowed: true
source:
  - waypoint source-of-truth discussion after canonical sim map bundle generation
  - intuitive-reduce-entropy plan entropy packet
  - grill-with-docs-batch accepted decision on 2026-06-19
related_context:
  - docs/human/domain.md
  - docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md
  - docs/plans/2026-06-17-sim-map-surface-simplification.md
  - docs/plans/molmospaces-waypoint-honest-cleanup-flow.md
---

# Base Waypoint Source Contract

## Problem

Canonical simulator map bundles now contain Base Navigation Map
`inspection_waypoints`, but the household runtime still has a second waypoint
projection layer that can regenerate public ids and fallback to scenario-derived
waypoints. That keeps multiple waypoint sources of truth alive after the map
bundle contract has already become the consistent map artifact boundary for
simulator, real robot, and digital-twin flows.

The result is false confidence: a product run or test can appear to have usable
waypoints even when the canonical map artifact is missing, malformed, or not
wired into the runtime.

## Accepted Contract

- Product runtime base `inspection_waypoints` must come from the selected map
  artifact.
- Simulator product runtime uses the canonical simulator map bundle, including
  `semantics.json.inspection_waypoints`.
- Real-robot and digital-twin product runtime use the AGI/Agibot map context or
  the canonical runtime bundle compiled from that context.
- Runtime may add state such as `visited`, runtime observations, and
  target-specific inspection candidates.
- Runtime must not synthesize, re-id, resample, or fallback-generate the base
  waypoint set.
- `generated_exploration_*` remains a valid artifact-level waypoint id prefix
  when the map artifact generated those waypoints. The prefix is not a runtime
  projection policy.
- Missing or malformed base waypoints in product runtime are fatal map artifact
  errors with actionable guidance to generate or compile the map bundle.

## Allowed No-Bundle Boundary

No-bundle waypoint generation is allowed only for:

- offline map bundle generation;
- explicit synthetic tests that name their synthetic contract;
- narrow unit helpers that do not claim product runtime behavior.

It is not allowed for:

- `surface=household-world` product runs;
- eval product rows;
- operator-console launch routes;
- coding-agent MCP server runtime;
- report/checker paths that claim current product artifact validity.

## Implementation Scope

1. Preserve artifact waypoint identity in the public Base Navigation Map
   projection. The agent-visible base waypoint id, source, pose, and room fields
   should match the source map artifact except for allowed runtime state.
2. Replace runtime base waypoint regeneration with a direct projection from the
   canonical map artifact.
3. Remove silent fallback from product runtime initialization. If a product path
   lacks a valid map bundle or base waypoint set, fail before the MCP server or
   run loop can claim readiness.
4. Keep runtime-generated target-inspection waypoints separate. Existing
   `generated_target_inspection_candidate` behavior remains runtime-owned
   because it is created from current-run observations.
5. Migrate tests and fixtures that still assume runtime-generated base waypoint
   ids or old map bundle names.

## Non-Goals

- Do not design a new waypoint sampling algorithm in this slice.
- Do not remove `inspection_waypoints` from the Base Navigation Map.
- Do not remove runtime target-inspection candidates.
- Do not add a compatibility shim for old runtime-generated base waypoint ids.
- Do not require a live Nav2 stack for simulator acceptance.
- Do not migrate historical reports or archived plan text unless they block
  current tests or product routes.

## Verification

- Validate every committed canonical simulator map bundle with
  `scripts/maps/check_bundle.py`.
- Add a contract test that initializes the household runtime from a canonical
  simulator bundle and asserts base waypoint ids, source, pose, and room fields
  are preserved in the public metric map.
- Add negative tests that product runtime fails loudly when the selected map
  artifact is missing `inspection_waypoints`.
- Keep a synthetic helper test for explicitly no-bundle fixture waypoint
  generation if the helper remains needed.
- Run focused household map/contract/MCP tests through
  `./scripts/dev/run_pytest_standalone.sh`.
- Run `ruff check` and `ruff format --check` on changed code and tests.

## Next Step

Run `$intuitive-preflight` to turn this contract into an implementation-ready
scope with exact files, stop gates, and proof commands.

## Preflight Contract

Preflight status: DRAFT

Task source: plan path plus accepted grill decision.

Canonical source: `docs/plans/2026-06-19-base-waypoint-source-contract.md`.

Route: durable `$intuitive-flow`, with implementation shaped as a bounded
refactor slice.

Goal: make product runtime project base inspection waypoints from the selected
map artifact without runtime re-id generation or silent no-bundle fallback.

Scope:

- Preserve artifact waypoint identity in the public Base Navigation Map
  projection: `waypoint_id`, `waypoint_source`, pose, room id/label, purpose,
  and other public fields should come from the selected map artifact.
- Keep private/static fixture links private unless a field is already part of
  the public Base Navigation Map contract.
- Replace runtime base waypoint regeneration in the household public map
  projection with direct artifact waypoint projection plus visit state.
- Keep `generated_exploration_candidates` only as a derived public view of
  artifact-authored generated-exploration waypoints, preserving artifact ids
  rather than assigning new runtime ids.
- Make product runtime paths fail before readiness when the selected map
  artifact is missing or lacks base `inspection_waypoints`.
- Keep explicit no-bundle use available for offline simulator map bundle
  generation and synthetic unit helpers.
- Update tests and current docs touched by the behavior change.

Non-goals:

- No new waypoint sampling algorithm.
- No live Nav2 dependency.
- No removal of runtime `generated_target_inspection_candidate` waypoints.
- No compatibility shim that maps old runtime-generated base ids to artifact
  ids.
- No broad historical report migration.
- No unrelated operator-console preview cleanup.

Entity budget:

- Reuse: Base Navigation Map, Prebuilt Robot Map Bundle, existing
  `RealWorldCleanupContract`, existing Nav2 bundle validation, existing product
  `map_bundle` launch selection.
- Remove/merge: runtime base waypoint re-id generation as a product projection
  policy; silent scenario-derived product fallback.
- New: at most small local helper functions/tests for public waypoint
  sanitization and fail-loud validation.
- Expansion triggers: adding a new public waypoint schema, new command flag,
  compatibility bridge, or changing target-inspection candidate semantics needs
  re-approval.

Context:

- Must-read:
  - `docs/human/domain.md`
  - `docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md`
  - `roboclaws/maps/project.py`
  - `roboclaws/maps/bundle_validation.py`
  - `roboclaws/household/realworld_contract_init.py`
  - `roboclaws/household/realworld_contract_projection.py`
  - `roboclaws/household/realworld_contract.py`
  - `roboclaws/household/realworld_cleanup.py`
  - `roboclaws/household/realworld_mcp_server.py`
  - `roboclaws/cli/household_agent_server.py`
  - `roboclaws/launch/catalog.py`
  - `roboclaws/launch/worlds.py`
  - `tests/contract/maps/test_nav2_map_bundle_contract.py`
  - `tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
  - `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
  - `tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py`
  - `tests/unit/launch/test_scene_sampler.py`
  - `tests/unit/operator_console/test_routes.py`
- Useful:
  - `scripts/maps/generate_molmospaces_scene_bundles.py`
  - `tests/contract/maps/test_generate_molmospaces_scene_bundles.py`
  - `tests/contract/maps/test_runtime_map_prior_snapshot.py`
  - `scripts/maps/check_bundle.py`
- Avoid unless needed: historical plan bodies, archived reports, local
  `output/`, and unrelated operator-console preview renderer changes.

Acceptance:

- SUCCESS: A household runtime initialized from a canonical simulator map
  bundle exposes public base `inspection_waypoints` with artifact waypoint ids,
  waypoint source, pose, and room fields preserved; navigation to those ids
  still works; target-inspection runtime candidates still work separately.
- SUCCESS: Product entrypoints that claim current household runtime readiness
  fail loudly when no valid map artifact/base waypoint set is available.
- SUCCESS: Existing canonical simulator bundles validate and at least one
  public household product command exercises the changed projection.
- BLOCKED_NEEDS_DECISION: Any proposal to preserve old runtime-generated base
  waypoint ids, expose fixture ids by default, add a new public waypoint API, or
  alter runtime target-inspection candidate semantics.
- BLOCKED_NEEDS_LOCAL_VALIDATION: If the required simulator-backed product run
  cannot execute in the implementation environment, the work is not complete
  until local validation passes.
- INTERMEDIATE_ONLY: acceptable only if explicitly requested after code-local
  gates pass but before simulator product proof.
- No regressions: private scoring truth stays out of Agent View; runtime
  observations and generated target-inspection candidates remain Runtime Metric
  Map behavior; offline bundle generation can still intentionally use the
  synthetic no-bundle path.

Verification:

- Deterministic:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/maps/test_generate_molmospaces_scene_bundles.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_routes.py`
  - `ruff check <changed files>`
  - `ruff format --check <changed files>`
- Integration:
  - `python scripts/maps/check_bundle.py assets/maps/molmospaces/procthor-10k-val/0`
  - Repeat `scripts/maps/check_bundle.py` across all committed canonical
    `assets/maps/molmospaces/*/*` bundles.
- Product-run:
  - `just run::surface surface=household-world world=molmospaces/procthor-10k-val/0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels scenario_setup=baseline`
  - Inspect the run artifact's Agent View / `metric_map.inspection_waypoints`
    and confirm artifact waypoint ids are preserved.
- Local-live-manual:
  - Required if MuJoCo/MolmoSpaces simulator assets are unavailable to the
    implementation runner; execute the product-run gate on a local workstation
    before claiming completion.
- Optional:
  - `just agent::eval recommend plan=docs/plans/2026-06-19-base-waypoint-source-contract.md budget=focused`

Execution:

- Main: supervise the implementation, protect unrelated dirty worktree changes,
  and verify final diffs/gates.
- Worker: none by default.
- Worker-goal: none.

To execute: `/goal execute docs/plans/2026-06-19-base-waypoint-source-contract.md with intuitive-flow`

Optional tracking: none.

Approval: `LGTM`, `approve`, or `go ahead` approves this preflight; edits
request revision.

## Closeout

Implementation status: Implemented on 2026-06-19.

What changed:

- Bundle-backed household runtime now projects base `inspection_waypoints`
  directly from the selected map artifact, preserving artifact waypoint ids,
  waypoint source, pose, room fields, and public metadata while stripping
  private `fixture_ids`.
- Product runtime without a selected map bundle now fails before readiness
  instead of synthesizing scenario-derived base waypoints.
- Synthetic no-bundle projection remains available only through explicit
  internal/test/offline opt-in.
- Runtime-generated target-inspection candidates remain separate Runtime Metric
  Map behavior.

Proof:

- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/maps/test_generate_molmospaces_scene_bundles.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_smoke_artifacts.py tests/contract/molmo_cleanup/test_molmo_mcp_smoke_shared_semantic_loop.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/maps/test_runtime_map_prior_snapshot.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_routes.py tests/unit/molmo_cleanup/test_molmo_planner_observed_binding.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::test_checker_accepts_single_realworld_run tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::test_checker_can_require_base_navigation_map_map_build tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::test_checker_accepts_realworld_mcp_smoke_policy tests/contract/molmo_cleanup/test_molmo_realworld_mcp_smoke_artifacts.py tests/contract/molmo_cleanup/test_molmo_mcp_smoke_shared_semantic_loop.py`
- `python scripts/maps/check_bundle.py` across all 16 committed
  `assets/maps/molmospaces/*/*` bundles.
- `ruff check` and `ruff format --check` on changed Python files.
- Product proof:
  `just run::surface surface=household-world world=molmospaces/procthor-10k-val/0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-public-labels seed=7 scenario_setup=baseline robot_views=off`
  passed. The resulting artifact
  `output/household/household-world/map-build/direct-world-public-labels/0619_2235/seed-7/run_result.json`
  reported `base_navigation_map.source=map_artifact_inspection_waypoints`,
  14 source waypoints, 14 runtime waypoints, preserved first ids
  `generated_exploration_001..005`, and 14/14 visited waypoints.

Notes:

- A cleanup product run with relocated objects also exercised the projection
  and visited all 14 artifact waypoints, but its command exited 1 because the
  deterministic cleanup policy failed the semantic placement score. That is
  outside this waypoint-source slice and was not treated as a waypoint
  projection failure.
- A `camera-grounded-labels` map-build run exercised the projection but exited
  1 because the local Grounding-DINO sidecar was not reachable. The passing
  `world-public-labels` map-build run is the product proof for this slice.

Parked follow-ups:

- Tighten the deterministic cleanup/smoke checker behavior separately if smoke
  verification should pass when a baseline scenario has zero cleanup targets.
  This was not changed because the current slice only owns map artifact and
  waypoint source-of-truth behavior.
