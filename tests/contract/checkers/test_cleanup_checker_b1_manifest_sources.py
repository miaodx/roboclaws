from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "check_molmo_realworld_cleanup_result.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_molmo_realworld_cleanup_result", CHECKER_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            (
                r"B1 robot consumption manifest source must contain valid JSON object: "
                r".*b1_robot_consumption_manifest\.json"
            ),
        ),
        (
            "[]\n",
            (
                r"B1 robot consumption manifest source must contain a JSON object: "
                r".*b1_robot_consumption_manifest\.json"
            ),
        ),
    ],
)
def test_checker_rejects_malformed_b1_robot_consumption_manifest_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    checker = _load_checker()
    (tmp_path / "b1_robot_consumption_manifest.json").write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        checker._assert_b1_robot_consumption_manifest(tmp_path, _b1_proof())


def test_checker_rejects_missing_b1_robot_consumption_manifest_source(tmp_path: Path) -> None:
    checker = _load_checker()

    with pytest.raises(
        FileNotFoundError,
        match=(
            r"B1 robot consumption manifest source is missing: "
            r".*b1_robot_consumption_manifest\.json"
        ),
    ):
        checker._assert_b1_robot_consumption_manifest(tmp_path, _b1_proof())


def _b1_proof() -> dict[str, object]:
    return {
        "status": "robot_navigation_verified",
        "alignment_status": "verified",
        "navigation_status": "verified",
        "alignment_artifact": "alignment.json",
        "navigation_artifact": "navigation.json",
        "robot_navigation_provenance": "isaac_b1_map12_navigation_smoke",
        "navigation_waypoint_count": 1,
    }
