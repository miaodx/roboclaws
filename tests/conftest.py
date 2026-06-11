from __future__ import annotations

from pathlib import Path

import pytest

INTEGRATION_MODULES = {
    # Starts a local MCP server and mutates external CLI MCP registrations when
    # the CLIs are installed. Keep it out of pre-commit fast loops.
    "test_code_mcp_binding_smoke.py",
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


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        layer = _layer_for_item(item)
        item.add_marker(getattr(pytest.mark, layer))


def _layer_for_item(item: pytest.Item) -> str:
    for marker_name in EXPLICIT_LAYER_MARKERS:
        if any(item.iter_markers(marker_name)):
            return marker_name

    path = Path(str(item.path))
    try:
        relative_parts = path.relative_to(Path(str(item.config.rootpath)) / "tests").parts
    except ValueError:
        relative_parts = ()
    if relative_parts and relative_parts[0] in LAYER_DIRS:
        return relative_parts[0]

    filename = path.name
    stem = filename.removeprefix("test_").removesuffix(".py")

    if filename in INTEGRATION_MODULES:
        return "integration"
    if any(part in stem for part in CONTRACT_NAME_PARTS):
        return "contract"
    if any(part in stem for part in REGRESSION_NAME_PARTS):
        return "regression"
    return "unit"
