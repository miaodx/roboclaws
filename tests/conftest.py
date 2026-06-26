from __future__ import annotations

from pathlib import Path

import pytest

INTEGRATION_MODULES = {
    # Starts a local MCP server and mutates external CLI MCP registrations when
    # the CLIs are installed. Keep it out of pre-commit fast loops.
    "test_code_mcp_binding_smoke.py",
}

LOCAL_ASSET_MODULES = {
    # These validate private B1 / Agibot map exports or robot-data-lab scene
    # assets that are present on local workstations but not in GitHub checkout.
    "test_b1_map12_alignment_fit_cli.py",
    "test_b1_map12_base_metric_map.py",
    "test_b1_map12_base_metric_sidecar.py",
    "test_b1_map12_correspondence_review_cli.py",
    "test_b1_map12_label_tool.py",
    "test_b1_map12_manual_alignment_overlay_cli.py",
    "test_b1_map12_verified_alignment.py",
    "test_b1_scene_topdown_diagnostic.py",
    "test_molmospaces_source_pin.py",
}

LOCAL_ASSET_TESTS = {
    "test_agibot_map_context_scripts.py": {
        "test_agibot_nav_json_artifact_source_rejects_invalid_payloads",
        "test_agibot_nav_raw_map_source_rejects_malformed_gzip_json",
        "test_agibot_nav_raw_map_source_rejects_non_object_gzip_json",
        "test_agibot_nav_raw_map_source_rejects_plain_json_file",
    },
    "test_base_waypoint_builder.py": {
        "test_base_waypoint_builder_preserves_b1_map12_waypoints",
    },
    "test_check_molmo_realworld_cleanup_result.py": {
        "test_checker_accepts_b1_robot_consumption_proof_without_rby1m_readiness",
        "test_checker_rejects_b1_robot_consumption_manifest_drift",
        "test_checker_rejects_b1_robot_consumption_without_manifest",
        "test_checker_rejects_b1_robot_consumption_without_verified_navigation",
    },
    "test_cross_environment_semantic_map_parity.py": {
        "test_b1_uses_dt_room_reference_and_alignment_correspondence_manifest",
    },
    "test_nav2_map_bundle_contract.py": {
        "test_base_metric_map_v1_validation_accepts_b1_bundle",
        "test_base_metric_map_v1_validation_rejects_contract_violations",
    },
    "test_scene_room_semantic_overlay.py": {
        "test_b1_base_metric_map_materializes_review_labels_without_retargeting_map",
    },
}

LAYER_DIRS = ("local", "slow", "integration", "contract", "regression", "unit")

REGRESSION_NAME_PARTS = (
    "refactor_regression",
    "view_experiment",
)

CONTRACT_NAME_PARTS = (
    "appliance",
    "artifact",
    "bridge",
    "check_",
    "coding_agent",
    "contract",
    "harness",
    "just_recipes",
    "mcp",
    "openclaw",
    "realworld",
    "replay",
    "report",
    "run_artifacts",
    "transcript",
    "verify_",
)

EXPLICIT_LAYER_MARKERS = ("local", "slow", "integration", "contract", "regression", "unit")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        layer = _layer_for_item(item)
        item.add_marker(getattr(pytest.mark, layer))


def _layer_for_item(item: pytest.Item) -> str:
    for marker_name in EXPLICIT_LAYER_MARKERS:
        if any(item.iter_markers(marker_name)):
            return marker_name

    path = Path(str(item.path))
    filename = path.name
    stem = filename.removeprefix("test_").removesuffix(".py")

    if filename in LOCAL_ASSET_MODULES:
        return "local"
    if item.name.split("[", 1)[0] in LOCAL_ASSET_TESTS.get(filename, set()):
        return "local"
    if filename in INTEGRATION_MODULES:
        return "integration"
    directory_layer = _directory_layer(item, path)
    if directory_layer:
        return directory_layer
    if any(part in stem for part in CONTRACT_NAME_PARTS):
        return "contract"
    if any(part in stem for part in REGRESSION_NAME_PARTS):
        return "regression"
    return "unit"


def _directory_layer(item: pytest.Item, path: Path) -> str:
    try:
        relative_parts = path.relative_to(Path(str(item.config.rootpath)) / "tests").parts
    except ValueError:
        return ""
    if relative_parts and relative_parts[0] in LAYER_DIRS:
        return relative_parts[0]
    return ""
