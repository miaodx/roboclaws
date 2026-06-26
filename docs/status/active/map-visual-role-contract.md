# Map Visual Role Contract

Owner/session: Codex intuitive-flow main session
Started: 2026-06-23
State: browser-validated; ready for review with noted caveats

## Scope

Implement the visual-role contract from
`docs/plans/2026-06-23-map-visual-role-contract.md`: one shared map preview
visual language for Base Navigation Map and Runtime Metric Map previews, plus
honest top-down scene render slots and structured operator-console roles.

## Source Of Truth

- Plan: `docs/plans/2026-06-23-map-visual-role-contract.md`
- Route: durable `$intuitive-flow`, bounded `$intuitive-refactor` slice

## Completed Slice

- Added shared map preview rendering under `roboclaws/maps/preview.py`.
- Migrated Base Navigation Map bundle previews and Runtime Metric Map previews
  to the shared 900x560 overlay language.
- Kept Base Navigation Map and Runtime Metric Map data schemas unchanged.
- Split operator-console view roles into `map`, `runtime_map`, and `topdown`
  with explicit `visual_role` and `artifact_source_family`.
- Kept top-down evidence tied to scene/camera renders, not map preview
  fallbacks.
- Regenerated MolmoSpaces static preview metadata with base-map and scene-render
  source families; B1/Agibot preview work remains omitted unless honest assets
  and proof exist.

## Last Proven Evidence

- Operator-console unit/static/render tests passed:
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py tests/unit/operator_console/test_static_assets.py tests/unit/operator_console/test_render_scene_previews.py`
- Report/live/checker tests passed:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/reports/test_molmo_cleanup_report.py tests/contract/molmo_cleanup/test_realworld_mcp_live_artifacts.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::test_checker_can_require_runtime_metric_map`
- Full B1-inclusive map bundle contract tests passed after initializing the
  local vendor submodules:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/maps/test_nav2_map_bundle_contract.py`
- `ruff check .` passed.
- Full `ruff format --check .` passed after mechanically formatting eight
  pre-existing out-of-format files.
- `git diff --check` passed.
- Touched-file format check passed.
- Product proof passed:
  `just run::surface surface=household-world world=molmospaces/procthor-objaverse-val/0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-public-labels seed=7`
- Latest product run:
  `output/household/household-world/map-build/direct-world-public-labels/0623_1756/seed-7`
- Product artifact dimensions verified:
  `map_bundle/preview.png` PNG 900x560,
  `runtime_metric_map_preview.png` PNG 900x560,
  `robot_views/0001_after.topdown.png` PNG 540x360.
- Browser validation passed against `http://127.0.0.1:18082/` using
  `GSTACK_CHROMIUM_NO_SANDBOX=1 /home/mi/.codex/skills/gstack/browse/dist/browse`.
  The real console attach path rendered three artifact-backed image buttons:
  `data-view-role=base_navigation_map_preview` with
  `data-artifact-source-family=base_navigation_map_bundle`,
  `data-view-role=runtime_metric_map_preview` with
  `data-artifact-source-family=runtime_metric_map`, and
  `data-view-role=topdown_scene_render` with
  `data-artifact-source-family=scene_camera_render`.
- Browser network/console proof: no console messages; artifact requests returned
  200. Screenshot:
  `output/operator-console/browser-map-role-proof.png`.

## Browser Fixture Note

The successful product proof was launched directly, not through the operator
console, so `/api/runs/latest` could not attach it from the default
`output/operator-console/runs` root. Browser QA used a run-shaped console
fixture at `output/operator-console/runs/browser-map-role-proof/` populated with
copies of the successful product artifacts. This exercised the existing
artifact-backed console attach/render path without changing application code.

## Caveats

- Static route previews display Base Map and top-down scene slots and leave
  Runtime Metric Map empty before a run. The canonical `visual_role` /
  `artifact_source_family` browser proof is artifact-backed run state.

## Next Action

Review the diff and port the committed worktree change to the repo root.

## No-Touch Scope

- No Base Navigation Map, Runtime Metric Map, Agent View, or map bundle schema
  version changes.
- No `semantic_map.png`, `map_overlay.json`, or stale compatibility shims.
- No B1/Agibot fabricated preview work.
