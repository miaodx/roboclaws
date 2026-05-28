from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from roboclaws.molmo_cleanup.apple2apple_test_grid import (
    GRID_SCHEMA,
    RUNTIME_MAP_PRIOR_PLACEHOLDER,
    build_apple2apple_test_grid,
    row_rerun_command,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_GRID_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_molmo_apple2apple_test_grid.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _rows_by_id(grid: dict) -> dict[str, dict]:
    return {row["row_id"]: row for row in grid["rows"]}


def test_apple2apple_grid_axes_cover_requested_comparison(tmp_path: Path) -> None:
    grid = build_apple2apple_test_grid(output_dir=tmp_path / "grid", task="clean")

    assert grid["schema"] == GRID_SCHEMA
    assert grid["axes"]["map_modes"] == ["online", "offline"]
    assert [item["route_id"] for item in grid["axes"]["agent_routes"]] == [
        "codex-api-router",
        "claude-kimi",
        "claude-mimo-omni",
    ]
    assert [item["lane_id"] for item in grid["axes"]["perception_lanes"]] == [
        "grounding-dino",
        "raw-fpv",
    ]
    assert len(grid["setup_rows"]) == 1
    assert len(grid["rows"]) == 12

    setup_command = grid["setup_rows"][0]["command"]
    assert setup_command[:5] == [
        "just",
        "task::run",
        "semantic-map-build",
        "direct",
        "world-labels",
    ]
    assert "map_bundle=assets/maps/molmospaces-procthor-val-0-7" in setup_command


def test_apple2apple_grid_pins_provider_routes_and_perception(tmp_path: Path) -> None:
    grid = build_apple2apple_test_grid(output_dir=tmp_path / "grid", task="clean")
    rows = _rows_by_id(grid)

    codex_dino = rows["online-codex-api-router-grounding-dino"]
    assert codex_dino["env"] == {"ROBOCLAWS_CODEX_PROVIDER": "codex-env"}
    assert codex_dino["required_env"] == ["CODEX_BASE_URL", "CODEX_API_KEY"]
    assert codex_dino["command"][:5] == [
        "just",
        "task::run",
        "household-cleanup",
        "codex",
        "camera-labels",
    ]
    assert "visual_grounding=grounding-dino" in codex_dino["command"]
    assert not any(item.startswith("runtime_map_prior=") for item in codex_dino["command"])

    offline_raw = rows["offline-claude-mimo-omni-raw-fpv"]
    assert offline_raw["env"] == {
        "ROBOCLAWS_CLAUDE_PROVIDER": "mimo-anthropic",
        "ROBOCLAWS_CLAUDE_MODEL": "mimo-v2-omni",
    }
    assert offline_raw["command"][:5] == [
        "just",
        "task::run",
        "household-cleanup",
        "claude",
        "camera-raw",
    ]
    assert "visual_grounding=grounding-dino" in offline_raw["command"]
    assert f"runtime_map_prior={RUNTIME_MAP_PRIOR_PLACEHOLDER}" in offline_raw["command"]

    claude_kimi = rows["online-claude-kimi-raw-fpv"]
    assert claude_kimi["env"] == {
        "ROBOCLAWS_CLAUDE_PROVIDER": "kimi-anthropic",
        "ROBOCLAWS_CLAUDE_MODEL": "kimi-k2.6",
    }
    assert row_rerun_command(claude_kimi).startswith(
        "ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 "
        "ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic "
        "just task::run household-cleanup claude camera-raw"
    )


def test_apple2apple_grid_accepts_explicit_offline_runtime_map_prior(tmp_path: Path) -> None:
    prior = "output/checks/semantic-map-build-final/seed-7/runtime_metric_map.json"
    grid = build_apple2apple_test_grid(
        output_dir=tmp_path / "grid",
        task="clean",
        runtime_map_prior=prior,
    )
    rows = _rows_by_id(grid)

    assert (
        f"runtime_map_prior={prior}" in rows["offline-codex-api-router-grounding-dino"]["command"]
    )
    assert RUNTIME_MAP_PRIOR_PLACEHOLDER not in " ".join(
        rows["offline-codex-api-router-grounding-dino"]["command"]
    )


def test_apple2apple_grid_script_dry_run_writes_manifest_and_report(tmp_path: Path) -> None:
    run_grid = _load_module(RUN_GRID_PATH, "run_molmo_apple2apple_test_grid")

    status = run_grid.main(["--output-dir", str(tmp_path / "grid"), "--task", "clean"])

    assert status == 0
    manifest_path = tmp_path / "grid" / "apple2apple_test_grid.json"
    report_path = tmp_path / "grid" / "apple2apple_test_grid.html"
    assert manifest_path.is_file()
    assert report_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == GRID_SCHEMA
    assert {row["status"] for row in manifest["rows"]} == {"dry_run"}
    assert "online-codex-api-router-grounding-dino" in report_path.read_text(encoding="utf-8")
