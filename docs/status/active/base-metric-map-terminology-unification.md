# Base Metric Map Terminology Unification

Source plan: `docs/plans/2026-06-23-base-metric-map-terminology-unification.md`

Latest user intent: continue implementation through `$intuitive-flow`.

Current slice: completed.

No-touch scope:
- Do not rename `navigation_area`, `navigation_area_id`,
  `base_navigation_area_inspection`, or
  `base_navigation_area_centroid_clearance_v1`.
- Do not reset or stage unrelated existing worktree changes.
- Do not add readers for old `base_navigation_map*` fields or filenames.

Final proven evidence:
- `uv sync --extra dev` passed.
- SDK-local Agibot boundary tests passed after migrating the nested vendor
  runner:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/agibot/test_agibot_map_context_scripts.py::test_generate_metric_map_from_base_metric_agibot_context tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_metric_context_generated_candidates`
- Focused pytest gate passed:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/maps tests/unit/operator_console tests/contract/reports/test_molmo_cleanup_report.py tests/contract/checkers/test_realworld_base_metric_map_checker.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/agibot/test_agibot_map_context_scripts.py`
- `ruff check .` passed.
- `ruff format --check .` passed.
- Required stale-token search returned no active-surface matches:
  `rg -n "Base Navigation Map|base_navigation_map|BASE_NAVIGATION_MAP|base-navigation-map" roboclaws scripts tests just skills AGENTS.md CLAUDE.md README.md ARCHITECTURE.md STATUS.md CONTEXT.md docs/human docs/adr assets vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py`
- Broader filtered stale-prefix search returned no active top-level map matches
  outside the protected `base_navigation_area_*` waypoint sub-concepts.

Scope note:
- `vendors/agibot_sdk` is a nested git repository. Its
  `tools/run_agibot_cleanup_backend.py` was migrated to emit Base Metric Map
  keys/strings, and the parent repo now shows the submodule as modified.

Stop condition met: current contract/code/assets/docs use Base Metric Map with
no compatibility aliases; protected navigation-area sub-concepts were not
renamed.

Parked work: none.
