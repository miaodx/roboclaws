from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_CAMERA_COMPARISON_PATH = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_robot_camera_apple2apple_comparison.py"
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_robot_camera_image_diff_reports_color_residual(tmp_path: Path) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_color_residual",
    )
    left_path = tmp_path / "mujoco.png"
    right_path = tmp_path / "isaac.png"
    Image.new("RGB", (12, 8), (120, 120, 120)).save(left_path)
    Image.new("RGB", (12, 8), (60, 60, 60)).save(right_path)

    diff = run_camera._image_diff(left_path, right_path)

    assert diff["mean_abs_rgb"] == 60.0
    assert diff["diff_gt_40_fraction"] == 1.0
    assert diff["diff_gt_80_fraction"] == 0.0
    assert diff["residual"]["schema"] == "robot_camera_render_residual_diagnostics_v1"
    assert diff["residual"]["residual_class"] == "view_dependent_color_residual"
    assert diff["residual"]["rgb_gain_oracle"]["mean_abs_rgb_after_gain"] == 0.0


def test_robot_camera_residual_triage_prioritizes_geometry_edges() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_geometry_residual",
    )
    left = Image.new("RGB", (32, 32), (0, 0, 0))
    ImageDraw.Draw(left).rectangle((0, 0, 15, 31), fill=(255, 255, 255))
    right = Image.new("RGB", (32, 32), (0, 0, 0))

    residual = run_camera._render_residual_diagnostics(left, right)

    assert residual["residual_class"] == "geometry_or_texture_edge_residual"
    assert residual["edge_abs_diff"] > 8.0
    summary = run_camera._summary(
        [
            {
                "status": "success",
                "image_diffs": {
                    "fpv": {
                        "mean_abs_rgb": 80.0,
                        "residual": residual,
                    },
                    "chase": {
                        "mean_abs_rgb": 32.0,
                        "residual": {
                            "residual_class": "low_residual",
                            "rgb_gain_oracle": {"mean_abs_rgb_after_gain": 30.0},
                            "edge_abs_diff": 1.0,
                        },
                    },
                },
            }
        ]
    )

    triage = summary["residual_triage"]
    assert triage["schema"] == "robot_camera_render_residual_triage_v1"
    assert triage["status"] == "render_domain_geometry_or_texture_residual"
    assert triage["views"]["fpv"]["residual_classes"] == {"geometry_or_texture_edge_residual": 1}
    assert "geometry/material/texture" in triage["recommended_next_action"]


def test_robot_camera_contract_diagnostics_flags_static_isaac_head_pitch_gap() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_contract_diagnostics",
    )
    robot_pose = {
        "x": 6.37057,
        "y": 8.8752,
        "theta": 1.57079632679,
        "yaw_deg": 90.0,
        "head_pitch": 0.653613,
        "pose_source": "apple2apple_shared_robot_pose",
    }
    location = {
        "status": "success",
        "robot_pose": robot_pose,
        "contracts": {
            "mujoco": {
                "agent_facing_fpv": {
                    "source": "robot_0/head_camera",
                    "robot_mounted": True,
                    "head_camera_equivalent": False,
                },
                "report_verify_view": {"source": "mujoco_focus_camera"},
                "robot_pose": dict(robot_pose),
            },
            "isaac": {
                "agent_facing_fpv": {
                    "source": "isaac_lab_camera_rgb_robot_mounted_head_camera:fpv",
                    "camera_prim_path": "/World/robot_0/head_camera",
                    "robot_mounted": True,
                    "head_camera_equivalent": False,
                },
                "report_verify_view": {
                    "source": "isaac_lab_camera_rgb_semantic_pose_robot_views:verify"
                },
                "camera_prim_path": "/World/robot_0/head_camera",
                "robot_pose": dict(robot_pose),
                "robot_asset": {
                    "status": "imported",
                    "head_camera_mounted": True,
                    "head_camera_equivalent": False,
                    "head_camera_prim_path": "/World/robot_0/head_camera",
                    "head_link_name": "link_head_2",
                    "import_summary": {
                        "import_method": "urdf_visual_static_usd_fallback",
                        "static_only": True,
                        "urdf": {"required_joints": ["base_x", "base_y", "head_1"]},
                        "converter": {
                            "fallback": {
                                "status": "ready",
                                "missing_mesh_count": 0,
                                "unsupported_mesh_count": 4,
                            }
                        },
                    },
                },
            },
        },
        "camera_diagnostics": {
            "mujoco": {
                "views": {
                    "fpv": {
                        "schema": "mujoco_fixed_camera_diagnostics_v1",
                        "status": "ready",
                        "camera_type": "fixed",
                        "camera_name": "robot_0/head_camera",
                        "world_position": [6.37, 8.87, 1.55],
                        "fovy_deg": 45.0,
                    }
                }
            },
            "isaac": {
                "views": {
                    "fpv": {
                        "schema": "isaac_usd_camera_diagnostics_v1",
                        "status": "ready",
                        "camera_type": "usd_camera_prim",
                        "prim_path": "/World/robot_0/head_camera",
                        "focal_length_mm": 24.0,
                        "horizontal_aperture_mm": 20.955,
                    }
                }
            },
        },
    }

    per_location = run_camera._location_camera_contract_diagnostics(location)
    summary = run_camera._camera_contract_diagnostics([location])

    assert per_location["fpv_head_camera_contract"] is True
    assert per_location["robot_pose_match"] is True
    assert per_location["isaac_robot_import"]["static_only"] is True
    assert per_location["fpv_camera_metadata"]["mujoco"]["camera_name"] == "robot_0/head_camera"
    assert per_location["fpv_camera_metadata"]["isaac"]["prim_path"] == (
        "/World/robot_0/head_camera"
    )
    assert per_location["head_articulation"]["status"] == ("isaac_static_head_pitch_not_applied")
    assert per_location["chase_contract"]["same_camera_contract"] is False
    assert summary["status"] == "fpv_contract_shared_with_static_head_articulation_gap"
    assert summary["fpv_head_camera_contract_count"] == 1
    assert summary["robot_pose_match_count"] == 1
    assert summary["isaac_static_head_pitch_gap_count"] == 1


def test_robot_camera_contract_diagnostics_accepts_static_head_camera_pitch_correction() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_contract_pitch_correction",
    )
    robot_pose = {
        "x": 6.37057,
        "y": 8.8752,
        "theta": 1.57079632679,
        "yaw_deg": 90.0,
        "head_pitch": 0.653613,
        "pose_source": "apple2apple_shared_robot_pose",
    }
    location = {
        "status": "success",
        "robot_pose": robot_pose,
        "contracts": {
            "mujoco": {
                "agent_facing_fpv": {
                    "source": "robot_0/head_camera",
                    "robot_mounted": True,
                    "head_camera_equivalent": False,
                },
                "report_verify_view": {"source": "mujoco_focus_camera"},
                "robot_pose": dict(robot_pose),
            },
            "isaac": {
                "agent_facing_fpv": {
                    "source": "isaac_lab_camera_rgb_robot_mounted_head_camera:fpv",
                    "camera_prim_path": "/World/robot_0/head_camera",
                    "robot_mounted": True,
                    "head_camera_equivalent": False,
                },
                "report_verify_view": {
                    "source": "isaac_lab_camera_rgb_semantic_pose_robot_views:verify"
                },
                "camera_prim_path": "/World/robot_0/head_camera",
                "robot_pose": dict(robot_pose),
                "robot_asset": {
                    "status": "imported",
                    "head_camera_mounted": True,
                    "head_camera_equivalent": False,
                    "head_camera_prim_path": "/World/robot_0/head_camera",
                    "head_link_name": "link_head_2",
                    "import_summary": {
                        "import_method": "urdf_visual_static_usd_fallback",
                        "static_only": True,
                    },
                },
            },
        },
        "camera_diagnostics": {
            "mujoco": {
                "views": {
                    "fpv": {
                        "schema": "mujoco_fixed_camera_diagnostics_v1",
                        "status": "ready",
                        "camera_type": "fixed",
                        "camera_name": "robot_0/head_camera",
                        "world_position": [6.37057, 8.8752, 1.55],
                        "fovy_deg": 45.0,
                    }
                }
            },
            "isaac": {
                "views": {
                    "fpv": {
                        "schema": "isaac_usd_camera_diagnostics_v1",
                        "status": "ready",
                        "camera_type": "usd_camera_prim",
                        "prim_path": "/World/robot_0/head_camera",
                        "world_matrix_rowmajor": [
                            1.0,
                            0.0,
                            0.0,
                            0.0,
                            0.0,
                            1.0,
                            0.0,
                            0.0,
                            0.0,
                            0.0,
                            1.0,
                            0.0,
                            6.37057,
                            8.8752,
                            1.545,
                            1.0,
                        ],
                        "robot_pose_stage_application": {
                            "schema": "isaac_robot_head_camera_pose_application_v1",
                            "status": "applied",
                            "head_pitch": 0.653613,
                            "head_pitch_applied": True,
                        },
                    }
                }
            },
        },
    }

    per_location = run_camera._location_camera_contract_diagnostics(location)
    summary = run_camera._camera_contract_diagnostics([location])

    assert per_location["head_articulation"]["status"] == (
        "isaac_static_head_pitch_applied_to_head_camera"
    )
    assert per_location["head_articulation"]["isaac_head_pitch_applied"] is True
    assert per_location["fpv_world_pose_delta"]["position_delta_m"] == 0.005
    assert summary["status"] == "fpv_contract_shared_with_static_head_camera_pitch_correction"
    assert summary["isaac_static_head_pitch_gap_count"] == 0
    assert summary["fpv_world_pose_delta_summary"]["status"] == "fpv_world_pose_aligned"
    assert summary["fpv_world_pose_delta_summary"]["position_delta_m_max"] == 0.005


def test_robot_camera_render_contract_diagnostics_reports_light_shadow_delta(
    tmp_path: Path,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_render_contract",
    )
    mujoco_xml = tmp_path / "scene.xml"
    mujoco_xml.write_text(
        """<mujoco>
  <asset>
    <texture name="tex_bed" type="2d" file="textures/bed.png"/>
    <material name="mat_bed" texture="tex_bed" rgba="1 1 1 1"/>
  </asset>
  <worldbody>
    <light name="mujoco_light"/>
    <body name="bed_1">
      <geom name="bed_1_visual_0" mesh="bed_mesh" material="mat_bed"/>
    </body>
  </worldbody>
</mujoco>
""",
        encoding="utf-8",
    )
    isaac_usd = tmp_path / "scene.usda"
    isaac_usd.write_text(
        """#usda 1.0
def Xform "World"
{
  def Scope "Looks"
  {
    def Material "mat_bed"
    {
      def Shader "PreviewSurface"
      {
        uniform token info:id = "UsdPreviewSurface"
        color3f inputs:diffuseColor = (1, 1, 1)
      }
      def Shader "DiffuseTexture"
      {
        asset inputs:file = @/tmp/textures/bed.png@
      }
    }
  }
  def Xform "bed_1"
  {
    def Mesh "mesh"
    {
      rel material:binding = </World/Looks/mat_bed>
    }
  }
  def DistantLight "key"
  {
    float inputs:intensity = 500
  }
  def DomeLight "sky"
  {
    float inputs:intensity = 50
  }
  def Mesh "wall"
  {
    bool primvars:doNotCastShadows = true
  }
}
""",
        encoding="utf-8",
    )
    manifest = {
        "locations": [
            {
                "status": "success",
                "target": {"kind": "receptacle", "target_id": "bed_1"},
                "image_diffs": {
                    "fpv": {"residual": {"residual_class": "geometry_or_texture_edge_residual"}},
                    "chase": {"residual": {"residual_class": "geometry_or_texture_edge_residual"}},
                },
            }
        ],
        "summary": {},
    }
    mujoco_state = {"scene_xml": str(mujoco_xml), "robot_xml": "robot.xml"}
    isaac_state = {
        "scene_usd": str(isaac_usd),
        "scene_binding_diagnostics": {
            "schema": "binding_v1",
            "status": "selected_bound",
            "receptacle_bindings": {
                "bed_1": {
                    "status": "bound",
                    "public_id": "bed_1",
                    "kind": "receptacle",
                    "usd_prim_path": "/World/bed_1",
                    "geometry_status": "renderable",
                }
            },
        },
    }

    run_camera._attach_state_artifact_summaries(
        manifest,
        output_dir=tmp_path,
        mujoco_state=mujoco_state,
        isaac_state=isaac_state,
    )
    (tmp_path / "mujoco_state.json").write_text(
        __import__("json").dumps(mujoco_state), encoding="utf-8"
    )
    (tmp_path / "isaac_state.json").write_text(
        __import__("json").dumps(isaac_state), encoding="utf-8"
    )

    run_camera._attach_render_contract_diagnostics(manifest, output_dir=tmp_path)

    summary = manifest["summary"]["render_contract_diagnostics"]
    location = manifest["locations"][0]["render_contract_diagnostics"]
    assert summary["status"] == "lighting_shadow_contract_delta"
    assert summary["mujoco_light_count"] == 1
    assert summary["isaac_light_count"] == 2
    assert summary["isaac_shadow_disabled_prim_count"] == 1
    assert summary["target_contract_delta_counts"] == {"material_texture_names_match": 1}
    assert location["target_contract_delta"]["status"] == "material_texture_names_match"


def test_robot_camera_render_contract_diagnostics_prioritizes_missing_target_binding(
    tmp_path: Path,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_render_contract_missing_binding",
    )
    mujoco_xml = tmp_path / "scene.xml"
    mujoco_xml.write_text(
        """<mujoco>
  <asset><material name="mat_counter"/></asset>
  <worldbody>
    <body name="counter_1"><geom name="counter_1_visual_0" material="mat_counter"/></body>
  </worldbody>
</mujoco>
""",
        encoding="utf-8",
    )
    isaac_usd = tmp_path / "scene.usda"
    isaac_usd.write_text(
        """#usda 1.0
def Xform "World"
{
  def Xform "counter_1"
  {
    def Mesh "mesh"
    {
    }
  }
}
""",
        encoding="utf-8",
    )
    manifest = {
        "locations": [
            {
                "status": "success",
                "target": {"kind": "receptacle", "target_id": "counter_1"},
                "image_diffs": {
                    "fpv": {"residual": {"residual_class": "low_residual"}},
                    "chase": {"residual": {"residual_class": "geometry_or_texture_edge_residual"}},
                },
            }
        ],
        "summary": {},
    }
    (tmp_path / "mujoco_state.json").write_text(
        __import__("json").dumps({"scene_xml": str(mujoco_xml)}),
        encoding="utf-8",
    )
    (tmp_path / "isaac_state.json").write_text(
        __import__("json").dumps(
            {
                "scene_usd": str(isaac_usd),
                "scene_binding_diagnostics": {
                    "receptacle_bindings": {
                        "counter_1": {
                            "status": "bound",
                            "public_id": "counter_1",
                            "kind": "receptacle",
                            "usd_prim_path": "/World/counter_1",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    run_camera._attach_render_contract_diagnostics(manifest, output_dir=tmp_path)

    summary = manifest["summary"]["render_contract_diagnostics"]
    location = manifest["locations"][0]["render_contract_diagnostics"]
    assert summary["status"] == "target_material_texture_or_binding_gap"
    assert summary["high_priority_target_delta_count"] == 1
    assert location["target_contract_delta"]["status"] == "missing_object_binding_evidence"


def test_robot_camera_patch_isaac_pose_can_set_comparison_color_profile(
    tmp_path: Path,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_color_profile_override",
    )
    state_path = tmp_path / "isaac_state.json"
    state_path.write_text(json.dumps({"semantic_pose_state": {}}), encoding="utf-8")

    run_camera._patch_isaac_robot_pose(
        state_path,
        {"x": 1.0, "y": 2.0, "theta": 0.5},
        target={"kind": "receptacle", "target_id": "sink_01"},
        color_profile={
            "backend_rgb_gain": {"isaaclab_subprocess": [0.9, 0.8, 0.7]},
            "backend_rgb_gain_source": "unit-comparison-profile",
        },
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["semantic_pose_state"]["comparison_pose_target"]["target_id"] == "sink_01"
    assert state["robot_view_color_profile_override"]["backend_rgb_gain"][
        "isaaclab_subprocess"
    ] == [0.9, 0.8, 0.7]

    run_camera._patch_isaac_robot_pose(
        state_path,
        {"x": 1.0, "y": 2.0, "theta": 0.5},
        target={"kind": "receptacle", "target_id": "sink_01"},
        color_profile={},
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "robot_view_color_profile_override" not in state
