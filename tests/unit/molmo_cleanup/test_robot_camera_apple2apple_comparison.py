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


def test_robot_camera_comparison_pins_isaac_mess_objects_to_mujoco(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_pinned_mess",
    )
    commands: list[list[str]] = []
    output_dir = tmp_path / "comparison"
    mujoco_state_path = output_dir / "mujoco_state.json"
    isaac_state_path = output_dir / "isaac_state.json"

    def fake_run_json(command: list[str], *, cwd: Path) -> dict:
        commands.append(command)
        if command[1].endswith("molmospaces_subprocess_worker.py") and "init" in command:
            mujoco_state_path.parent.mkdir(parents=True, exist_ok=True)
            mujoco_state_path.write_text(
                json.dumps(
                    {
                        "receptacles": {},
                        "objects": {},
                        "private_manifest": {
                            "targets": [
                                {"object_id": "apple_1", "valid_receptacle_ids": ["fridge_1"]},
                                {"object_id": "plate_1", "valid_receptacle_ids": ["sink_1"]},
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            return {
                "backend": "molmospaces_subprocess",
                "ok": True,
                "private_manifest": {
                    "targets": [
                        {"object_id": "apple_1", "valid_receptacle_ids": ["fridge_1"]},
                        {"object_id": "plate_1", "valid_receptacle_ids": ["sink_1"]},
                    ]
                },
            }
        if command[1].endswith("isaac_lab_backend_worker.py") and "init" in command:
            isaac_state_path.write_text(
                json.dumps(
                    {
                        "scene_binding_diagnostics": {},
                        "receptacle_index": {},
                        "object_index": {},
                    }
                ),
                encoding="utf-8",
            )
            return {"backend": "isaaclab_subprocess", "ok": True}
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(run_camera, "_run_json", fake_run_json)
    monkeypatch.setattr(
        run_camera,
        "_select_comparison_targets",
        lambda *args, **kwargs: {"selected_targets": [], "status": "unit_no_targets"},
    )

    args = type(
        "Args",
        (),
        {
            "output_dir": output_dir,
            "mujoco_python": Path("python"),
            "isaac_python": Path("isaac-python"),
            "seed": 6,
            "scene_source": "procthor-10k-val",
            "scene_index": 0,
            "generated_mess_count": 2,
            "render_width": 540,
            "render_height": 360,
            "location_count": 1,
            "scene_usd_path": tmp_path / "scene.usda",
            "isaac_robot_view_color_profile_path": None,
        },
    )()
    args.scene_usd_path.write_text("#usda 1.0\n", encoding="utf-8")

    manifest = run_camera.run_comparison(args)

    isaac_init_command = commands[1]
    assert manifest["status"] == "blocked"
    assert manifest["mess_generation"]["status"] == "isaac_pinned_to_mujoco_generated_mess"
    assert manifest["mess_generation"]["pinned_generated_mess_object_ids"] == [
        "apple_1",
        "plate_1",
    ]
    assert isaac_init_command.count("--generated-mess-object-id") == 2
    assert "--generated-mess-object-id" in isaac_init_command
    assert isaac_init_command[-4:] == [
        "--generated-mess-object-id",
        "apple_1",
        "--generated-mess-object-id",
        "plate_1",
    ]


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
                        "render_resolution": {"width": 540, "height": 360},
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
    assert per_location["fpv_lens_delta"]["status"] == "fpv_lens_contract_delta"
    assert per_location["fpv_lens_delta"]["isaac_vertical_fov_deg"] == 32.454394
    assert per_location["head_articulation"]["status"] == ("isaac_static_head_pitch_not_applied")
    assert per_location["chase_contract"]["same_camera_contract"] is False
    assert summary["status"] == "fpv_contract_shared_with_static_head_articulation_gap"
    assert summary["fpv_head_camera_contract_count"] == 1
    assert summary["robot_pose_match_count"] == 1
    assert summary["isaac_static_head_pitch_gap_count"] == 1
    assert summary["fpv_lens_gap_count"] == 1


def test_robot_camera_contract_diagnostics_recognizes_robot_relative_chase_contract() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_chase_contract",
    )

    chase = run_camera._chase_contract_diagnostics(
        {
            "report_chase_view": {"source": "robot_0/camera_follower"},
            "report_verify_view": {"source": "mujoco_focus_camera"},
        },
        {
            "report_chase_view": {"source": "robot_relative_camera_follower"},
            "report_verify_view": {
                "source": "isaac_lab_camera_rgb_semantic_pose_robot_views:verify"
            },
        },
    )

    assert chase["same_camera_contract"] is True
    assert chase["mujoco_source"] == "robot_0/camera_follower"
    assert chase["isaac_source"] == "robot_relative_camera_follower"


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
                        "focal_length_mm": 24.0,
                        "horizontal_aperture_mm": 29.82337649,
                        "render_resolution": {"width": 540, "height": 360},
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
    assert per_location["fpv_lens_delta"]["status"] == "fpv_lens_aligned"
    assert per_location["fpv_lens_delta"]["vertical_fov_delta_deg"] == 0.0
    assert summary["status"] == "fpv_contract_shared_with_static_head_camera_pitch_correction"
    assert summary["isaac_static_head_pitch_gap_count"] == 0
    assert summary["fpv_lens_gap_count"] == 0
    assert summary["fpv_lens_delta_summary"]["status"] == "fpv_lens_aligned"
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
        color3f inputs:diffuseColor.connect = </World/Looks/mat_bed/DiffuseTexture.outputs:rgb>
        float inputs:metallic = 0
        float inputs:opacity = 1
        float inputs:roughness = 0.5
      }
      def Shader "DiffuseTexture"
      {
        asset inputs:file = @/tmp/textures/bed.png@
        float4 inputs:fallback = (0.9, 0.8, 0.7, 1)
        float4 inputs:scale = (0.9, 0.8, 0.7, 1)
        token inputs:sourceColorSpace = "auto"
        token inputs:wrapS = "repeat"
        token inputs:wrapT = "repeat"
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
                    "fpv": {
                        "mean_abs_rgb": 48.0,
                        "residual": {
                            "residual_class": "geometry_or_texture_edge_residual",
                            "edge_abs_diff": 12.0,
                            "rgb_gain_oracle": {"mean_abs_rgb_after_gain": 32.0},
                            "left_metrics": {"mean_luminance": 82.0},
                            "right_metrics": {"mean_luminance": 126.0},
                        },
                    },
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
    checks = manifest["summary"]["render_domain_checks"]
    location = manifest["locations"][0]["render_contract_diagnostics"]
    assert summary["status"] == "lighting_shadow_contract_delta"
    assert summary["mujoco_light_count"] == 1
    assert summary["isaac_light_count"] == 2
    assert summary["isaac_shadow_disabled_prim_count"] == 1
    assert summary["target_contract_delta_counts"] == {"material_texture_names_match": 1}
    assert checks["schema"] == "robot_camera_render_domain_checks_v1"
    assert checks["status"] == "render_domain_delta_confirmed"
    check_by_id = {item["check_id"]: item for item in checks["checks"]}
    assert check_by_id["light_shadow_contract"]["status"] == "light_shadow_contract_delta"
    assert check_by_id["light_shadow_contract"]["probe_history"]["status"] == "not_attached"
    assert check_by_id["texture_colorspace_material_response"]["status"] == (
        "texture_basenames_match_paths_or_colorspace_unverified"
    )
    assert check_by_id["texture_colorspace_material_response"]["texture_name_match_count"] == 1
    assert check_by_id["texture_colorspace_material_response"][
        "material_response_status_counts"
    ] == {"texture_path_or_colorspace_unverified": 1}
    assert check_by_id["texture_colorspace_material_response"]["high_residual_target_count"] == 1
    high_residual_target = check_by_id["texture_colorspace_material_response"][
        "high_residual_targets"
    ][0]
    assert high_residual_target["target_id"] == "bed_1"
    assert high_residual_target["fpv_mean_abs_rgb"] == 48.0
    assert high_residual_target["texture_full_path_delta"] is True
    assert high_residual_target["mujoco_texture_basenames"] == ["bed.png"]
    assert high_residual_target["isaac_texture_basenames"] == ["bed.png"]
    assert high_residual_target["fpv_isaac_mean_luminance"] == 126.0
    assert check_by_id["usd_preview_surface_material_model"]["status"] == (
        "usd_preview_surface_vs_mujoco_material_model_delta"
    )
    assert (
        check_by_id["usd_preview_surface_material_model"]["isaac_preview_surface_binding_count"]
        == 1
    )
    assert check_by_id["usd_preview_surface_material_model"]["preview_surface_input_counts"] == {
        "metallic": 1,
        "opacity": 1,
        "roughness": 1,
    }
    preview_target = check_by_id["usd_preview_surface_material_model"]["high_residual_targets"][0]
    assert preview_target["target_id"] == "bed_1"
    assert preview_target["isaac_preview_surface_inputs"][0]["roughness"] == 0.5
    assert preview_target["isaac_preview_surface_inputs"][0]["opacity"] == 1.0
    assert preview_target["isaac_texture_source_color_spaces"] == ["auto"]
    assert preview_target["isaac_texture_scales"] == [[0.9, 0.8, 0.7, 1.0]]
    assert preview_target["isaac_texture_fallbacks"] == [[0.9, 0.8, 0.7, 1.0]]
    assert preview_target["isaac_texture_wrap_modes"] == ["repeat/repeat"]
    assert check_by_id["tone_color_response"]["status"] == "tone_color_delta_rgb_oracle"
    assert check_by_id["tone_color_response"]["fpv_mean_abs_rgb_avg"] == 48.0
    assert check_by_id["tone_color_response"]["check_id"] == "tone_color_response"
    assert location["target_contract_delta"]["status"] == "material_texture_names_match"
    assert location["fpv_mean_abs_rgb"] == 48.0


def test_robot_camera_light_shadow_check_summarizes_worse_prior_probe(tmp_path: Path) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_light_probe_history",
    )
    baseline = {
        "scene": {
            "scene_source": "procthor-10k-val",
            "scene_index": 0,
            "seed": 6,
            "generated_mess_count": 5,
            "render_width": 540,
            "render_height": 360,
        },
        "summary": {
            "location_count": 8,
            "fpv_mean_abs_rgb_avg": 38.098,
            "chase_mean_abs_rgb_avg": 83.7516,
            "camera_contract_diagnostics": {
                "status": "fpv_contract_shared_with_static_head_camera_pitch_correction",
                "fpv_lens_delta_summary": {"status": "fpv_lens_aligned"},
                "fpv_world_pose_delta_summary": {"status": "fpv_world_pose_aligned"},
            },
            "render_contract_diagnostics": {
                "status": "lighting_shadow_contract_delta",
                "mujoco_light_count": 1,
                "isaac_light_count": 2,
                "isaac_shadow_disabled_prim_count": 44,
            },
            "residual_triage": {
                "status": "render_domain_geometry_or_texture_residual",
                "views": {"fpv": {"residual_classes": {"geometry_or_texture_edge_residual": 4}}},
            },
        },
    }
    probe = json.loads(json.dumps(baseline))
    probe["scene"]["scene_usd_path"] = "output/isaaclab/light_shadow_probe.usda"
    probe["summary"]["fpv_mean_abs_rgb_avg"] = 50.8161
    probe["summary"]["chase_mean_abs_rgb_avg"] = 114.0763
    probe["summary"]["render_contract_diagnostics"].update(
        {
            "status": "checked_targets_material_texture_names_match",
            "isaac_light_count": 1,
            "isaac_shadow_disabled_prim_count": 0,
        }
    )
    probe_path = tmp_path / "probe_manifest.json"
    probe_path.write_text(json.dumps(probe), encoding="utf-8")

    check = run_camera._light_shadow_contract_check(
        manifest=baseline,
        output_dir=tmp_path,
        mujoco_contract={"light_count": 1},
        isaac_contract={"light_count": 2, "shadow_disabled_prim_count": 44},
        room_delta={
            "status": "light_or_shadow_contract_delta",
            "mujoco_light_count": 1,
            "isaac_light_count": 2,
            "isaac_shadow_disabled_prim_count": 44,
        },
        probe_manifest_paths=[probe_path],
    )

    history = check["probe_history"]
    assert history["schema"] == "robot_camera_light_shadow_probe_history_v1"
    assert history["status"] == "prior_probes_worse"
    assert history["comparable_probe_count"] == 1
    assert history["worsened_probe_count"] == 1
    assert history["probes"][0]["comparable_to_current"] is True
    assert history["probes"][0]["delta_vs_current"]["fpv_mean_abs_rgb_delta"] == 12.7181
    assert history["probes"][0]["delta_vs_current"]["fpv_worse"] is True
    assert "Do not promote" in check["recommended_next_action"]


def test_robot_camera_preview_surface_check_summarizes_worse_material_probe(
    tmp_path: Path,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_material_probe_history",
    )
    baseline = {
        "scene": {
            "scene_source": "procthor-10k-val",
            "scene_index": 0,
            "seed": 6,
            "generated_mess_count": 5,
            "render_width": 540,
            "render_height": 360,
        },
        "summary": {
            "location_count": 8,
            "fpv_mean_abs_rgb_avg": 38.098,
            "chase_mean_abs_rgb_avg": 83.7516,
            "camera_contract_diagnostics": {
                "status": "fpv_contract_shared_with_static_head_camera_pitch_correction",
                "fpv_lens_delta_summary": {"status": "fpv_lens_aligned"},
                "fpv_world_pose_delta_summary": {"status": "fpv_world_pose_aligned"},
            },
            "render_contract_diagnostics": {
                "status": "lighting_shadow_contract_delta",
            },
            "residual_triage": {
                "status": "render_domain_geometry_or_texture_residual",
                "views": {"fpv": {"residual_classes": {"geometry_or_texture_edge_residual": 4}}},
            },
        },
    }
    probe = json.loads(json.dumps(baseline))
    probe["scene"]["scene_usd_path"] = (
        "output/isaaclab/val_0_scene_refs_fix_material_raw_roughness1/scene_semantic.usda"
    )
    probe["summary"]["location_count"] = 4
    probe["summary"]["fpv_mean_abs_rgb_avg"] = 45.4954
    probe["summary"]["chase_mean_abs_rgb_avg"] = 72.5027
    probe["summary"]["residual_triage"]["views"]["fpv"]["residual_classes"] = {
        "geometry_or_texture_edge_residual": 3,
        "view_dependent_color_residual": 1,
    }
    probe_path = tmp_path / "material_probe_manifest.json"
    probe_path.write_text(json.dumps(probe), encoding="utf-8")
    neutral_probe = json.loads(json.dumps(baseline))
    neutral_probe["scene"]["scene_usd_path"] = (
        "output/isaaclab/val_0_scene_refs_fix_material_roughness1_only/scene_semantic.usda"
    )
    neutral_probe["summary"]["fpv_mean_abs_rgb_avg"] = 37.5747
    neutral_probe["summary"]["chase_mean_abs_rgb_avg"] = 90.6459
    neutral_probe_path = tmp_path / "neutral_material_probe_manifest.json"
    neutral_probe_path.write_text(json.dumps(neutral_probe), encoding="utf-8")
    improved_probe = json.loads(json.dumps(baseline))
    improved_probe["scene"]["scene_usd_path"] = (
        "output/isaaclab/val_0_scene_refs_fix_0008_lightwood_scale_square/scene_semantic.usda"
    )
    improved_probe["summary"]["fpv_mean_abs_rgb_avg"] = 35.8577
    improved_probe["summary"]["chase_mean_abs_rgb_avg"] = 83.7491
    improved_probe_path = tmp_path / "improved_material_probe_manifest.json"
    improved_probe_path.write_text(json.dumps(improved_probe), encoding="utf-8")

    check = run_camera._usd_preview_surface_material_model_check(
        manifest=baseline,
        output_dir=tmp_path,
        per_location=[
            {
                "target": {"target_id": "table_1", "kind": "receptacle"},
                "fpv_mean_abs_rgb": 48.0,
                "fpv_residual_class": "geometry_or_texture_edge_residual",
                "mujoco_target_contract": {
                    "visuals": [
                        {
                            "material": "material_LightWoodCounters3",
                            "rgba": [0.698113, 0.339363, 0.135012, 1.0],
                        }
                    ]
                },
                "isaac_target_contract": {
                    "bindings": [
                        {
                            "has_preview_surface": True,
                            "has_diffuse_texture": True,
                            "preview_surface_inputs": {
                                "roughness": 0.5,
                                "opacity": 1.0,
                                "metallic": 0.0,
                            },
                            "texture_source_color_space": "auto",
                        }
                    ]
                },
            }
        ],
        probe_manifest_paths=[probe_path, neutral_probe_path, improved_probe_path],
    )

    history = check["probe_history"]
    assert history["schema"] == "robot_camera_material_response_probe_history_v1"
    assert history["status"] == "prior_probe_improved"
    assert history["comparable_probe_count"] == 3
    assert history["improved_probe_count"] == 1
    assert history["worsened_probe_count"] == 1
    assert history["neutral_probe_count"] == 1
    assert history["probes"][0]["comparable_to_current"] is True
    assert history["probes"][0]["delta_vs_current"]["fpv_mean_abs_rgb_delta"] == 7.3974
    assert history["probes"][0]["delta_vs_current"]["fpv_worse"] is True
    assert history["probes"][0]["delta_vs_current"]["chase_improvement"] is True
    assert history["probes"][1]["delta_vs_current"]["fpv_mean_abs_rgb_delta"] == -0.5233
    assert history["probes"][1]["delta_vs_current"]["fpv_improvement"] is False
    assert history["probes"][1]["delta_vs_current"]["fpv_worse"] is False
    assert history["probes"][2]["delta_vs_current"]["fpv_mean_abs_rgb_delta"] == -2.2403
    assert history["probes"][2]["delta_vs_current"]["fpv_improvement"] is True
    assert "comparison-only" in check["recommended_next_action"]
    assert "across more targets" in check["recommended_next_action"]


def test_robot_camera_tone_color_check_summarizes_improved_rgb_gain_probe(
    tmp_path: Path,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_tone_color_probe_history",
    )
    baseline = {
        "scene": {
            "scene_source": "procthor-10k-val",
            "scene_index": 0,
            "seed": 6,
            "generated_mess_count": 5,
            "render_width": 540,
            "render_height": 360,
        },
        "summary": {
            "location_count": 8,
            "fpv_mean_abs_rgb_avg": 38.098,
            "chase_mean_abs_rgb_avg": 83.7516,
            "camera_contract_diagnostics": {
                "status": "fpv_contract_shared_with_static_head_camera_pitch_correction",
                "fpv_lens_delta_summary": {"status": "fpv_lens_aligned"},
                "fpv_world_pose_delta_summary": {"status": "fpv_world_pose_aligned"},
            },
            "render_contract_diagnostics": {
                "status": "lighting_shadow_contract_delta",
            },
            "residual_triage": {
                "status": "render_domain_geometry_or_texture_residual",
                "views": {"fpv": {"residual_classes": {"geometry_or_texture_edge_residual": 4}}},
            },
        },
    }
    probe = json.loads(json.dumps(baseline))
    probe["summary"]["fpv_mean_abs_rgb_avg"] = 35.0612
    probe["summary"]["chase_mean_abs_rgb_avg"] = 85.0
    probe["summary"]["render_domain_checks"] = {
        "checks": [
            {
                "check_id": "tone_color_response",
                "status": "tone_color_delta_remaining_after_comparison_gain",
                "comparison_rgb_gain_applied": True,
                "comparison_rgb_gain": {"isaaclab_subprocess": [0.944061, 0.844818, 0.822146]},
            }
        ]
    }
    probe_path = tmp_path / "rgb_gain_probe_manifest.json"
    probe_path.write_text(json.dumps(probe), encoding="utf-8")

    check = run_camera._tone_color_response_check(
        manifest=baseline,
        output_dir=tmp_path,
        locations=[
            {
                "status": "success",
                "image_diffs": {
                    "fpv": {
                        "mean_abs_rgb": 38.098,
                        "residual": {
                            "residual_class": "view_dependent_color_residual",
                            "rgb_gain_oracle": {"mean_abs_rgb_after_gain": 31.0},
                        },
                    },
                    "chase": {
                        "mean_abs_rgb": 83.7516,
                        "residual": {"residual_class": "geometry_or_texture_edge_residual"},
                    },
                },
            }
        ],
        isaac_state={},
        probe_manifest_paths=[probe_path],
    )

    history = check["probe_history"]
    assert history["schema"] == "robot_camera_tone_color_probe_history_v1"
    assert history["status"] == "prior_probe_improved"
    assert history["comparable_probe_count"] == 1
    assert history["improved_probe_count"] == 1
    assert history["worsened_probe_count"] == 0
    assert history["neutral_probe_count"] == 0
    assert history["probes"][0]["comparable_to_current"] is True
    assert history["probes"][0]["comparison_rgb_gain_applied"] is True
    assert history["probes"][0]["comparison_rgb_gain"]["isaaclab_subprocess"] == [
        0.944061,
        0.844818,
        0.822146,
    ]
    assert history["probes"][0]["delta_vs_current"]["fpv_mean_abs_rgb_delta"] == -3.0368
    assert history["probes"][0]["delta_vs_current"]["fpv_improvement"] is True
    assert "strongest current comparison-only direction" in check["recommended_next_action"]


def test_robot_camera_native_isaac_render_diagnostics_are_reported_separately(
    tmp_path: Path,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_native_isaac_render",
    )
    mujoco_xml = tmp_path / "scene.xml"
    mujoco_xml.write_text(
        """<mujoco>
  <asset><material name="mat_table"/></asset>
  <worldbody>
    <light name="key"/>
    <body name="table_1">
      <geom name="table_1_visual_0" material="mat_table"/>
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
  def Xform "table_1"
  {
    def Mesh "mesh"
    {
      rel material:binding = </World/Looks/mat_table>
    }
  }
  def Scope "Looks"
  {
    def Material "mat_table"
    {
      def Shader "PreviewSurface"
      {
        uniform token info:id = "UsdPreviewSurface"
      }
    }
  }
}
""",
        encoding="utf-8",
    )
    native = {
        "schema": "isaac_native_render_diagnostics_v1",
        "status": "captured",
        "renderer_mode": "isaac_lab_headless_rtx",
        "capture_method": "isaac_lab_camera_rgb_static_robot_views",
        "view_kind": "robot_views",
        "settings_api_available": True,
        "available_setting_count": 4,
        "missing_setting_count": 2,
        "tone_mapping": {
            "operator": {
                "status": "available",
                "value": "aces",
                "setting_path": "/rtx/post/tonemap/op",
            }
        },
        "camera_exposure": {
            "auto_exposure_enabled": {
                "status": "available",
                "value": False,
                "setting_path": "/rtx/post/histogram/autoExposure/enabled",
            },
            "iso": {
                "status": "available",
                "value": 100,
                "setting_path": "/rtx/post/camera/iso",
            },
        },
        "ocio": {},
        "color_correction": {},
        "color_grading": {},
        "renderer": {
            "renderer": {
                "status": "available",
                "value": "RayTracedLighting",
                "setting_path": "/renderer/active",
            }
        },
        "camera_prim_paths": ["/World/robot_0/head_camera"],
        "render_product_paths": ["/Render/Product/Fpv"],
        "render_resolution": {"width": 540, "height": 360},
        "isaac_lab_isp_active": False,
        "settings_mutation_attempted": False,
        "default_render_settings_changed": False,
        "post_render_comparison_profile": {
            "applied": False,
            "source": "not_a_native_renderer_setting",
        },
    }
    manifest = {
        "schema": "roboclaws_robot_camera_apple2apple_comparison_v1",
        "purpose": "unit",
        "scene": {"scene_usd_path": str(isaac_usd)},
        "locations": [
            {
                "status": "success",
                "label": "0001_table_1",
                "target": {"kind": "receptacle", "target_id": "table_1"},
                "robot_pose": {},
                "views": {
                    "mujoco": {"fpv": "mujoco/fpv.png", "chase": "mujoco/chase.png"},
                    "isaac": {"fpv": "isaac/fpv.png", "chase": "isaac/chase.png"},
                },
                "camera_diagnostics": {
                    "isaac": {
                        "schema": "isaac_robot_view_camera_diagnostics_v1",
                        "native_render_diagnostics": native,
                    }
                },
                "image_diffs": {
                    "fpv": {
                        "mean_abs_rgb": 42.0,
                        "nonzero_fraction": 1.0,
                        "residual": {
                            "residual_class": "view_dependent_color_residual",
                            "rgb_gain_oracle": {"mean_abs_rgb_after_gain": 30.0},
                        },
                    },
                    "chase": {
                        "mean_abs_rgb": 12.0,
                        "nonzero_fraction": 0.5,
                        "residual": {"residual_class": "low_residual"},
                    },
                },
            }
        ],
        "summary": {
            "residual_triage": {
                "status": "view_dependent_color_residual",
            }
        },
    }
    (tmp_path / "mujoco_state.json").write_text(
        json.dumps(
            {
                "scene_xml": str(mujoco_xml),
                "objects": {},
                "receptacles": {
                    "table_1": {
                        "receptacle_id": "table_1",
                        "category": "Table",
                        "position": [0.0, 0.0, 0.5],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "isaac_state.json").write_text(
        json.dumps(
            {
                "scene_usd": str(isaac_usd),
                "native_render_diagnostics": native,
                "receptacle_index": {
                    "table_1": {
                        "usd_prim_path": "/World/table_1",
                        "category": "Table",
                        "geometry_status": "renderable",
                        "has_renderable_geometry": True,
                        "valid_stage_prim": True,
                        "usd_world_bounds": {"center": [0.0, 0.0, 0.5]},
                    }
                },
                "object_index": {},
                "scene_binding_diagnostics": {
                    "receptacle_bindings": {
                        "table_1": {
                            "status": "bound",
                            "public_id": "table_1",
                            "kind": "receptacle",
                            "category": "Table",
                            "usd_prim_path": "/World/table_1",
                            "geometry_status": "renderable",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    run_camera._attach_render_contract_diagnostics(manifest, output_dir=tmp_path)
    run_camera._write_outputs(manifest, tmp_path)

    native_summary = manifest["summary"]["native_isaac_render_diagnostics"]
    native_detail = manifest["native_isaac_render_diagnostics"]
    render_gate = manifest["object_render_parity_diagnostics"]["render_gate"]
    assert manifest["object_visual_parity_audit"] == manifest["object_parity_audit"]
    assert (
        manifest["summary"]["object_visual_parity_audit"]
        == (manifest["summary"]["object_parity_audit"])
    )
    assert native_summary["status"] == "native_settings_recorded"
    assert native_summary["settings_api_available"] is True
    assert native_detail["tone_mapping"]["operator"]["value"] == "aces"
    assert native_detail["camera_exposure"]["auto_exposure_enabled"]["value"] is False
    assert native_summary["default_render_settings_changed"] is False
    assert native_summary["post_render_comparison_profile"]["source"] == (
        "not_a_native_renderer_setting"
    )
    assert render_gate["native_isaac_status"] == "native_settings_recorded"
    assert render_gate["native_isaac_render_diagnostics"]["status"] == ("native_settings_recorded")
    assert (
        manifest["lanes"][run_camera.ISAAC_LANE_ID]["native_render_diagnostics"][
            "default_render_settings_changed"
        ]
        is False
    )
    report_html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Native Isaac Render Diagnostics" in report_html
    assert "not_a_native_renderer_setting" in report_html
    assert "/rtx/post/tonemap/op" in report_html


def test_robot_camera_comparison_target_selection_filters_unbound_isaac_targets() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_target_selection",
    )
    state = {
        "receptacles": {
            "bed_1": {},
            "sink_1": {},
        },
        "objects": {
            "alarmclock_1": {},
            "bowl_1": {},
            "pillow_1": {},
        },
    }
    selection = run_camera._select_comparison_targets(
        state,
        limit=4,
        scene_binding_diagnostics={
            "receptacle_bindings": {
                "bed_1": {"status": "bound", "usd_prim_path": "/World/bed_1"},
                "sink_1": {"status": "bound", "usd_prim_path": "/World/sink_1"},
            },
            "object_bindings": {
                "bowl_1": {"status": "bound", "usd_prim_path": "/World/bowl_1"},
            },
            "selected_object_bindings": {
                "pillow_1": {"status": "bound", "usd_prim_path": "/World/pillow_1"},
            },
        },
    )

    assert selection["status"] == "isaac_bound_targets_selected"
    assert selection["selected_count"] == 4
    assert [item["target_id"] for item in selection["selected_targets"]] == [
        "bed_1",
        "sink_1",
        "bowl_1",
        "pillow_1",
    ]
    assert selection["dropped_unbound_target_count"] == 1
    assert selection["dropped_unbound_targets"][0]["target_id"] == "alarmclock_1"


def test_robot_camera_comparison_target_selection_uses_isaac_scene_index() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_target_selection_scene_index",
    )
    selection = run_camera._select_comparison_targets(
        {
            "receptacles": {
                "bed_1": {},
                "table_1": {},
            },
            "objects": {
                "box_1": {},
                "bowl_1": {},
            },
        },
        limit=2,
        scene_binding_diagnostics={},
        isaac_state={
            "receptacle_index": {
                "bed_1": {
                    "usd_prim_path": "/World/bed_1",
                    "geometry_status": "renderable",
                },
                "table_1": {
                    "usd_prim_path": "/World/table_1",
                    "geometry_status": "renderable",
                },
            },
            "object_index": {
                "box_1": {
                    "usd_prim_path": "/World/box_1",
                    "geometry_status": "renderable",
                },
                "bowl_1": {
                    "usd_prim_path": "/World/bowl_1",
                    "geometry_status": "renderable",
                },
            },
        },
    )

    assert selection["status"] == "isaac_bound_targets_selected"
    assert selection["isaac_bound_candidate_count"] == 4
    assert [item["target_id"] for item in selection["selected_targets"]] == ["bed_1", "table_1"]
    assert selection["not_selected_bound_target_count"] == 2
    assert [item["target_id"] for item in selection["not_selected_bound_targets"]] == [
        "bowl_1",
        "box_1",
    ]
    assert selection["dropped_unbound_target_count"] == 0


def test_robot_camera_comparison_target_selection_preserves_legacy_order_without_bindings() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_target_selection_legacy",
    )
    selection = run_camera._select_comparison_targets(
        {
            "receptacles": {"bed_2": {}, "bed_1": {}},
            "objects": {"bowl_1": {}},
        },
        limit=2,
        scene_binding_diagnostics={},
    )

    assert selection["status"] == "unfiltered_no_isaac_binding_diagnostics"
    assert [item["target_id"] for item in selection["selected_targets"]] == ["bed_1", "bed_2"]
    assert selection["dropped_unbound_target_count"] == 0


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


def test_robot_camera_isaac_render_contract_reports_visual_physics(
    tmp_path: Path,
) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_visual_physics_contract",
    )
    isaac_usd = tmp_path / "scene.usda"
    isaac_usd.write_text(
        """#usda 1.0
def Xform "World"
{
    def Xform "box_1" (
        apiSchemas = ["PhysicsRigidBodyAPI"]
    )
    {
        float physics:mass = 1
        def Mesh "mesh"
        {
            rel material:binding = </World/Looks/BoxMat>
        }
        def PhysicsRevoluteJoint "flap_joint"
        {
            float physics:lowerLimit = 0
        }
    }
    def Scope "Looks"
    {
        def Material "BoxMat"
        {
            token outputs:surface.connect = </World/Looks/BoxMat/Shader.outputs:surface>
        }
    }
}
""",
        encoding="utf-8",
    )

    contract = run_camera._isaac_render_contract_from_usda(str(isaac_usd))
    view = run_camera._isaac_view_render_contract(contract, usd_prim_path="/World/box_1")

    assert contract["visual_physics_status"] == "physics_articulation_preserved"
    assert contract["physics_joint_paths"] == ["/World/box_1/flap_joint"]
    assert contract["physics_api_schema_prim_paths"] == ["/World/box_1"]
    assert contract["physics_property_prim_paths"] == ["/World/box_1"]
    assert view["visual_physics_status"] == "physics_articulation_preserved"
    assert view["physics_joint_count"] == 1
    assert view["physics_api_schema_prim_count"] == 1
    assert view["physics_property_prim_count"] == 1


def test_robot_camera_object_parity_audit_covers_unselected_objects(tmp_path: Path) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_object_parity_audit",
    )
    mujoco_xml = tmp_path / "scene.xml"
    mujoco_xml.write_text(
        """<mujoco>
  <asset>
    <texture name="BoxTex" file="box_closed.png"/>
    <texture name="BowlTex" file="bowl.png"/>
    <material name="material_Box" texture="BoxTex"/>
    <material name="material_Bowl" texture="BowlTex"/>
  </asset>
  <worldbody>
    <body name="box_1"><geom name="box_1_visual_0" material="material_Box"/></body>
    <body name="bowl_1"><geom name="bowl_1_visual_0" material="material_Bowl"/></body>
    <body name="table_1"><geom name="table_1_visual_0" material="material_Box"/></body>
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
  def Xform "box_1"
  {
    def Mesh "mesh"
    {
      rel material:binding = </World/box_1/Looks/material_Box_Open>
    }
    def Scope "Looks"
    {
      def Material "material_Box_Open"
      {
        def Shader "PreviewSurface"
        {
          uniform token info:id = "UsdPreviewSurface"
          color3f inputs:diffuseColor = (0.6, 0.4, 0.2)
        }
      }
    }
  }
  def Xform "bowl_1"
  {
    def Mesh "mesh"
    {
      rel material:binding = </World/bowl_1/Looks/material_Bowl>
    }
    def Scope "Looks"
    {
      def Material "material_Bowl"
      {
        def Shader "PreviewSurface"
        {
          uniform token info:id = "UsdPreviewSurface"
          color3f inputs:diffuseColor = (1, 1, 1)
        }
      }
    }
  }
  def Xform "table_1"
  {
    def Mesh "mesh"
    {
      rel material:binding = </World/table_1/Looks/material_Box>
    }
    def Scope "Looks"
    {
      def Material "material_Box"
      {
        def Shader "PreviewSurface"
        {
          uniform token info:id = "UsdPreviewSurface"
          color3f inputs:diffuseColor = (1, 1, 1)
        }
      }
    }
  }
}
""",
        encoding="utf-8",
    )
    mujoco_state = {
        "scene_xml": str(mujoco_xml),
        "objects": {
            "box_1": {
                "object_id": "box_1",
                "category": "Box",
                "location_id": "",
                "position": [1.0, 2.0, 0.5],
            },
            "bowl_1": {
                "object_id": "bowl_1",
                "category": "Bowl",
                "location_id": "table_1",
                "position": [2.0, 2.0, 0.7],
            },
        },
        "receptacles": {
            "table_1": {
                "receptacle_id": "table_1",
                "category": "DiningTable",
                "position": [2.0, 2.0, 0.6],
            }
        },
        "open_receptacle_ids": ["table_1"],
    }
    isaac_state = {
        "scene_usd": str(isaac_usd),
        "object_index": {
            "box_1": {
                "asset_id": "Box_10",
                "category": "Box",
                "parent": "table_1",
                "usd_prim_path": "/World/box_1",
                "geometry_status": "renderable",
                "has_renderable_geometry": True,
                "valid_stage_prim": True,
                "usd_world_bounds": {
                    "center": [1.01, 2.02, 0.51],
                    "size": [0.5, 0.4, 0.3],
                },
            },
            "bowl_1": {
                "asset_id": "Bowl_12",
                "category": "Plate",
                "parent": "table_1",
                "usd_prim_path": "/World/bowl_1",
                "geometry_status": "renderable",
                "has_renderable_geometry": True,
                "valid_stage_prim": True,
                "usd_world_bounds": {
                    "center": [2.0, 2.0, 0.7],
                    "size": [0.2, 0.2, 0.1],
                },
            },
        },
        "receptacle_index": {
            "table_1": {
                "asset_id": "Dining_Table_203",
                "category": "DiningTable",
                "usd_prim_path": "/World/table_1",
                "geometry_status": "renderable",
                "has_renderable_geometry": True,
                "valid_stage_prim": True,
                "usd_world_bounds": {
                    "center": [2.0, 2.0, 0.6],
                    "size": [1.0, 1.0, 0.6],
                },
            }
        },
        "open_receptacle_ids": ["table_1"],
        "semantic_pose_state": {
            "articulations": {
                "table_1": {
                    "open": True,
                    "rendered_to_usd": False,
                }
            }
        },
        "scene_binding_diagnostics": {},
    }
    for image_relpath, color in {
        "mujoco/fpv.png": (120, 120, 120),
        "mujoco/chase.png": (80, 90, 100),
        "isaac/fpv.png": (60, 60, 60),
        "isaac/chase.png": (90, 70, 50),
    }.items():
        image_path = tmp_path / image_relpath
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (12, 8), color).save(image_path)
    locations = [
        {
            "status": "success",
            "target": {"kind": "object", "target_id": "box_1"},
            "views": {
                "mujoco": {"fpv": "mujoco/fpv.png", "chase": "mujoco/chase.png"},
                "isaac": {"fpv": "isaac/fpv.png", "chase": "isaac/chase.png"},
            },
        }
    ]
    audit = run_camera._object_parity_audit(
        mujoco_state=mujoco_state,
        isaac_state=isaac_state,
        mujoco_contract=run_camera._mujoco_render_contract_from_xml(str(mujoco_xml)),
        isaac_contract=run_camera._isaac_render_contract_from_usda(str(isaac_usd)),
        scene_binding_diagnostics={},
        locations=locations,
        output_dir=tmp_path,
    )

    assert audit["schema"] == "robot_camera_object_parity_audit_v1"
    assert audit["status"] == "object_parity_gaps_detected"
    assert audit["object_count"] == 2
    assert audit["receptacle_count"] == 1
    items = {item["target_id"]: item for item in audit["items"]}
    assert items["box_1"]["binding_status"] == "bound_in_both"
    assert items["box_1"]["state_status"] == "visual_state_unverified"
    assert items["box_1"]["support_status"] == "support_available_in_isaac_only"
    assert items["box_1"]["render_contract_delta"]["status"] == "material_or_texture_name_delta"
    assert items["box_1"]["rgb_view_evidence"]["status"] == "selected_views_nonblank"
    assert items["box_1"]["rgb_view_evidence"]["view_status_counts"] == {"nonblank_rgb": 4}
    assert items["box_1"]["isaac"]["asset_id"] == "Box_10"
    assert items["bowl_1"]["category_status"] == "category_delta"
    assert items["bowl_1"]["rgb_view_evidence"]["status"] == "not_captured_in_selected_views"
    assert items["table_1"]["state_status"] == "state_not_rendered_to_usd"
    high_priority_ids = {item["target_id"] for item in audit["high_priority_items"]}
    assert {"box_1", "bowl_1", "table_1"} <= high_priority_ids
    category_summary = {item["category"]: item for item in audit["category_status_summary"]}
    assert category_summary["box"]["item_count"] == 1
    assert category_summary["box"]["object_gate_classification_counts"] == {"visual_state_delta": 1}
    assert category_summary["box"]["rgb_view_evidence_status_counts"] == {
        "selected_views_nonblank": 1
    }
    assert category_summary["bowl"]["object_gate_classification_counts"] == {"not_comparable": 1}
    assert category_summary["diningtable"]["object_gate_classification_counts"] == {
        "visual_state_delta": 1
    }

    diagnostics = run_camera._object_render_parity_diagnostics(
        object_audit=audit,
        render_domain_checks={
            "status": "render_domain_delta_confirmed",
            "check_status_counts": {"light_shadow_contract_delta": 1},
            "recommended_next_action": "Inspect renderer response.",
        },
        residual_triage={"status": "render_domain_geometry_or_texture_residual"},
    )

    assert diagnostics["schema"] == "robot_camera_object_render_parity_diagnostics_v1"
    assert diagnostics["status"] == "object_gate_failures_detected"
    object_gate = diagnostics["object_gate"]
    assert object_gate["status"] == "object_gate_failures_detected"
    assert object_gate["failure_count"] == 3
    classifications = {
        item["target_id"]: item["classification"] for item in object_gate["failure_records"]
    }
    assert classifications["box_1"] == "visual_state_delta"
    assert classifications["bowl_1"] == "not_comparable"
    assert classifications["table_1"] == "visual_state_delta"
    blocking_statuses = {
        item["target_id"]: item["blocking_status"] for item in object_gate["failure_records"]
    }
    assert blocking_statuses["bowl_1"] == "category_delta"
    assert diagnostics["render_gate"]["status"] == "blocked_by_object_gate"

    report_html = run_camera._render_report(
        {
            "purpose": "unit test",
            "summary": {},
            "object_render_parity_diagnostics": diagnostics,
            "object_visual_parity_audit": audit,
            "locations": [],
        }
    )
    assert "Object/Render Gate" in report_html
    assert "object_gate_failures_detected" in report_html
    assert "visual_state_delta" in report_html
    assert "Category Status Summary" in report_html
    assert "diningtable" in report_html
    assert "selected_views_nonblank" in report_html
    assert "prepared_usd_visual_physics_freeze" in report_html


def test_robot_camera_object_parity_audit_uses_isaac_semantic_pose_position(tmp_path: Path) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_object_parity_semantic_pose",
    )
    mujoco_state = {
        "objects": {
            "teddy_1": {
                "object_id": "teddy_1",
                "category": "TeddyBear",
                "position": [1.0, 2.0, 0.8],
            }
        },
        "receptacles": {},
    }
    isaac_state = {
        "object_index": {
            "teddy_1": {
                "asset_id": "Teddy_Bear_1",
                "category": "TeddyBear",
                "parent": "bed_1",
                "usd_prim_path": "/World/teddy_1",
                "geometry_status": "renderable",
                "has_renderable_geometry": True,
                "valid_stage_prim": True,
                "usd_world_bounds": {
                    "center": [8.0, 9.0, 1.2],
                    "size": [0.5, 0.4, 0.5],
                },
            }
        },
        "receptacle_index": {},
        "semantic_pose_state": {
            "object_poses": {
                "teddy_1": {
                    "object_id": "teddy_1",
                    "position": [1.02, 2.0, 0.82],
                    "position_source": "isaac_support_placement_resolver",
                    "support_receptacle_id": "desk_1",
                    "placement_support_status": "degraded_elevated",
                }
            },
            "semantic_pose_view_capture": {
                "rendered_to_usd": True,
            },
        },
    }

    audit = run_camera._object_parity_audit(
        mujoco_state=mujoco_state,
        isaac_state=isaac_state,
        mujoco_contract={},
        isaac_contract={},
        scene_binding_diagnostics={},
        locations=[],
        output_dir=tmp_path,
    )

    item = {item["target_id"]: item for item in audit["items"]}["teddy_1"]
    assert item["pose_status"] == "pose_aligned"
    assert item["pose_delta_m"] == 0.028284
    assert item["isaac"]["position"] == [1.02, 2.0, 0.82]
    assert item["isaac"]["position_source"] == "isaac_support_placement_resolver"


def test_robot_camera_box_visual_state_reports_frozen_ref_baked_usd() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_box_visual_state_frozen",
    )

    contract = run_camera._object_visual_state_contract(
        target_id="box_1",
        kind="object",
        mujoco_entry={"category": "Box"},
        isaac_entry={"category": "Box"},
        mujoco_state={
            "joint_states": {
                "box_1": [
                    {
                        "joint_name": "box_1_box10flapinner1joint0",
                        "joint_type": "hinge",
                        "qpos": 2.91219,
                        "ref": 2.91219,
                        "range": [0.0, 2.91219],
                    },
                    {
                        "joint_name": "box_1_box10flapinner2joint0",
                        "joint_type": "hinge",
                        "qpos": -3.06698,
                        "ref": -3.06698,
                        "range": [-3.06698, 0.0],
                    },
                ]
            }
        },
        isaac_state={},
        isaac_contract={
            "status": "parsed",
            "material_bindings": {},
            "physics_joint_paths": [],
            "physics_api_schema_prim_paths": [],
            "physics_property_prim_paths": [],
        },
        usd_prim_path="/World/box_1",
    )

    assert contract["status"] == "visual_state_static_ref_baked"
    assert contract["mujoco"]["status"] == "mujoco_ref_endpoint_articulation"
    assert contract["mujoco"]["endpoint_joint_count"] == 2
    assert contract["isaac"]["status"] == "isaac_visual_physics_frozen"
    assert run_camera.OBJECT_VISUAL_STATE_CATEGORIES == {"box"}
    assert contract["protected_by"] == "prepared_usd_visual_physics_freeze"
    assert contract["registry"]["status"] == "active_category_contract"
    assert contract["evidence_artifact"].endswith(
        "0603_val1_seed8_2mess_4loc_default_combined_chasefix/report.html"
    )
    assert "PhysX will not re-open" in contract["reason"]


def test_robot_camera_box_visual_state_reports_preserved_isaac_physics() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_box_visual_state_physics",
    )

    contract = run_camera._object_visual_state_contract(
        target_id="box_1",
        kind="object",
        mujoco_entry={"category": "Box"},
        isaac_entry={"category": "Box"},
        mujoco_state={
            "joint_states": {
                "box_1": [
                    {
                        "joint_name": "box_1_box10flapouter1joint0",
                        "joint_type": "hinge",
                        "qpos": -2.93938,
                        "ref": -2.93938,
                        "range": [-2.93938, 0.0],
                    }
                ]
            }
        },
        isaac_state={},
        isaac_contract={
            "status": "parsed",
            "material_bindings": {},
            "physics_joint_paths": ["/World/box_1/Geometry/flap_joint"],
            "physics_api_schema_prim_paths": ["/World/box_1/Geometry/flap"],
            "physics_property_prim_paths": ["/World/box_1/Geometry/flap"],
        },
        usd_prim_path="/World/box_1",
    )

    assert contract["status"] == "visual_state_articulation_physics_preserved"
    assert contract["protected_by"] == "prepared_usd_visual_physics_freeze"
    assert contract["isaac"]["status"] == "isaac_articulation_physics_preserved"
    assert contract["isaac"]["physics_joint_count"] == 1
    assert "re-solve those joints" in contract["reason"]


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
