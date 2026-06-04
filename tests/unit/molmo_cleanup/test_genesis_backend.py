from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from roboclaws.household.genesis_backend import GenesisSubprocessBackend
from scripts.genesis_cleanup.genesis_backend_worker import (
    GENESIS_COLOR_PROFILE_RGB_GAIN,
    GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT,
    GENESIS_COLOR_PROFILE_VIEW_TONE_ADJUSTMENT,
    GENESIS_RENDER_LIGHTING_PROFILE,
    _extract_materialized_usd_visual_asset,
    _extract_render_only_visual_mesh,
    _genesis_color_profile,
    _genesis_lighting_profile,
    _genesis_scene,
)


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


def test_genesis_render_only_visual_mesh_extractor_uses_usd_geometry(tmp_path: Path) -> None:
    pytest.importorskip("pxr")
    scene_usd = tmp_path / "scene.usda"
    scene_usd.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Mesh "Triangle"
    {
        point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        int[] faceVertexCounts = [3]
        int[] faceVertexIndices = [0, 1, 2]
    }
}
""",
        encoding="utf-8",
    )

    result = _extract_render_only_visual_mesh(scene_usd, tmp_path / "mesh.obj")

    assert result["source_usd"] == str(scene_usd)
    assert result["source_mesh_count"] == 1
    assert result["vertex_count"] == 3
    assert result["triangle_count"] == 1
    assert (tmp_path / "mesh.obj").read_text(encoding="utf-8").count("\nf ") == 1


def test_genesis_materialized_visual_asset_preserves_texture_material(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pxr")
    texture_dir = tmp_path / "textures"
    texture_dir.mkdir()
    Image.new("RGB", (2, 2), (200, 200, 200)).save(texture_dir / "floor.png")
    scene_usd = tmp_path / "scene.usda"
    scene_usd.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Mesh "Triangle"
    {
        point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        int[] faceVertexCounts = [3]
        int[] faceVertexIndices = [0, 1, 2]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (0, 1)] (
            interpolation = "vertex"
        )
        rel material:binding = </World/Looks/Material_01>
    }

    def Scope "Looks"
    {
        def Material "Material_01"
        {
            token outputs:surface.connect =
                </World/Looks/Material_01/PreviewSurface.outputs:surface>

            def Shader "PreviewSurface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect =
                    </World/Looks/Material_01/DiffuseTexture.outputs:rgb>
                float inputs:opacity = 1
                token outputs:surface
            }

            def Shader "DiffuseTexture"
            {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @textures/floor.png@
                color4f inputs:fallback = (0.2, 0.3, 0.4, 1)
                float3 inputs:scale = (0.6, 0.5, 0.4)
                float2 inputs:st.connect = </World/Looks/Material_01/StReader.outputs:result>
                float3 outputs:rgb
            }

            def Shader "StReader"
            {
                uniform token info:id = "UsdPrimvarReader_float2"
                token inputs:varname = "st"
                float2 outputs:result
            }
        }
    }
}
""",
        encoding="utf-8",
    )

    result = _extract_materialized_usd_visual_asset(scene_usd, tmp_path / "visual_asset")

    obj_text = Path(str(result["mesh_path"])).read_text(encoding="utf-8")
    mtl_text = Path(str(result["material_path"])).read_text(encoding="utf-8")
    assert result["source_mesh_count"] == 1
    assert result["material_count"] == 1
    assert result["textured_material_count"] == 1
    assert result["texture_count"] == 1
    assert result["baked_texture_count"] == 1
    assert result["triangle_count"] == 1
    assert result["textured_triangle_count"] == 1
    assert "vt " in obj_text
    assert "usemtl Material_01" in obj_text
    assert "Kd 1.000000 1.000000 1.000000" in mtl_text
    assert "map_Kd textures/floor_baked_" in mtl_text
    baked_texture = next((tmp_path / "visual_asset" / "textures").glob("floor_baked_*.png"))
    assert baked_texture.is_file()
    assert Image.open(baked_texture).convert("RGB").getpixel((0, 0)) == (120, 100, 80)


def test_genesis_scene_applies_visual_lighting_options() -> None:
    captured: dict[str, object] = {}

    class FakeViewerOptions:
        def __init__(self, **kwargs: object) -> None:
            captured["viewer_options"] = kwargs

    class FakeVisOptions:
        def __init__(self, **kwargs: object) -> None:
            captured["vis_options"] = kwargs

    class FakeRasterizer:
        pass

    class FakeScene:
        def __init__(self, **kwargs: object) -> None:
            captured["scene"] = kwargs

    class FakeOptions:
        ViewerOptions = FakeViewerOptions
        VisOptions = FakeVisOptions

    class FakeRenderers:
        Rasterizer = FakeRasterizer

    class FakeGenesis:
        options = FakeOptions
        renderers = FakeRenderers
        Scene = FakeScene

    scene = _genesis_scene(FakeGenesis, width=960, height=640, vertical_fov=45.0)

    assert isinstance(scene, FakeScene)
    assert captured["viewer_options"] == {
        "res": (960, 640),
        "camera_pos": (0.0, -3.0, 2.0),
        "camera_lookat": (0.0, 0.0, 1.0),
        "camera_fov": 45.0,
    }
    assert captured["vis_options"] == {
        "ambient_light": tuple(GENESIS_RENDER_LIGHTING_PROFILE["ambient_light"]),
        "background_color": tuple(GENESIS_RENDER_LIGHTING_PROFILE["background_color"]),
        "shadow": GENESIS_RENDER_LIGHTING_PROFILE["shadow"],
        "lights": [
            {
                "type": "directional",
                "dir": (-1.0, -1.0, -1.0),
                "color": (1.0, 1.0, 1.0),
                "intensity": 3.0,
            },
            {
                "type": "directional",
                "dir": (1.0, 1.0, -0.6),
                "color": (1.0, 0.96, 0.9),
                "intensity": 0.8,
            },
            {
                "type": "directional",
                "dir": (0.0, -1.0, -0.35),
                "color": (0.9, 0.95, 1.0),
                "intensity": 0.45,
            },
        ],
    }


def test_genesis_lighting_profile_uses_request_environment_fill() -> None:
    profile = _genesis_lighting_profile(
        {
            "profile_id": "scene_probe_mujoco_headlight_fill_v1",
            "mujoco_headlight_ambient": [0.35, 0.35, 0.35],
            "mujoco_headlight_diffuse": [0.4, 0.4, 0.4],
            "genesis_ambient_light": [0.37, 0.37, 0.37],
            "genesis_background_color": [0.04, 0.08, 0.12],
            "genesis_shadow": False,
            "genesis_directional_lights": [
                {"dir": [-1.0, -1.0, -1.0], "color": [1.0, 1.0, 1.0], "intensity": 3.0},
                {"dir": [1.0, 1.0, -0.6], "color": [1.0, 0.96, 0.9], "intensity": 0.8},
            ],
        }
    )

    assert profile["profile_id"] == "scene_probe_mujoco_headlight_fill_v1"
    assert profile["ambient_light"] == pytest.approx([0.37, 0.37, 0.37])
    assert profile["mujoco_headlight_ambient"] == pytest.approx([0.35, 0.35, 0.35])
    assert profile["mujoco_headlight_diffuse"] == pytest.approx([0.4, 0.4, 0.4])
    assert profile["shadow"] is False
    assert len(profile["lights"]) == 2
    assert profile["lights"][1]["intensity"] == pytest.approx(0.8)


def test_genesis_color_profile_adds_explicit_luminance_calibration() -> None:
    profile = _genesis_color_profile(
        {
            "profile_id": "display_srgb_soft_highlight_v1",
            "backend_luminance_gain": {"molmospaces-mujoco": 1.0},
            "backend_luminance_gain_source": "existing-source",
        }
    )

    assert profile["backend_luminance_gain"]["molmospaces-mujoco"] == 1.0
    assert profile["backend_luminance_gain"]["genesis-prepared-usd"] == pytest.approx(0.94)
    assert profile["backend_rgb_gain"]["genesis-prepared-usd"] == pytest.approx(
        GENESIS_COLOR_PROFILE_RGB_GAIN
    )
    assert profile["backend_tone_adjustment"]["genesis-prepared-usd"] == pytest.approx(
        GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT
    )
    assert profile["backend_view_tone_adjustment"]["genesis-prepared-usd"][
        "room_01_room_2"
    ] == pytest.approx(GENESIS_COLOR_PROFILE_VIEW_TONE_ADJUSTMENT["room_01_room_2"])
    assert "existing-source" in profile["backend_luminance_gain_source"]
    assert "Genesis materialized USD visual probe 2026-06-04" in profile[
        "backend_luminance_gain_source"
    ]
    assert "Genesis materialized USD visual probe 2026-06-04" in profile[
        "backend_rgb_gain_source"
    ]
    assert "Genesis baked-texture visual probe 2026-06-04" in profile[
        "backend_tone_adjustment_source"
    ]
