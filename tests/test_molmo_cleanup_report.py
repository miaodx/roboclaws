from __future__ import annotations

from pathlib import Path

from roboclaws.molmo_cleanup.advisory_scoring import build_advisory_evaluation
from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.cleanup_primitive_evidence import (
    cleanup_primitive_evidence_from_substeps,
)
from roboclaws.molmo_cleanup.manipulation_provenance import (
    api_semantic_manipulation_evidence,
    blocked_planner_probe_evidence,
)
from roboclaws.molmo_cleanup.rby1m_curobo_gate import (
    rby1m_curobo_gate_from_planner_probe,
)
from roboclaws.molmo_cleanup.report import (
    render_cleanup_report,
    render_planner_manipulation_report,
    write_state_snapshot,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.scoring import score_cleanup


def test_cleanup_report_renders_score_moves_and_provenance(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    final_locations = scenario.object_locations()
    final_locations.update({"mug_01": "sink_01", "book_01": "bookshelf_01"})
    score = score_cleanup(final_locations, scenario.private_manifest)
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(scenario, final_locations, tmp_path / "after.png", title="After")
    run_result = {
        "cleanup_status": score.status,
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "manipulation_evidence": api_semantic_manipulation_evidence(
            backend="api_semantic_synthetic",
            primitive_summary={API_SEMANTIC_PROVENANCE: 1},
        ),
        "score": score.to_dict(),
        "advisory_evaluation": build_advisory_evaluation(
            score=score.to_dict(),
            scenario_id=scenario.scenario_id,
        ),
    }
    trace_events = [
        {
            "tool": "place",
            "event": "response",
            "response": {
                "ok": True,
                "object_id": "mug_01",
                "receptacle_id": "sink_01",
                "primitive_provenance": API_SEMANTIC_PROVENANCE,
            },
        }
    ]
    run_result["cleanup_primitive_evidence"] = cleanup_primitive_evidence_from_substeps(
        [
            {
                "object_id": "mug_01",
                "target_receptacle_id": "sink_01",
                "steps": [
                    {
                        "phase": "navigate_to_object",
                        "status": "ok",
                        "primitive_provenance": API_SEMANTIC_PROVENANCE,
                    },
                    {
                        "phase": "pick",
                        "status": "ok",
                        "primitive_provenance": API_SEMANTIC_PROVENANCE,
                    },
                    {
                        "phase": "navigate_to_receptacle",
                        "status": "ok",
                        "primitive_provenance": API_SEMANTIC_PROVENANCE,
                    },
                    {
                        "phase": "place",
                        "status": "ok",
                        "primitive_provenance": API_SEMANTIC_PROVENANCE,
                        "state_mutation": "mujoco_freejoint_qpos",
                    },
                ],
            }
        ]
    )

    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=trace_events,
        before_snapshot=before,
        after_snapshot=after,
    )

    html = report_path.read_text(encoding="utf-8")
    assert "MolmoSpaces Cleanup Pilot" in html
    assert "api_semantic" in html
    assert "Manipulation Provenance" in html
    assert "Cleanup Primitive Gate" in html
    assert "nav/object" in html
    assert "mujoco_freejoint_qpos" in html
    assert "does not prove planner-backed robot manipulation" in html
    assert "mug_01" in html
    assert "Semantic acceptability" in html
    assert "Advisory Review" in html
    assert "authoritative=false" in html
    assert "valid_receptacle_ids" not in html
    assert before.is_file()
    assert after.is_file()


def test_cleanup_report_renders_robot_visual_timeline(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    score = score_cleanup(scenario.object_locations(), scenario.private_manifest)
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "after.png",
        title="After",
    )
    for name in ("step.fpv.png", "step.chase.png", "step.map.png", "step.verify.png"):
        (tmp_path / "robot_views" / name).parent.mkdir(exist_ok=True)
        (tmp_path / "robot_views" / name).write_bytes(b"placeholder")
    run_result = {
        "cleanup_status": score.status,
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "score": score.to_dict(),
        "robot_name": "rby1m",
        "semantic_substeps": [
            {
                "object_id": "mug_01",
                "source_receptacle_id": "table_01",
                "target_receptacle_id": "sink_01",
                "steps": [
                    {"phase": "navigate_to_object"},
                    {"phase": "pick"},
                    {"phase": "navigate_to_receptacle"},
                    {"phase": "place", "location_id": "sink_01"},
                    {
                        "phase": "object_done",
                        "location_id": "sink_01",
                        "location_relation": "on",
                    },
                ],
            }
        ],
    }

    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=[],
        before_snapshot=before,
        after_snapshot=after,
        robot_view_steps=[
            {
                "action": "before",
                "robot_pose": {"x": 0.0, "y": 0.0, "theta": 0.0},
                "views": {
                    "fpv": "robot_views/step.fpv.png",
                    "chase": "robot_views/step.chase.png",
                    "map": "robot_views/step.map.png",
                    "verify": "robot_views/bootstrap.verify.png",
                },
                "focus": {
                    "has_focus": False,
                    "fpv_visibility": {
                        "status": "ok",
                        "object_pixels": 0,
                        "receptacle_pixels": 0,
                    },
                    "visibility": {
                        "status": "ok",
                        "object_pixels": 0,
                        "receptacle_pixels": 0,
                    },
                },
            },
            {
                "action": "goto sink",
                "semantic_phase": "navigate_to_receptacle",
                "robot_pose": {
                    "x": 1.0,
                    "y": 2.0,
                    "theta": 0.5,
                    "theta_source": "target_facing_base_yaw",
                    "head_pitch": 0.6,
                    "head_pitch_source": "target_framing_head_pitch",
                    "robot_room_id": "room_1",
                    "target_room_id": "room_1",
                    "same_room_as_target": True,
                },
                "views": {
                    "fpv": "robot_views/step.fpv.png",
                    "chase": "robot_views/step.chase.png",
                    "map": "robot_views/step.map.png",
                    "verify": "robot_views/step.verify.png",
                },
                "focus": {
                    "has_focus": True,
                    "object_label": "Mug mug",
                    "receptacle_label": "Sink sink",
                    "provenance": "public_mujoco_state_report_aid",
                    "fpv_visibility": {
                        "status": "ok",
                        "object_pixels": 12,
                        "receptacle_pixels": 80,
                    },
                    "visibility": {
                        "status": "ok",
                        "object_pixels": 24,
                        "receptacle_pixels": 120,
                    },
                },
            },
        ],
    )

    html = report_path.read_text(encoding="utf-8")
    assert "Robot View Timeline" in html
    assert "Semantic Substeps" in html
    assert "Canonical cleanup loop: nav, pick, nav, open when needed, place." in html
    assert "<span>nav</span><small>object</small>" in html
    assert "<span>pick</span><small>object</small>" in html
    assert "<span>nav</span><small>target</small>" in html
    assert "<span>place</span><small>surface</small>" in html
    assert "Subphase" in html
    assert "nav/target" in html
    assert "object_done" not in html
    assert "rby1m" in html
    assert "robot_views/step.fpv.png" in html
    assert "robot_views/bootstrap.verify.png" not in html
    assert "Verification" in html
    assert "object 0 px" not in html
    assert "navigate_to_receptacle" in html
    assert "Mug mug" in html
    assert "public_mujoco_state_report_aid" in html
    assert "target_facing_base_yaw" in html
    assert "target_framing_head_pitch" in html
    assert "FPV visibility" in html
    assert "same room" in html
    assert "object 24 px" in html


def test_cleanup_report_renders_raw_fpv_observations(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    score = score_cleanup(scenario.object_locations(), scenario.private_manifest)
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "after.png",
        title="After",
    )
    fpv = tmp_path / "robot_views" / "raw.fpv.png"
    fpv.parent.mkdir()
    fpv.write_bytes(b"placeholder")
    run_result = {
        "contract": "realworld_cleanup_v1",
        "cleanup_status": "failed",
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "score": score.to_dict(),
        "agent_view": {
            "perception_mode": "raw_fpv_only",
            "metric_map": {"rooms": [], "inspection_waypoints": []},
            "fixture_hints": {"rooms": []},
            "observed_objects": [],
            "raw_fpv_observations": [
                {
                    "observation_id": "raw_fpv_001",
                    "room_id": "kitchen",
                    "waypoint_id": "kitchen_scan_1",
                    "perception_mode": "raw_fpv_only",
                    "structured_detections_available": False,
                    "artifact_status": "recorded",
                    "image_artifacts": {"fpv": "robot_views/raw.fpv.png"},
                }
            ],
        },
        "raw_fpv_observations": [
            {
                "observation_id": "raw_fpv_001",
                "room_id": "kitchen",
                "waypoint_id": "kitchen_scan_1",
                "perception_mode": "raw_fpv_only",
                "structured_detections_available": False,
                "artifact_status": "recorded",
                "image_artifacts": {"fpv": "robot_views/raw.fpv.png"},
            }
        ],
    }

    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=[],
        before_snapshot=before,
        after_snapshot=after,
    )

    html = report_path.read_text(encoding="utf-8")
    assert "Agent View" in html
    assert "Raw FPV Observations" in html
    assert "raw_fpv_001" in html
    assert "robot_views/raw.fpv.png" in html
    assert "support estimates" in html


def test_cleanup_report_renders_camera_model_policy(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    score = score_cleanup(scenario.object_locations(), scenario.private_manifest)
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "after.png",
        title="After",
    )
    run_result = {
        "contract": "realworld_cleanup_v1",
        "cleanup_status": "success",
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "score": score.to_dict(),
        "agent_view": {
            "perception_mode": "camera_model_policy",
            "metric_map": {"rooms": [], "inspection_waypoints": []},
            "fixture_hints": {"rooms": []},
            "raw_fpv_observations": [
                {
                    "observation_id": "raw_fpv_001",
                    "room_id": "kitchen",
                    "waypoint_id": "kitchen_scan_1",
                    "perception_mode": "camera_model_policy",
                    "structured_detections_available": False,
                    "artifact_status": "pending_robot_view_capture",
                    "image_artifacts": {},
                }
            ],
            "observed_objects": [
                {
                    "object_id": "observed_001",
                    "category": "dish",
                    "name": "Mug",
                    "current_room_id": "kitchen",
                    "perception_source": "camera_model_policy",
                    "model_provenance": "simulated_camera_model",
                    "source_observation_id": "raw_fpv_001",
                    "support_estimate": {
                        "fixture_id": "coffee_table_01",
                        "source": "camera_model_policy",
                        "model_provenance": "simulated_camera_model",
                    },
                }
            ],
            "camera_model_policy_evidence": {
                "schema": "camera_model_policy_v1",
                "enabled": True,
                "model_provenance": "simulated_camera_model",
                "event_count": 1,
                "candidate_count": 1,
                "private_truth_included": False,
                "events": [
                    {
                        "observation_id": "raw_fpv_001",
                        "room_id": "kitchen",
                        "model_provenance": "simulated_camera_model",
                        "candidate_count": 1,
                        "registered_observed_handles": ["observed_001"],
                    }
                ],
            },
        },
    }
    run_result["raw_fpv_observations"] = run_result["agent_view"]["raw_fpv_observations"]
    run_result["camera_model_policy_evidence"] = run_result["agent_view"][
        "camera_model_policy_evidence"
    ]

    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=[],
        before_snapshot=before,
        after_snapshot=after,
    )

    html = report_path.read_text(encoding="utf-8")
    assert "Camera Model Policy" in html
    assert "simulated_camera_model" in html
    assert "observed_001" in html
    assert "raw_fpv_001" in html
    assert "Raw FPV Observations" in html


def test_cleanup_report_keeps_visual_core_before_audit_sections(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    final_locations = scenario.object_locations()
    final_locations.update({"mug_01": "sink_01"})
    score = score_cleanup(final_locations, scenario.private_manifest).to_dict()
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(scenario, final_locations, tmp_path / "after.png", title="After")
    semantic_substeps = [
        {
            "object_id": "observed_001",
            "source_receptacle_id": "table_01",
            "target_receptacle_id": "sink_01",
            "steps": [
                {"phase": "navigate_to_object", "primitive_provenance": API_SEMANTIC_PROVENANCE},
                {"phase": "pick", "primitive_provenance": API_SEMANTIC_PROVENANCE},
                {
                    "phase": "navigate_to_receptacle",
                    "primitive_provenance": API_SEMANTIC_PROVENANCE,
                },
                {
                    "phase": "place",
                    "location_id": "sink_01",
                    "primitive_provenance": API_SEMANTIC_PROVENANCE,
                },
            ],
        }
    ]
    run_result = {
        "contract": "realworld_cleanup_v1",
        "backend": "api_semantic_synthetic",
        "cleanup_status": score["status"],
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "policy": "camera_model_policy_baseline",
        "score": score,
        "semantic_substeps": semantic_substeps,
        "cleanup_primitive_evidence": cleanup_primitive_evidence_from_substeps(semantic_substeps),
        "agent_view": {
            "perception_mode": "camera_model_policy",
            "metric_map": {"rooms": [], "inspection_waypoints": []},
            "fixture_hints": {"rooms": []},
            "observed_objects": [
                {
                    "object_id": "observed_001",
                    "category": "dish",
                    "support_estimate": {"fixture_id": "table_01"},
                    "source_observation_id": "raw_fpv_001",
                    "model_provenance": "simulated_camera_model",
                }
            ],
            "raw_fpv_observations": [
                {
                    "observation_id": "raw_fpv_001",
                    "room_id": "kitchen",
                    "waypoint_id": "kitchen_scan_1",
                    "artifact_status": "recorded",
                    "image_artifacts": {"fpv": "robot_views/raw.fpv.png"},
                }
            ],
            "camera_model_policy_evidence": {
                "enabled": True,
                "event_count": 1,
                "candidate_count": 1,
                "model_provenance": "simulated_camera_model",
                "private_truth_included": False,
                "events": [
                    {
                        "observation_id": "raw_fpv_001",
                        "room_id": "kitchen",
                        "model_provenance": "simulated_camera_model",
                        "candidate_count": 1,
                        "registered_observed_handles": ["observed_001"],
                    }
                ],
            },
        },
        "raw_fpv_observations": [
            {
                "observation_id": "raw_fpv_001",
                "room_id": "kitchen",
                "waypoint_id": "kitchen_scan_1",
                "artifact_status": "recorded",
                "image_artifacts": {"fpv": "robot_views/raw.fpv.png"},
            }
        ],
        "camera_model_policy_evidence": {
            "enabled": True,
            "event_count": 1,
            "candidate_count": 1,
            "model_provenance": "simulated_camera_model",
            "private_truth_included": False,
            "events": [
                {
                    "observation_id": "raw_fpv_001",
                    "room_id": "kitchen",
                    "model_provenance": "simulated_camera_model",
                    "candidate_count": 1,
                    "registered_observed_handles": ["observed_001"],
                }
            ],
        },
        "advisory_evaluation": build_advisory_evaluation(
            score=score,
            scenario_id=scenario.scenario_id,
        ),
        "private_evaluation": {
            "generated_mess_count": 1,
            "generated_mess_set": ["mug_01"],
            "acceptable_destination_sets": {"mug_01": ["sink_01"]},
            "mess_restoration_rate": 1.0,
            "sweep_coverage_rate": 1.0,
            "disturbance_count": 0,
        },
    }
    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=[
            {
                "tool": "place",
                "event": "response",
                "response": {
                    "ok": True,
                    "object_id": "observed_001",
                    "receptacle_id": "sink_01",
                    "primitive_provenance": API_SEMANTIC_PROVENANCE,
                },
            }
        ],
        before_snapshot=before,
        after_snapshot=after,
        robot_view_steps=[
            {
                "action": "place observed_001",
                "semantic_phase": "place",
                "robot_pose": {},
                "views": {"fpv": "robot_views/place.fpv.png"},
                "focus": {},
            }
        ],
    )

    html = report_path.read_text(encoding="utf-8")
    ordered_headings = [
        "<h2>Before And After</h2>",
        "<h2>Object Moves</h2>",
        "<h2>Semantic Substeps</h2>",
        "<h2>Robot View Timeline</h2>",
        "<h2>Score</h2>",
        "<h2>Cleanup Primitive Gate</h2>",
        "<h2>Agent View</h2>",
        "<h2>Raw FPV Observations</h2>",
        "<h2>Camera Model Policy</h2>",
        "<h2>Advisory Review</h2>",
        "<h2>Private Evaluation</h2>",
    ]
    positions = [html.index(heading) for heading in ordered_headings]
    assert positions == sorted(positions)
    assert "place/surface" in html


def test_cleanup_report_renders_attached_planner_proof(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    score = score_cleanup(scenario.object_locations(), scenario.private_manifest)
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "after.png",
        title="After",
    )
    proof_dir = tmp_path / "planner_proof"
    proof_dir.mkdir()
    (proof_dir / "initial.png").write_bytes(b"initial")
    (proof_dir / "final.png").write_bytes(b"final")
    run_result = {
        "contract": "realworld_cleanup_v1",
        "cleanup_status": score.status,
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "manipulation_evidence": api_semantic_manipulation_evidence(
            backend="api_semantic_synthetic",
            primitive_summary={API_SEMANTIC_PROVENANCE: 1},
        ),
        "score": score.to_dict(),
        "planner_backed_manipulation_proof": {
            "schema": "planner_backed_cleanup_attachment_v1",
            "status": "planner_backed",
            "primitive_provenance": "planner_backed",
            "planner_backed": True,
            "strict_proof_eligible": True,
            "embodiment": "franka",
            "steps_executed": 2,
            "max_abs_qpos_delta": 0.01,
            "runtime_diagnostics": {"renderer_adapter_enabled": True},
            "image_artifacts": {
                "initial": "planner_proof/initial.png",
                "final": "planner_proof/final.png",
            },
        },
    }

    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=[],
        before_snapshot=before,
        after_snapshot=after,
    )

    html = report_path.read_text(encoding="utf-8")
    assert "Attached Planner-Backed Proof" in html
    assert "Planner Initial" in html
    assert "Planner Final" in html
    assert "Cleanup object moves" in html
    assert "api_semantic" in html
    assert "planner_proof/initial.png" in html
    assert "planner_proof/final.png" in html


def test_cleanup_report_renders_attached_planner_proof_bundle(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    score = score_cleanup(scenario.object_locations(), scenario.private_manifest)
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "after.png",
        title="After",
    )
    for proof_id in ("proof_001", "proof_002"):
        proof_dir = tmp_path / "planner_proof" / proof_id
        proof_dir.mkdir(parents=True)
        (proof_dir / "initial.png").write_bytes(b"initial")
        (proof_dir / "final.png").write_bytes(b"final")
    run_result = {
        "contract": "realworld_cleanup_v1",
        "cleanup_status": score.status,
        "primitive_provenance": "planner_backed",
        "manipulation_evidence": api_semantic_manipulation_evidence(
            backend="api_semantic_synthetic",
            primitive_summary={"planner_backed": 8},
        ),
        "score": score.to_dict(),
        "planner_backed_manipulation_proof": {
            "schema": "planner_backed_cleanup_proof_bundle_v1",
            "status": "planner_backed",
            "primitive_provenance": "planner_backed",
            "planner_backed": True,
            "strict_proof_eligible": True,
            "proof_count": 2,
            "attachments": [
                _proof_attachment("proof_001", "observed_001", "sink_01"),
                _proof_attachment("proof_002", "observed_002", "toy_bin_01"),
            ],
        },
    }

    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=[],
        before_snapshot=before,
        after_snapshot=after,
    )

    html = report_path.read_text(encoding="utf-8")
    assert "Attached Planner-Backed Proofs" in html
    assert "proof_001 Planner Initial" in html
    assert "proof_002 Planner Final" in html
    assert "observed_001" in html
    assert "toy_bin_01" in html
    assert "planner_proof/proof_001/initial.png" in html
    assert "planner_proof/proof_002/final.png" in html


def _proof_attachment(proof_id: str, object_id: str, target_id: str) -> dict[str, object]:
    return {
        "schema": "planner_backed_cleanup_attachment_v1",
        "proof_id": proof_id,
        "status": "planner_backed",
        "primitive_provenance": "planner_backed",
        "planner_backed": True,
        "strict_proof_eligible": True,
        "embodiment": "rby1m",
        "task": "pick_and_place",
        "probe_mode": "execute",
        "upstream_policy_class": "CuroboPickAndPlacePlannerPolicy",
        "steps_executed": 2,
        "max_abs_qpos_delta": 0.01,
        "runtime_diagnostics": {"modules": {"curobo": {"available": True}}},
        "image_artifacts": {
            "initial": f"planner_proof/{proof_id}/initial.png",
            "final": f"planner_proof/{proof_id}/final.png",
        },
        "cleanup_primitive_binding": {
            "schema": "planner_probe_cleanup_primitive_binding_v1",
            "object_id": object_id,
            "target_receptacle_id": target_id,
            "tools": ["navigate_to_object", "pick", "navigate_to_receptacle", "place"],
        },
    }


def test_planner_manipulation_probe_report_uses_shared_underlay(tmp_path: Path) -> None:
    stdout = tmp_path / "planner_probe_stdout.txt"
    stderr = tmp_path / "planner_probe_stderr.txt"
    stdout.write_text("{}", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    run_result = {
        "contract": "planner_backed_manipulation_probe_v1",
        "backend": "molmospaces_subprocess",
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": blocked_planner_probe_evidence(
            backend="molmospaces_subprocess",
            embodiment="franka",
            task="pick_and_place",
            probe_mode="config_import",
            blockers=[
                {
                    "code": "execution_not_attempted",
                    "message": "Planner execution was not attempted.",
                }
            ],
            upstream_policy_class="PickAndPlacePlannerPolicy",
        ),
        "artifacts": {
            "stdout": str(stdout),
            "stderr": str(stderr),
        },
    }
    run_result["manipulation_evidence"]["runtime_diagnostics"] = {
        "python_executable": "/tmp/molmospaces/.venv/bin/python",
        "python_version": "3.11.8",
        "faulthandler_enabled": True,
        "renderer_adapter_enabled": True,
        "renderer_device_id": 0,
        "mujoco_gl_env": "egl",
        "pyopengl_platform_env": "egl",
        "cuda_home_env": "/usr/local/cuda",
        "torch_cuda_arch_list_env": "8.9",
        "torch": {
            "available": True,
            "version": "2.7.1+cu128",
            "cuda_version": "12.8",
            "cuda_available": True,
            "cpp_extension_cuda_home": "/usr/local/cuda",
        },
        "cuda_visible_devices_env": "0",
        "pytorch_cuda_alloc_conf_env": "expandable_segments:True",
        "cuda_memory": {
            "available": True,
            "device_count": 1,
            "current_device_index": 0,
            "devices": [
                {
                    "index": 0,
                    "name": "NVIDIA RTX 3500 Ada Generation Laptop GPU",
                    "total_memory_bytes": 12884901888,
                    "compute_capability": "8.9",
                }
            ],
            "current_snapshot": {
                "stage": "runtime_diagnostics",
                "elapsed_s": 0.02,
                "device_index": 0,
                "device_name": "NVIDIA RTX 3500 Ada Generation Laptop GPU",
                "free_bytes": 298844160,
                "total_bytes": 12455405158,
                "torch_allocated_bytes": 10458234880,
                "torch_reserved_bytes": 11408506880,
            },
        },
        "modules": {
            "curobo": {"available": False, "version": None},
            "molmo_spaces": {"available": True, "version": "0.1.0"},
        },
        "curobo_extension_cache": {
            "configured_dir": "output/cache",
            "extensions": {
                "lbfgs_step_cu": {
                    "build_dir": "output/cache/lbfgs_step_cu",
                    "so_exists": False,
                    "lock_exists": True,
                    "files": [{"name": "lock", "size_bytes": 0}],
                },
                "geom_cu": {
                    "build_dir": "output/cache/geom_cu",
                    "so_exists": True,
                    "lock_exists": False,
                    "files": [{"name": "geom_cu.so", "size_bytes": 12}],
                },
            },
        },
        "warp_compatibility": {
            "available": True,
            "version": "1.13.0",
            "has_torch_attr": True,
            "has_device_from_torch": True,
            "has_from_torch": True,
            "has_stream_from_torch": True,
            "adapter": {
                "applied": True,
                "provided": ["warp.torch.device_from_torch"],
            },
        },
    }
    run_result["manipulation_evidence"]["worker_stage_events"] = [
        {
            "event": "worker_start",
            "stage": "worker_start",
            "elapsed_s": 0.01,
            "embodiment": "rby1m",
            "probe_mode": "config_import",
        },
        {
            "event": "rby1m_config_import_start",
            "stage": "rby1m_config_import",
            "elapsed_s": 0.02,
        },
    ]
    run_result["manipulation_evidence"]["cuda_memory_snapshots"] = [
        {
            "stage": "execute_policy_construct_before",
            "elapsed_s": 10.2,
            "device_index": 0,
            "device_name": "NVIDIA RTX 3500 Ada Generation Laptop GPU",
            "free_bytes": 2147483648,
            "total_bytes": 12884901888,
            "torch_allocated_bytes": 1073741824,
            "torch_reserved_bytes": 2147483648,
        },
        {
            "stage": "execute_policy_run_start",
            "elapsed_s": 24.5,
            "device_index": 0,
            "device_name": "NVIDIA RTX 3500 Ada Generation Laptop GPU",
            "free_bytes": 298844160,
            "total_bytes": 12455405158,
            "torch_allocated_bytes": 10458234880,
            "torch_reserved_bytes": 11408506880,
        },
    ]
    run_result["manipulation_evidence"]["curobo_memory_profile"] = {
        "profile": "low",
        "applied": True,
        "before": {
            "policy": {
                "batch_size": 4,
                "max_batch_plan_attempts": 4,
                "enable_collision_avoidance": True,
            },
            "planners": {
                "left": {
                    "num_trajopt_seeds": 12,
                    "num_ik_seeds": 128,
                    "max_attempts": 15,
                    "trajopt_tsteps": 48,
                    "enable_finetune_trajopt": True,
                }
            },
        },
        "after": {
            "policy": {
                "batch_size": 1,
                "max_batch_plan_attempts": 1,
                "enable_collision_avoidance": True,
            },
            "planners": {
                "left": {
                    "num_trajopt_seeds": 1,
                    "num_ik_seeds": 16,
                    "max_attempts": 1,
                    "trajopt_tsteps": 24,
                    "enable_finetune_trajopt": False,
                }
            },
        },
    }
    run_result["manipulation_evidence"]["sampled_task_binding"] = {
        "schema": "planner_probe_sampled_task_binding_v1",
        "pickup_obj_name": "pickup/body",
        "place_receptacle_name": "sink/body",
        "place_target_name": "sink/body",
    }
    run_result["manipulation_evidence"]["requested_cleanup_primitive_binding"] = {
        "schema": "planner_probe_cleanup_primitive_binding_v1",
        "requested": True,
        "object_id": "pickup/body",
        "target_receptacle_id": "sink/body",
        "source_receptacle_id": "counter/body",
        "planner_object_id": "pickup/body",
        "planner_target_receptacle_id": "sink/body",
        "tools": ["navigate_to_object", "pick", "navigate_to_receptacle", "place"],
    }
    run_result["manipulation_evidence"]["cleanup_primitive_binding"] = {
        "schema": "planner_probe_cleanup_primitive_binding_v1",
        "object_id": "pickup/body",
        "target_receptacle_id": "sink/body",
        "source_receptacle_id": "counter/body",
        "planner_object_id": "pickup/body",
        "planner_target_receptacle_id": "sink/body",
        "tools": ["navigate_to_object", "pick", "navigate_to_receptacle", "place"],
    }
    run_result["manipulation_evidence"]["last_worker_stage"] = "rby1m_config_import"
    run_result["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(run_result)

    report_path = render_planner_manipulation_report(run_dir=tmp_path, run_result=run_result)
    html = report_path.read_text(encoding="utf-8")

    assert "Planner-Backed Manipulation Probe" in html
    assert "Manipulation Provenance" in html
    assert "Runtime Diagnostics" in html
    assert "Planner Probe Cleanup Binding" in html
    assert "pickup/body" in html
    assert "sink/body" in html
    assert "Planner object alias" in html
    assert "navigate_to_receptacle" in html
    assert "CUDA Memory Headroom" in html
    assert "CuRobo Memory Profile" in html
    assert "CuRobo Extension Cache" in html
    assert "lbfgs_step_cu" in html
    assert "Warp Compatibility" in html
    assert "Adapter applied" in html
    assert "Worker Stage Timeline" in html
    assert "Capability Blockers" in html
    assert "PickAndPlacePlannerPolicy" in html
    assert "rby1m_config_import_start" in html
    assert "rby1m_config_import" in html
    assert "faulthandler=True" in html
    assert "renderer_adapter=True" in html
    assert "MUJOCO_GL=egl" in html
    assert "CUDA_HOME=/usr/local/cuda" in html
    assert "torch_cuda_available=True" in html
    assert "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" in html
    assert "execute_policy_run_start" in html
    assert "num_ik_seeds" in html
    assert "Collision avoidance" in html
    assert "10.6 GiB" in html
    assert "curobo" in html
    assert "RBY1M CuRobo Gate" in html
    assert "wrong_embodiment" in html
