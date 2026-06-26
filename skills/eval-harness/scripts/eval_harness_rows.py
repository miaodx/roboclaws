from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

ROW_SCHEMA = "roboclaws_eval_harness_row_v1"
DEFAULT_WORLD = "molmospaces/val_0"
DEFAULT_BACKEND = "mujoco"
DEFAULT_SEED = "7"
DEFAULT_PROVIDER_PROFILE = "codex-router-responses"
DEFAULT_AGENT_SDK_PROVIDER_PROFILE = "minimax-responses"
MAP_BUILD_CONSUMER_MODEL_MATRIX_PROVIDER_PROFILES = (
    "codex-router-responses",
    "mimo-inside-openai-chat",
    "kimi-openai-chat",
    "minimax-responses",
)


def candidate_rows(
    *, output_dir: Path, explicit_axes: dict[str, list[str]]
) -> list[dict[str, Any]]:
    provider_profiles = explicit_axes.get("provider_profile") or [DEFAULT_PROVIDER_PROFILE]
    agent_sdk_provider = next(
        (profile for profile in provider_profiles if profile != DEFAULT_PROVIDER_PROFILE),
        DEFAULT_AGENT_SDK_PROVIDER_PROFILE,
    )
    row_dir = output_dir / "rows"
    eval_output_root = output_dir / "evals"
    return [
        _row(
            row_id="route-trace-contract-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/contract/dev_tools/test_task_agent_just_recipes.py",
            ],
            axes={"intent": "route-trace"},
            reason=(
                "Launch catalog, provider profile, or command-surface changes need "
                "route trace coverage."
            ),
            rule_ids=("launch_catalog",),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="eval-unit-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/unit/evals",
            ],
            axes={"intent": "eval-harness"},
            reason=(
                "Eval harness, suite, manifest, or regression-promotion changes need eval tests."
            ),
            rule_ids=("eval_harness",),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="cleanup-contract-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/unit/molmo_cleanup/test_molmo_cleanup_policy.py",
                "tests/unit/molmo_cleanup/test_molmo_cleanup_semantic_acceptability.py",
                "tests/unit/molmo_cleanup/test_molmo_semantic_cleanup_loop.py",
            ],
            axes={"intent": "cleanup", "agent_engine": "direct-runner"},
            reason=(
                "Cleanup, MCP, checker, and report changes need deterministic cleanup "
                "contract checks."
            ),
            rule_ids=("cleanup_skill", "mcp_checker", "agent_view_module"),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="agent-view-contract-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::"
                "test_realworld_agent_view_payload_keeps_private_evaluation_out",
                "tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::"
                "test_realworld_raw_fpv_mode_suppresses_structured_detections",
                "tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::"
                "test_realworld_camera_model_policy_registers_model_labelled_candidates",
                "tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::"
                "test_realworld_camera_model_policy_records_sim_pipeline_provenance",
                "tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::"
                "test_realworld_camera_labels_http_failure_is_visible_without_sim_fallback",
                "tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::"
                "test_realworld_camera_labels_missing_raw_image_fails_before_sidecar",
                "tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::"
                "test_realworld_camera_labels_http_success_uses_destination_resolver",
                "tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::"
                "test_realworld_mcp_registered_tools_match_profile_public_surface",
                "tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::"
                "test_agent_sdk_camera_grounded_composite_tool_is_opt_in",
                "tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::"
                "test_realworld_mcp_rejects_removed_static_fixture_projection_tool",
                "tests/contract/mcp/test_semantic_profiles.py",
                "tests/unit/molmo_cleanup/test_visual_grounding.py::"
                "test_visual_grounding_request_rejects_static_fixture_projection_field",
                "tests/unit/molmo_cleanup/test_visual_grounding.py::"
                "test_visual_grounding_request_rejects_private_public_map_hints",
                "tests/unit/molmo_cleanup/test_visual_grounding.py::"
                "test_visual_grounding_request_rejects_private_hint_keys",
                "tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::"
                "test_agibot_map_build_camera_labels_call_external_grounding",
                "tests/contract/agibot/test_agibot_map_context_scripts.py::"
                "test_sdk_runner_exports_base_metric_context_generated_candidates",
            ],
            axes={"intent": "agent-view", "agent_engine": "direct-runner"},
            reason=(
                "Agent View module changes need artifact schema, privacy guard, MCP "
                "response, profile capability, active-perception, sidecar public-input, "
                "and Agibot export coverage."
            ),
            rule_ids=("agent_view_module",),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="household-direct-world-public-product",
            row_kind="product_run",
            command=[
                "just",
                "run::surface",
                "surface=household-world",
                f"world={DEFAULT_WORLD}",
                f"backend={DEFAULT_BACKEND}",
                "preset=cleanup",
                "agent_engine=direct-runner",
                "evidence_lane=world-public-labels",
                f"seed={DEFAULT_SEED}",
                f"output_dir={row_dir / 'household-direct-world-public-product' / 'run'}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "world-public-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="MCP/server/checker changes need at least one public cleanup product route.",
            rule_ids=("mcp_checker", "agent_view_module"),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="open-ended-household-contract-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/contract/dev_tools/test_task_agent_just_recipes.py::"
                "test_surface_prompt_omitted_intent_with_prompt_infers_open_ended",
                "tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::"
                "test_realworld_mcp_open_ended_intent_is_recorded_in_run_result",
                "tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::"
                "test_checker_allows_open_ended_agent_view_with_no_visible_objects",
            ],
            axes={"intent": "open-ended"},
            reason=(
                "Open-ended, goal-contract, or completion-claim changes need a "
                "first-class open-ended launch and artifact contract gate."
            ),
            rule_ids=("open_ended",),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="smoke-regression-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="smoke_regression",
                budget="smoke",
                output_root=eval_output_root,
                stamp="smoke-regression-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "smoke_regression"},
            reason="Eval harness or command-surface changes need the smoke regression suite.",
            rule_ids=("eval_harness", "launch_catalog"),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="map-build-consumer-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="map_build_consumer",
                budget="smoke",
                output_root=eval_output_root,
                stamp="map-build-consumer-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "map_build_consumer"},
            reason=(
                "Map-build and actionability changes need the map consumer suite and "
                "runtime-map-prior flow."
            ),
            rule_ids=("map_build",),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        *[
            _map_build_consumer_model_matrix_row(
                output_root=eval_output_root,
                row_dir=row_dir,
                provider_profile=profile,
            )
            for profile in MAP_BUILD_CONSUMER_MODEL_MATRIX_PROVIDER_PROFILES
        ],
        _row(
            row_id="open-ended-goals-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="open_ended_goals",
                budget="smoke",
                output_root=eval_output_root,
                stamp="open-ended-goals-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "open_ended_goals"},
            reason=(
                "Open-ended household goal changes need the dedicated no-preset "
                "open-task capability suite."
            ),
            rule_ids=("open_ended",),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="scene-sampler-stress-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="scene_sampler_stress",
                budget="smoke",
                output_root=eval_output_root,
                stamp="scene-sampler-stress-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "scene_sampler_stress"},
            reason=(
                "MolmoSpaces scene-source sampling changes need the static sampler stress "
                "projection with partial/blocked source metadata."
            ),
            rule_ids=("scene_sampler", "launch_catalog", "eval_harness"),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="cleanup-capability-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="cleanup_capability",
                budget="smoke",
                output_root=eval_output_root,
                stamp="cleanup-capability-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "cleanup_capability"},
            reason="Cleanup skill or MCP changes need the repeated cleanup capability suite.",
            rule_ids=("cleanup_skill", "mcp_checker"),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="openai-agents-sdk-open-task-live-eval",
            row_kind="live_agent_eval",
            command=_eval_suite_command(
                suite="open_ended_goals",
                budget="smoke",
                output_root=eval_output_root,
                stamp="openai-agents-sdk-open-task-live-eval",
                agent_engine="openai-agents-sdk",
                provider_profile=agent_sdk_provider,
                live_execution="run",
            ),
            axes={
                "agent_engine": "openai-agents-sdk",
                "provider_profile": agent_sdk_provider,
                "intent": "open-ended",
                "preset": "",
                "evidence_lane": "world-public-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason=(
                "Agent SDK or open-task launch changes need a representative live-agent "
                "capability eval row."
            ),
            rule_ids=("agent_sdk", "open_ended"),
            requirements=("just", "python_env", "openai_agents_package", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
        ),
        _row(
            row_id="openai-agents-sdk-cleanup-live-eval",
            row_kind="live_agent_eval",
            command=_eval_suite_command(
                suite="cleanup_capability",
                budget="smoke",
                output_root=eval_output_root,
                stamp="openai-agents-sdk-cleanup-live-eval",
                agent_engine="openai-agents-sdk",
                provider_profile=agent_sdk_provider,
                live_execution="run",
            ),
            axes={
                "agent_engine": "openai-agents-sdk",
                "provider_profile": agent_sdk_provider,
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "world-public-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason=(
                "Cleanup skill or MCP changes need a representative SDK live-agent "
                "cleanup capability eval row."
            ),
            rule_ids=("cleanup_skill", "mcp_checker"),
            requirements=("just", "python_env", "openai_agents_package", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
        ),
        _row(
            row_id="openai-agents-sdk-cleanup-camera-raw-fpv-live-product",
            row_kind="live_agent_eval",
            command=_cleanup_command(
                row_dir=row_dir,
                row_id="openai-agents-sdk-cleanup-camera-raw-fpv-live-product",
                agent_engine="openai-agents-sdk",
                provider_profile=agent_sdk_provider,
                evidence_lane="camera-raw-fpv",
            ),
            axes={
                "agent_engine": "openai-agents-sdk",
                "provider_profile": agent_sdk_provider,
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "camera-raw-fpv",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="RAW-FPV changes need a live or direct SDK RAW-FPV cleanup gate.",
            rule_ids=("raw_fpv",),
            requirements=("just", "python_env", "openai_agents_package", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
        ),
        _row(
            row_id="openai-agents-sdk-codex-router-responses-availability",
            row_kind="live_agent_eval",
            command=_eval_suite_command(
                suite="open_ended_goals",
                budget="smoke",
                output_root=eval_output_root,
                stamp="openai-agents-sdk-codex-router-responses-availability",
                agent_engine="openai-agents-sdk",
                provider_profile=DEFAULT_PROVIDER_PROFILE,
                live_execution="run",
            ),
            axes={
                "agent_engine": "openai-agents-sdk",
                "provider_profile": DEFAULT_PROVIDER_PROFILE,
                "intent": "open-ended",
                "preset": "",
                "evidence_lane": "world-public-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason=(
                "Agent SDK codex-router-responses remains provider availability evidence while "
                "provider-side 502/upstream-unavailable responses persist."
            ),
            rule_ids=("agent_sdk_codex_env_availability",),
            requirements=("just", "python_env", "openai_agents_package", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
            requirement="optional",
        ),
        _row(
            row_id="planner-proof-dry-run-product",
            row_kind="product_run",
            command=[
                "just",
                "run::surface",
                "surface=planner-proof",
                "world=planner-proof/default",
                f"backend={DEFAULT_BACKEND}",
                "intent=planner-proof",
                "agent_engine=direct-runner",
                "mode=dry-run",
                f"output_dir={row_dir / 'planner-proof-dry-run-product' / 'run'}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "planner-proof",
                "backend": DEFAULT_BACKEND,
                "world": "planner-proof/default",
            },
            reason=(
                "Planner-proof changes need the current public planner-proof dry-run "
                "proof row; lower-level harness recipes remain private mechanics."
            ),
            rule_ids=("planner_proof",),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-camera-grounded-grounding-dino",
            row_kind="product_run",
            command=_cleanup_command(
                row_dir=row_dir,
                row_id="direct-camera-grounded-grounding-dino",
                agent_engine="direct-runner",
                evidence_lane="camera-grounded-labels",
                camera_labeler="grounding-dino",
            ),
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "camera-grounded-labels",
                "camera_labeler": "grounding-dino",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Visual-grounding changes need a real Grounding DINO camera-labeler gate.",
            rule_ids=("visual_grounding",),
            requirements=("just", "python_env", "dino_sidecar"),
            expense="dino",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-map-build-grounding-dino",
            row_kind="product_run",
            command=[
                "just",
                "run::surface",
                "surface=household-world",
                f"world={DEFAULT_WORLD}",
                f"backend={DEFAULT_BACKEND}",
                "preset=map-build",
                "agent_engine=direct-runner",
                "evidence_lane=camera-grounded-labels",
                "camera_labeler=grounding-dino",
                f"seed={DEFAULT_SEED}",
                "scenario_setup=baseline",
                f"output_dir={row_dir / 'direct-map-build-grounding-dino' / 'run'}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "map-build",
                "preset": "map-build",
                "evidence_lane": "camera-grounded-labels",
                "camera_labeler": "grounding-dino",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason=(
                "Map-build product proof should exercise the deployable Grounding-DINO "
                "camera-labeler route."
            ),
            rule_ids=("map_build", "visual_grounding"),
            requirements=("just", "python_env", "dino_sidecar"),
            expense="dino",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-camera-raw-fpv",
            row_kind="product_run",
            command=_cleanup_command(
                row_dir=row_dir,
                row_id="direct-camera-raw-fpv",
                agent_engine="direct-runner",
                evidence_lane="camera-raw-fpv",
            ),
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "camera-raw-fpv",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="RAW-FPV changes need a direct RAW-FPV product gate.",
            rule_ids=("raw_fpv",),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-map-build-world-public",
            row_kind="product_run",
            command=[
                "just",
                "run::surface",
                "surface=household-world",
                f"world={DEFAULT_WORLD}",
                f"backend={DEFAULT_BACKEND}",
                "preset=map-build",
                "agent_engine=direct-runner",
                "evidence_lane=world-public-labels",
                f"seed={DEFAULT_SEED}",
                "scenario_setup=baseline",
                f"output_dir={row_dir / 'direct-map-build-world-public' / 'run'}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "map-build",
                "preset": "map-build",
                "evidence_lane": "world-public-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Map-build and actionability changes need a map-build lane gate.",
            rule_ids=("map_build",),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-cleanup-runtime-prior-consumer",
            row_kind="product_run",
            command=[
                *_cleanup_command(
                    row_dir=row_dir,
                    row_id="direct-cleanup-runtime-prior-consumer",
                    agent_engine="direct-runner",
                    evidence_lane="world-public-labels",
                ),
                "runtime_map_prior=${direct-map-build-world-public:runtime_metric_map.json}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "world-public-labels",
                "runtime_map_prior": "required",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Map-build changes need a cleanup consumer gate with the runtime-map prior.",
            rule_ids=("map_build",),
            requirements=("just", "python_env", "runtime_map_prior"),
            expense="local-sim",
            row_dir=row_dir,
        ),
    ]


def _map_build_consumer_model_matrix_row(
    *,
    output_root: Path,
    row_dir: Path,
    provider_profile: str,
) -> dict[str, Any]:
    row_id = f"map-build-consumer-openai-agents-sdk-{provider_profile}"
    return _row(
        row_id=row_id,
        row_kind="live_agent_eval",
        command=_eval_suite_command(
            suite="map_build_consumer",
            budget="focused",
            output_root=output_root,
            stamp=row_id,
            agent_engine="openai-agents-sdk",
            provider_profile=provider_profile,
            live_execution="run",
        ),
        axes={
            "agent_engine": "openai-agents-sdk",
            "provider_profile": provider_profile,
            "intent": "map-build-consumer",
            "suite": "map_build_consumer",
            "evidence_lane": "world-public-labels",
            "backend": DEFAULT_BACKEND,
            "world": DEFAULT_WORLD,
            "parallel_group_id": "map_build_consumer_2026_06_24",
            "provider_cell_count": str(len(MAP_BUILD_CONSUMER_MODEL_MATRIX_PROVIDER_PROFILES)),
            "default_local_concurrency_width": "1",
            "concurrency_policy": ("serial_by_default_for_single_molmospaces_visual_backend_slot"),
        },
        reason=(
            "MapBuild consumer plan/model-matrix proof needs this provider profile "
            "as a first-class availability-or-behavior cell. Run provider cells "
            "serially unless ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS is explicitly "
            "raised and each live row has an isolated stamp/output root."
        ),
        rule_ids=("map_build",),
        requirements=("just", "python_env", "openai_agents_package", "codex_provider"),
        expense="live-agent",
        row_dir=row_dir,
    )


def _cleanup_command(
    *,
    row_dir: Path,
    row_id: str,
    agent_engine: str,
    evidence_lane: str,
    provider_profile: str = "",
    camera_labeler: str = "",
) -> list[str]:
    command = [
        "just",
        "run::surface",
        "surface=household-world",
        f"world={DEFAULT_WORLD}",
        f"backend={DEFAULT_BACKEND}",
        "preset=cleanup",
        f"agent_engine={agent_engine}",
        f"evidence_lane={evidence_lane}",
        f"seed={DEFAULT_SEED}",
        "scenario_setup=relocate-cleanup-related-objects",
        "relocation_count=5",
        f"output_dir={row_dir / row_id / 'run'}",
    ]
    if provider_profile:
        command.append(f"provider_profile={provider_profile}")
    if camera_labeler:
        command.append(f"camera_labeler={camera_labeler}")
    return command


def _eval_suite_command(
    *,
    suite: str,
    budget: str,
    output_root: Path,
    stamp: str,
    agent_engine: str = "direct-runner",
    provider_profile: str = "",
    live_execution: str = "blocked",
) -> list[str]:
    command = [
        "just",
        "agent::eval",
        f"suite={suite}",
        f"budget={budget}",
        f"output_dir={output_root}",
        f"stamp={stamp}",
        f"agent_engine={agent_engine}",
    ]
    if provider_profile:
        command.append(f"provider_profile={provider_profile}")
    if agent_engine != "direct-runner":
        command.append(f"live_execution={live_execution}")
    return command


def _row(
    *,
    row_id: str,
    row_kind: str,
    command: list[str],
    axes: dict[str, str],
    reason: str,
    rule_ids: tuple[str, ...],
    requirements: tuple[str, ...],
    expense: str,
    row_dir: Path,
    requirement: str = "required",
) -> dict[str, Any]:
    return {
        "schema": ROW_SCHEMA,
        "row_id": row_id,
        "row_kind": row_kind,
        "command": [str(item) for item in command],
        "command_display": shlex.join(str(item) for item in command),
        "axes": axes,
        "reason_selected": reason,
        "selection_rule_ids": list(rule_ids),
        "source_signals": [],
        "selected": False,
        "requirement": requirement,
        "expense": expense,
        "requires": list(requirements),
        "status": "skipped_irrelevant",
        "blocker_category": "",
        "skip_reason": "no matching source signal or explicit override",
        "output_artifacts": [],
        "row_dir": str(row_dir / row_id),
    }
