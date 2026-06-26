# Agent View Module Refactor

Source plan: `docs/plans/2026-06-22-agent-view-module-refactor.md`

Latest user intent: execute the full Agent View Module refactor with
`intuitive-flow`.

Current slice: implementation complete; final regression/static verification
passed. Ready for human review or commit.

Last proven evidence:

- Required orientation set refreshed: `README.md`, `ARCHITECTURE.md`,
  `STATUS.md`, `AGENTS.md`, `CLAUDE.md`.
- Flow and durable-run rules read.
- Host goal is active.
- Worktree was clean at resume.
- Slice 1 docs patched:
  `docs/adr/0145-use-agent-view-as-household-world-module-boundary.md` and the
  interface inventory appendix in the source plan.
- ASCII check passed for the ADR, plan, and capsule.
- Added canonical `roboclaws/household/agent_view.py` with
  `schema=agent_view_v2`, section accessors, and shared private-field guard.
- Routed MolmoSpaces, Agibot cleanup, Agibot map-build MCP, Agibot SDK export,
  and MolmoSpaces Agibot rehearsal Agent View producers through the v2
  schema/guard vocabulary.
- Migrated report, checker, probe, corpus, artifact, and focused test consumers
  from old top-level Agent View fields to v2 section accessors. Remaining
  scan hits are local pseudo-map fixtures in
  `tests/contract/maps/test_nav2_map_bundle_contract.py`, not saved Agent View
  artifacts.
- Added eval-harness path signal for `roboclaws/household/agent_view.py`.
- Added Agent View active-perception summaries for RAW-FPV observations,
  camera-grounded-label sidecar status/provenance, and visual-candidate
  lifecycle state/actionability counts.
- Advanced live visual-grounding sidecar requests to
  `visual_grounding_request_v2` with `public_map_hints.fixture_hints`, and
  removed `static_fixture_projection` from live request builders. The request
  validator now rejects legacy `static_fixture_projection`,
  `private_truth_included=true`, and known private scorer/setup keys in public
  map hints.
- Updated MolmoSpaces, Agibot map-build, visual-grounding service adapters,
  and the benchmark runner to use the v2 request shape.
- Replaced stale policy-view allowed input naming with
  `base_navigation_map` / `runtime_metric_map`.
- Derived Agent View `capabilities` from MCP profile metadata plus runtime
  public-tool registration. Runtime extra tools are now explicit, and blocked
  manipulation details resolve to profile metadata.
- Updated MolmoSpaces and Agibot builders to use MCP profile constants rather
  than duplicated profile strings.
- Updated the Agibot SDK runner wrapper to convert the SDK-local export into
  public `agent_view_v2`, preserve a `vendor_agent_view.json` sidecar for
  subsequent vendor CLI stages, and embed the Roboclaws-owned artifact in
  `run_result.json`.
- Added a focused `agent-view-contract-tests` eval-harness row for the
  `agent_view_module` signal. The row covers Agent View artifact privacy,
  MCP/profile capabilities, active-perception provenance, visual-grounding
  public input guards, and Agibot Agent View export without redesigning the
  eval row taxonomy.
- Corrected the real-robot alignment checker/report readiness proof to require
  `real_robot_readiness.public_static_map=true` and
  `static_fixture_projection=false`, matching the new Agent View boundary.
- Updated `ARCHITECTURE.md` to name `roboclaws/household/agent_view.py` as the
  canonical Agent View owner and document the current `agent_view_v2` sections.
- Proof:
  - `python -m py_compile ...` on touched runtime/checker/test files.
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/unit/evals/test_eval_harness_selector.py tests/contract/checkers/test_realworld_base_navigation_map_checker.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -k 'agent_view or agibot or raw_fpv or camera_model_policy or open_ended' tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py::test_agibot_molmospaces_prehardware_map_build_starts_from_base_navigation_map`
    passed with one skip.
  - `ruff check ...` passed on touched household/scripts/tests scope.
  - `ruff format --check ...` passed on touched household/scripts/tests scope.
  - `just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused`
    wrote `output/eval-harness/20260622T180801Z/eval_harness.json`.
  - Slice 3 focused pytest:
    `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/visual_grounding/test_visual_grounding_service.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py -k 'raw_fpv_mode_suppresses_structured_detections or camera_model_policy_observe_exposes_model_declared_candidates or camera_model_policy_records_sim_pipeline_provenance or camera_labels_http_success_uses_destination_resolver or camera_labels_http_failure_is_visible_without_sim_fallback or camera_labels_missing_raw_image_fails_before_sidecar or agent_view_payload_keeps_private_evaluation_out' tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -k 'camera_grounded_composite or raw_fpv or camera_labels_declare_response_is_agent_compact' tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_map_build_camera_labels_call_external_grounding`
    passed.
  - Slice 3 `ruff check`, `ruff format --check`, and `git diff --check`
    passed on touched active-perception/sidecar files.
  - Slice 4 focused pytest:
    `./scripts/dev/run_pytest_standalone.sh -q tests/contract/mcp/test_semantic_profiles.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_registered_tools_match_profile_public_surface tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_agent_sdk_camera_grounded_composite_tool_is_opt_in tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_physical_agibot_pilot_uses_sdk_runner_reports_without_movement tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py::test_molmospaces_agibot_contract_rehearsal_writes_simulated_report tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates`
    passed.
  - Slice 4 `ruff check`, `ruff format --check`, vendor runner
    `py_compile`, and `git diff --check` passed on touched files.
  - Slice 5 selector test:
    `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_harness_selector.py`
    passed.
  - Slice 5 Agent View gate command:
    `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_agent_view_payload_keeps_private_evaluation_out tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_raw_fpv_mode_suppresses_structured_detections tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_model_policy_registers_model_labelled_candidates tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_model_policy_records_sim_pipeline_provenance tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_labels_http_failure_is_visible_without_sim_fallback tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_labels_missing_raw_image_fails_before_sidecar tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_labels_http_success_uses_destination_resolver tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_registered_tools_match_profile_public_surface tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_agent_sdk_camera_grounded_composite_tool_is_opt_in tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_rejects_removed_static_fixture_projection_tool tests/contract/mcp/test_semantic_profiles.py tests/unit/molmo_cleanup/test_visual_grounding.py::test_visual_grounding_request_rejects_static_fixture_projection_field tests/unit/molmo_cleanup/test_visual_grounding.py::test_visual_grounding_request_rejects_private_public_map_hints tests/unit/molmo_cleanup/test_visual_grounding.py::test_visual_grounding_request_rejects_private_hint_keys tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_map_build_camera_labels_call_external_grounding tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates`
    passed.
  - Slice 5 eval-harness recommend:
    `just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused`
    wrote `output/eval-harness/20260622T185007Z/eval_harness.json`
    and selected `agent-view-contract-tests`.
  - Slice 5 narrowed eval-harness execute:
    `just agent::eval execute changed_file=roboclaws/household/agent_view.py budget=focused`
    wrote `output/eval-harness/20260622T185559Z/eval_harness.json`;
    selected `cleanup-contract-tests`, `agent-view-contract-tests`, and
    `household-direct-world-public-product`; all three ran and passed.
  - Final focused regression:
    `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/mcp/test_semantic_profiles.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/unit/evals/test_eval_harness_selector.py`
    passed.
  - Final checker/perception regression:
    `./scripts/dev/run_pytest_standalone.sh -q tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -k 'agent_view or real_robot_alignment or runtime_metric_map or raw_fpv or camera_model_policy or static_fixture_projection or base_navigation_map' tests/contract/checkers/test_realworld_base_navigation_map_checker.py tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_map_build_camera_labels_call_external_grounding tests/contract/visual_grounding/test_visual_grounding_service.py`
    passed.
  - Final static checks: `ruff check ...`, owned-scope `ruff format --check ...`,
    `python -m py_compile vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py`,
    `git diff --check`, and the narrowed stale Agent View old-field search
    passed.
  - Repo-wide `ruff format --check` across all tests/scripts in the plan found
    unrelated pre-existing format drift in
    `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
    `tests/unit/launch/test_environment_setup_catalog.py`, and
    `tests/unit/molmo_cleanup/test_ci_live_reports.py`; owned changed scope
    format check passed.

Next hypothesis:

Implementation is complete unless human review asks for changes.

Next proof:

- Optional: create a semantic commit if requested or if the workflow proceeds to
  landing.

Stop condition:

- Stop before changing public `just run::surface` grammar, adding compatibility
  shims for old Agent View layout, broad eval-harness taxonomy redesign, or any
  private-truth leak into agent-facing payloads.

No-touch scope:

- No `evolution_target`.
- No capability-slice eval grouping.
- No provider matrix redesign.
- No live-provider proof as a deterministic completion requirement.

Parked work:

- Eval `evolution_target`, capability-slice grouping, provider matrix changes,
  and live-provider proof remain parked follow-ups/non-goals.
