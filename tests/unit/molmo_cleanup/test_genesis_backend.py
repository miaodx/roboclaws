from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from roboclaws.household.genesis_backend import GenesisSubprocessBackend


def test_genesis_backend_reports_missing_runtime(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Genesis Python runtime is missing"):
        GenesisSubprocessBackend(
            run_dir=tmp_path,
            scene_usd_path=tmp_path / "scene.usda",
            python_executable=tmp_path / "missing-python",
        )


def test_genesis_backend_exposes_camera_control_request_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = GenesisSubprocessBackend.__new__(GenesisSubprocessBackend)
    backend.state_path = tmp_path / "state.json"
    backend.python_executable = tmp_path / "python"
    captured: dict[str, object] = {}

    def fake_run_worker(command: str, *args: str) -> dict[str, object]:
        captured["command"] = command
        captured["args"] = args
        return {"ok": True}

    monkeypatch.setattr(backend, "_run_worker", fake_run_worker)
    request_path = tmp_path / "camera_control_request.json"
    request_path.write_text(
        json.dumps({"render_resolution": {"width": 960, "height": 640}, "views": []}),
        encoding="utf-8",
    )

    result = backend.render_camera_control_request(
        tmp_path / "camera_views",
        request_path=request_path,
    )

    assert result["ok"] is True
    assert captured["command"] == "camera_views"
    assert captured["args"] == (
        "--output-dir",
        str(tmp_path / "camera_views"),
        "--camera-request-path",
        str(request_path),
        "--render-width",
        "960",
        "--render-height",
        "640",
    )


def test_genesis_fake_worker_protocol_echoes_runtime_and_camera_views(tmp_path: Path) -> None:
    scene_usd = tmp_path / "scene.usda"
    request_path = tmp_path / "camera_control_request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema": "roboclaws.camera_control.render_views.v1",
                "render_resolution": {"width": 64, "height": 48},
                "lens": {"vertical_fov_deg": 45.0},
                "views": [
                    {
                        "view_id": "room_01",
                        "eye": [0.0, -3.0, 2.0],
                        "target": [0.0, 0.0, 1.0],
                        "up": [0.0, 0.0, 1.0],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    backend = GenesisSubprocessBackend(
        run_dir=tmp_path / "run",
        scene_usd_path=scene_usd,
        python_executable=Path(sys.executable),
        runtime_mode="fake",
    )

    result = backend.render_camera_control_request(
        tmp_path / "views",
        request_path=request_path,
    )

    assert result["ok"] is True
    assert result["runtime"]["runtime_mode"] == "fake"
    assert result["runtime"]["renderer_mode"] == "fake_genesis_protocol"
    assert result["visual_artifact_provenance"] == "fake_protocol_placeholder_image"
    assert (tmp_path / "views" / "room_01.png").is_file()
