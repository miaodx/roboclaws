from __future__ import annotations

import json
import os
import shutil
import subprocess
import types
from pathlib import Path

import pytest
from PIL import Image

from roboclaws.molmo_cleanup.renderer_comparison import (
    COMPARISON_SCHEMA,
    FILAMENT_LANE_ID,
    STANDARD_LANE_ID,
    RendererComparisonConfig,
    RendererLane,
    _capture_lane,
    render_renderer_comparison_report,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MOLMO_JUST = REPO_ROOT / "just" / "molmo.just"


def just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local/bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), color=color).save(path)


def _manifest() -> dict[str, object]:
    return {
        "schema": COMPARISON_SCHEMA,
        "scene": {
            "seed": 7,
            "scene_source": "procthor-10k-val",
            "scene_index": 0,
            "include_robot": True,
            "robot_name": "rby1m",
            "generated_mess_count": 10,
        },
        "focus": {
            "object_id": "mug_01",
            "source_receptacle_id": "table_01",
            "target_receptacle_id": "sink_01",
        },
        "lanes": {
            STANDARD_LANE_ID: {
                "status": "success",
                "python_executable": ".venv/bin/python",
                "runtime": {"python_version": "3.12.9", "mujoco_version": "3.3.0"},
                "scene_xml": "/tmp/standard.xml",
                "images": {
                    "snapshot": {
                        "path": "standard/snapshot.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "fpv": {
                        "path": "standard/robot_views/focused.fpv.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "chase": {
                        "path": "standard/robot_views/focused.chase.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "verify": {
                        "path": "standard/robot_views/focused.verify.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "map": {
                        "path": "standard/robot_views/focused.map.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                },
            },
            FILAMENT_LANE_ID: {
                "status": "success",
                "python_executable": ".venv-molmospaces-filament/bin/python",
                "runtime": {"python_version": "3.11.14", "mujoco_version": "3.3.0"},
                "scene_xml": "/tmp/filament.xml",
                "images": {
                    "snapshot": {
                        "path": "filament/snapshot.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "fpv": {
                        "path": "filament/robot_views/focused.fpv.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "chase": {
                        "path": "filament/robot_views/focused.chase.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "verify": {
                        "path": "filament/robot_views/focused.verify.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "map": {
                        "path": "filament/robot_views/focused.map.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                },
            },
        },
    }


def _multi_sample_manifest() -> dict[str, object]:
    manifest = _manifest()
    manifest["focuses"] = [
        {
            "sample_id": "focus-01",
            "object_id": "mug_01",
            "source_receptacle_id": "table_01",
            "target_receptacle_id": "sink_01",
        },
        {
            "sample_id": "focus-02",
            "object_id": "book_01",
            "source_receptacle_id": "desk_01",
            "target_receptacle_id": "shelf_01",
        },
    ]
    for lane_dir, lane in (
        ("standard", manifest["lanes"][STANDARD_LANE_ID]),  # type: ignore[index]
        ("filament", manifest["lanes"][FILAMENT_LANE_ID]),  # type: ignore[index]
    ):
        lane["runtime"]["mujoco_renderer_runtime"] = lane_dir  # type: ignore[index]
        lane["focuses"] = list(manifest["focuses"])  # type: ignore[index]
        lane["samples"] = []  # type: ignore[index]
        for focus in manifest["focuses"]:  # type: ignore[union-attr]
            sample_id = focus["sample_id"]
            lane["samples"].append(  # type: ignore[index,union-attr]
                {
                    "sample_id": sample_id,
                    "focus": dict(focus),
                    "images": {
                        "fpv": {
                            "path": f"{lane_dir}/robot_views/{sample_id}.fpv.png",
                            "dimensions": {"width": 64, "height": 48, "channels": 3},
                        },
                        "chase": {
                            "path": f"{lane_dir}/robot_views/{sample_id}.chase.png",
                            "dimensions": {"width": 64, "height": 48, "channels": 3},
                        },
                        "verify": {
                            "path": f"{lane_dir}/robot_views/{sample_id}.verify.png",
                            "dimensions": {"width": 64, "height": 48, "channels": 3},
                        },
                        "map": {
                            "path": f"{lane_dir}/robot_views/{sample_id}.map.png",
                            "dimensions": {"width": 64, "height": 48, "channels": 3},
                        },
                    },
                }
            )
    return manifest


def test_renderer_comparison_report_renders_side_by_side_sections(tmp_path: Path) -> None:
    manifest = _manifest()
    for lane in manifest["lanes"].values():  # type: ignore[index,union-attr]
        for image in lane["images"].values():  # type: ignore[index,union-attr]
            _write_image(tmp_path / image["path"], color=(20, 80, 120))  # type: ignore[index]

    report_path = render_renderer_comparison_report(manifest, output_dir=tmp_path)
    html = report_path.read_text(encoding="utf-8")

    assert report_path == tmp_path / "report.html"
    assert "MolmoSpaces Renderer Comparison" in html
    assert "Standard MuJoCo and MolmoSpaces Filament MuJoCo" in html
    for title in (
        "Snapshot Comparison",
        "FPV Comparison",
        "Chase Comparison",
        "Verify Comparison",
        "Map Comparison",
    ):
        assert title in html
    assert STANDARD_LANE_ID in html
    assert FILAMENT_LANE_ID in html
    assert "standard/robot_views/focused.fpv.png" in html
    assert "filament/robot_views/focused.verify.png" in html
    assert "Runtime Metadata" in html
    assert "3.11.14" in html


def test_renderer_comparison_report_renders_multiple_robot_view_samples(tmp_path: Path) -> None:
    manifest = _multi_sample_manifest()
    for lane in manifest["lanes"].values():  # type: ignore[index,union-attr]
        for image in lane["images"].values():  # type: ignore[index,union-attr]
            _write_image(tmp_path / image["path"], color=(20, 80, 120))  # type: ignore[index]
        for sample in lane["samples"]:  # type: ignore[index,union-attr]
            for image in sample["images"].values():  # type: ignore[index,union-attr]
                _write_image(tmp_path / image["path"], color=(40, 120, 80))  # type: ignore[index]

    report_path = render_renderer_comparison_report(manifest, output_dir=tmp_path)
    html = report_path.read_text(encoding="utf-8")

    assert "Robot View Samples" in html
    assert "focus-01" in html
    assert "focus-02" in html
    assert "book_01" in html
    assert "standard/robot_views/focus-02.fpv.png" in html
    assert "filament/robot_views/focus-02.verify.png" in html
    assert "Renderer runtime" in html


def test_renderer_comparison_manifest_shape_is_json_serializable() -> None:
    manifest = _manifest()

    encoded = json.dumps(manifest, sort_keys=True)

    assert COMPARISON_SCHEMA in encoded
    assert sorted(manifest["lanes"]) == [FILAMENT_LANE_ID, STANDARD_LANE_ID]  # type: ignore[index]


def test_renderer_comparison_lane_capture_disables_persistent_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER", "1")
    seen_values: list[str | None] = []

    class FakeBackend:
        def __init__(self, **kwargs: object) -> None:
            seen_values.append(os.environ.get("ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER"))
            self.runtime = {"python_version": "3.12.9", "mujoco_version": "3.4.0"}
            self.model_stats = {}
            self.scene_xml = "/tmp/fake.xml"
            self.requested_generated_mess_count = 1
            self.generated_mess_count = 1
            self.scenario = types.SimpleNamespace(
                private_manifest=types.SimpleNamespace(
                    targets=[
                        types.SimpleNamespace(
                            object_id="obj_1",
                            valid_receptacle_ids=["sink_1"],
                        )
                    ]
                )
            )

        def object_locations(self) -> dict[str, str]:
            return {"obj_1": "table_1"}

        def write_snapshot(self, output_path: Path, *, title: str) -> Path:
            _write_image(output_path, color=(20, 20, 20))
            return output_path

        def navigate_to_object(self, object_id: str) -> dict[str, object]:
            return {"ok": True, "object_id": object_id}

        def write_robot_views(
            self,
            output_dir: Path,
            *,
            label: str,
            focus_object_id: str | None = None,
            focus_receptacle_id: str | None = None,
        ) -> dict[str, object]:
            paths: dict[str, str] = {}
            shapes: dict[str, list[int]] = {}
            for kind in ("fpv", "chase", "verify", "map"):
                image_path = output_dir / f"{label}.{kind}.png"
                _write_image(image_path, color=(40, 40, 40))
                paths[kind] = str(image_path)
                shapes[kind] = [48, 64, 3]
            return {"ok": True, "views": paths, "shapes": shapes}

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "roboclaws.molmo_cleanup.renderer_comparison.MolmoSpacesSubprocessBackend",
        FakeBackend,
    )
    runtime = tmp_path / "python"
    runtime.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    runtime.chmod(0o755)

    result = _capture_lane(
        RendererComparisonConfig(
            output_dir=tmp_path,
            standard_python=runtime,
            filament_python=runtime,
        ),
        RendererLane(STANDARD_LANE_ID, runtime, "standard"),
        focuses=None,
    )

    assert result["status"] == "success"
    assert result["focuses"] == [
        {
            "sample_id": "focus-01",
            "object_id": "obj_1",
            "source_receptacle_id": "table_1",
            "target_receptacle_id": "sink_1",
        }
    ]
    assert result["samples"][0]["images"]["fpv"]["path"] == "standard/robot_views/focus-01.fpv.png"
    assert seen_values == ["0"]
    assert os.environ["ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER"] == "1"


def test_molmo_renderer_comparison_recipe_checks_filament_sidecar_before_running(
    tmp_path: Path,
) -> None:
    standard = tmp_path / "standard-python"
    filament = tmp_path / "missing-filament-python"
    standard.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    standard.chmod(0o755)

    env = os.environ.copy()
    env.pop("ROBOCLAWS_JUST_TRACE", None)
    env["ROBOCLAWS_MOLMOSPACES_STANDARD_PYTHON"] = str(standard)
    env["ROBOCLAWS_MOLMOSPACES_FILAMENT_PYTHON"] = str(filament)
    result = subprocess.run(
        [
            just_bin(),
            "-f",
            str(MOLMO_JUST),
            "renderer-comparison",
            "seed=7",
            "generated_mess_count=10",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert (
        "missing Filament MolmoSpaces runtime" in result.stderr
        or "incomplete Filament MolmoSpaces runtime" in result.stderr
    )
    assert str(filament) in result.stderr
    assert "uv sync --project sidecars/molmospaces-filament" in result.stderr
