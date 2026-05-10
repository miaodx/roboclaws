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
    render_planner_proof_bundle_runner_report,
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
    assert "<td>nav</td>" in html
    assert "<td>object</td>" in html
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
    assert "Role" in html
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
    assert "<td>place</td>" in html
    assert "<td>surface</td>" in html


def test_cleanup_report_renders_planner_proof_requests_before_agent_view(
    tmp_path: Path,
) -> None:
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
        "planner_cleanup_bridge_evidence": {
            "status": "blocked_capability",
            "target_runtime": {"embodiment": "rby1m"},
            "cleanup_primitives": {"status": "blocked_capability", "subphase_count": 4},
            "blockers": [],
            "target_runtime_ready": True,
            "cleanup_primitives_ready": False,
            "planner_backed": False,
        },
        "planner_proof_requests": {
            "schema": "planner_cleanup_proof_requests_v1",
            "request_count": 2,
            "ready_count": 1,
            "agent_view_exposed": False,
            "blockers": [{"code": "planner_binding_backend_unavailable"}],
            "requests": [
                {
                    "request_id": "proof_001",
                    "ready": True,
                    "object_id": "observed_001",
                    "source_receptacle_id": "counter_01",
                    "target_receptacle_id": "sink_01",
                    "tools": [
                        "navigate_to_object",
                        "pick",
                        "navigate_to_receptacle",
                        "place",
                    ],
                    "binding": {
                        "planner_object_id": "pickup/body",
                        "planner_target_receptacle_id": "sink/body",
                    },
                    "planner_probe_args": {},
                    "blockers": [],
                },
                {
                    "request_id": "proof_002",
                    "ready": False,
                    "object_id": "observed_002",
                    "source_receptacle_id": "table_01",
                    "target_receptacle_id": "cabinet_01",
                    "tools": ["navigate_to_object"],
                    "binding": {},
                    "planner_probe_args": {},
                    "blockers": [{"code": "planner_binding_backend_unavailable"}],
                },
            ],
        },
        "agent_view": {
            "contract": "realworld_cleanup_v1",
            "metric_map": {"rooms": [], "inspection_waypoints": []},
            "fixture_hints": {"rooms": []},
            "observed_objects": [{"object_id": "observed_001", "category": "dish"}],
        },
        "private_evaluation": {
            "generated_mess_count": 1,
            "generated_mess_set": ["mug_01"],
            "acceptable_destination_sets": {"mug_01": ["sink_01"]},
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
    ordered_headings = [
        "<h2>Planner Cleanup Bridge</h2>",
        "<h2>Planner Proof Requests</h2>",
        "<h2>Agent View</h2>",
    ]
    positions = [html.index(heading) for heading in ordered_headings]
    assert positions == sorted(positions)
    assert "Requests" in html
    assert "proof_001" in html
    assert "ready" in html
    assert "blocked" in html
    assert "observed_001" in html
    assert "counter_01" in html
    assert "sink_01" in html
    assert "navigate_to_object, pick, navigate_to_receptacle, place" in html
    assert "pickup/body" in html
    assert "sink/body" in html
    assert "planner_binding_backend_unavailable" in html
    agent_view_html = html[html.index("<h2>Agent View</h2>") :]
    assert "pickup/body" not in agent_view_html
    assert "sink/body" not in agent_view_html


def test_planner_proof_bundle_runner_report_renders_commands(tmp_path: Path) -> None:
    manifest = {
        "schema": "planner_cleanup_proof_bundle_run_manifest_v1",
        "status": "dry_run",
        "cleanup_run_result": str(tmp_path / "cleanup" / "run_result.json"),
        "output_dir": str(tmp_path),
        "proof_request_count": 1,
        "ready_request_count": 1,
        "proof_request_selection": {
            "schema": "planner_cleanup_proof_request_selection_v1",
            "mode": "exclude_task_feasibility_blocked",
            "ready_request_count": 1,
            "selected_count": 1,
            "excluded_count": 1,
            "generated_fallback_request_count": 1,
            "fallback_required": False,
            "selected_request_ids": ["proof_001_fallback_01"],
            "selected_requests": [
                {
                    "request_id": "proof_001_fallback_01",
                    "request_type": "fallback_generated",
                    "source_request_id": "proof_001",
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "prior_task_feasibility_status": "blocked",
                    "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                    "prior_result_match_kind": "request_id",
                }
            ],
            "excluded_requests": [
                {
                    "request_id": "proof_001",
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "reason": "prior_task_feasibility_blocked",
                    "prior_task_feasibility_status": "blocked",
                    "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                    "prior_task_feasibility_blocker_summary": (
                        "3 grasp failures; 1 candidate-removal calls"
                    ),
                    "prior_result_match_kind": "request_id",
                    "prior_blockers": [{"code": "HouseInvalidForTask"}],
                }
            ],
            "target_feasibility_blocker_count": 2,
            "target_feasibility_blockers": [
                {
                    "kind": "source_request",
                    "source_request_id": "proof_001",
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "reason": "prior_task_feasibility_blocked",
                    "prior_task_feasibility_status": "blocked",
                    "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                    "prior_task_feasibility_blocker_summary": (
                        "3 grasp failures; 1 candidate-removal calls"
                    ),
                    "prior_result_match_kind": "request_id",
                    "prior_blockers": [{"code": "HouseInvalidForTask"}],
                },
                {
                    "kind": "fallback_pair",
                    "source_request_id": "proof_001",
                    "object_alias": "pickup/body",
                    "target_alias": "sink/body_alt",
                    "derived_from": "proof_001_fallback_02",
                    "reason": "prior_task_feasibility_blocked_pair",
                    "prior_task_feasibility_status": "blocked",
                    "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                    "prior_task_feasibility_blocker_summary": (
                        "3 grasp failures; 1 candidate-removal calls"
                    ),
                    "prior_result_match_kind": "request_id",
                    "last_worker_stage": "worker_exception",
                    "prior_report": str(tmp_path / "prior-proof" / "report.html"),
                    "prior_blockers": [{"code": "HouseInvalidForTask"}],
                },
            ],
            "grasp_feasibility_blocker_count": 2,
            "grasp_feasibility_blockers": [
                {
                    "kind": "source_request",
                    "source_request_id": "proof_001",
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "reason": "prior_task_feasibility_blocked",
                    "prior_task_feasibility_status": "blocked",
                    "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                    "prior_task_feasibility_blocker_summary": (
                        "3 grasp failures; 1 candidate-removal calls"
                    ),
                    "prior_result_match_kind": "request_id",
                    "prior_blockers": [{"code": "HouseInvalidForTask"}],
                },
                {
                    "kind": "fallback_pair",
                    "source_request_id": "proof_001",
                    "object_alias": "pickup/body",
                    "target_alias": "sink/body_alt",
                    "derived_from": "proof_001_fallback_02",
                    "reason": "prior_task_feasibility_blocked_pair",
                    "prior_task_feasibility_status": "blocked",
                    "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                    "prior_task_feasibility_blocker_summary": (
                        "3 grasp failures; 1 candidate-removal calls"
                    ),
                    "prior_result_match_kind": "request_id",
                    "last_worker_stage": "worker_exception",
                    "prior_report": str(tmp_path / "prior-proof" / "report.html"),
                    "prior_blockers": [{"code": "HouseInvalidForTask"}],
                },
            ],
            "fallback_generation": {
                "schema": "planner_cleanup_proof_request_fallback_generation_v1",
                "status": "generated",
                "enabled": True,
                "generated_request_count": 1,
                "discovered_alias_count": 1,
                "filtered_alias_count": 1,
                "filtered_pair_count": 1,
                "generated_requests": [
                    {
                        "request_id": "proof_001_fallback_01",
                        "source_request_id": "proof_001",
                        "ready": True,
                        "object_id": "observed_001",
                        "target_receptacle_id": "sink_01",
                        "planner_probe_args": {
                            "--cleanup-object-id": "observed_001",
                            "--cleanup-target-receptacle-id": "sink_01",
                            "--cleanup-planner-object-id": "pickup/alt",
                            "--cleanup-planner-target-receptacle-id": "sink/alt",
                        },
                        "fallback_request": {
                            "source_request_id": "proof_001",
                            "reason": "prior_task_feasibility_blocked",
                            "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                            "prior_task_feasibility_blocker_summary": (
                                "3 grasp failures; 1 candidate-removal calls"
                            ),
                            "prior_result_match_kind": "request_id",
                            "prior_blockers": [{"code": "HouseInvalidForTask"}],
                        },
                    }
                ],
                "discovered_aliases": [
                    {
                        "source_request_id": "proof_001",
                        "axis": "target",
                        "alias": "sink/body_alt",
                        "derived_from": "proof_001_fallback_01",
                        "invalid_alias": "Sink|1|2",
                        "reason": "valid_name_sibling_from_prior_keyerror",
                    }
                ],
                "filtered_aliases": [
                    {
                        "source_request_id": "proof_001",
                        "axis": "target",
                        "alias": "Sink|1|2",
                        "reason": "not_exact_scene_runtime_alias",
                    }
                ],
                "filtered_pairs": [
                    {
                        "source_request_id": "proof_001",
                        "object_alias": "pickup/body",
                        "target_alias": "sink/body_alt",
                        "derived_from": "proof_001_fallback_02",
                        "reason": "prior_task_feasibility_blocked_pair",
                        "prior_task_feasibility_blocker_kind": "grasp_feasibility",
                        "prior_task_feasibility_blocker_summary": (
                            "3 grasp failures; 1 candidate-removal calls"
                        ),
                        "prior_result_match_kind": "request_id",
                        "prior_blockers": [{"code": "HouseInvalidForTask"}],
                    }
                ],
            },
        },
        "warmup": {
            "kind": "rby1m_curobo_config_import",
            "output_dir": str(tmp_path / "warmup"),
            "run_result": str(tmp_path / "warmup" / "run_result.json"),
            "report": str(tmp_path / "warmup" / "report.html"),
            "command": [
                "python",
                "probe.py",
                "--probe-mode",
                "config_import",
                "--torch-extensions-dir",
                str(tmp_path / "torch_extensions"),
            ],
        },
        "prior_proof_result_summary": {
            "schema": "merged_prior_planner_proof_result_summary_v1",
            "result_count": 1,
            "view_artifact_count": 2,
            "results": [
                {
                    "request_id": "standalone_observed_001_to_sink_01",
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "run_result": str(tmp_path / "prior-proof" / "run_result.json"),
                    "report": str(tmp_path / "prior-proof" / "report.html"),
                    "status": "blocked_capability",
                    "task_feasibility_status": "blocked",
                    "task_feasibility_blocker_kind": "grasp_feasibility",
                    "task_feasibility_blocker_summary": (
                        "3 grasp failures; 1 candidate-removal calls"
                    ),
                    "views": [
                        {
                            "label": "initial",
                            "path": str(tmp_path / "prior-proof" / "initial.png"),
                        },
                        {
                            "label": "final",
                            "path": str(tmp_path / "prior-proof" / "final.png"),
                        },
                    ],
                }
            ],
        },
        "command_count": 1,
        "commands": [
            {
                "request_id": "proof_001_fallback_01",
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "run_result": str(tmp_path / "proofs" / "001" / "run_result.json"),
                "report": str(tmp_path / "proofs" / "001" / "report.html"),
                "command": [
                    "python",
                    "probe.py",
                    "--cleanup-object-id",
                    "observed_001",
                    "--cleanup-planner-target-receptacle-id",
                    "sink/alt",
                ],
            }
        ],
        "proof_result_summary": {
            "schema": "planner_cleanup_proof_result_summary_v1",
            "expected_count": 1,
            "result_count": 1,
            "planner_backed_count": 0,
            "blocked_count": 1,
            "timeout_count": 1,
            "rby1m_config_import_timeout_count": 1,
            "missing_result_count": 0,
            "cleanup_binding_promoted_count": 0,
            "execution_attempted_count": 0,
            "task_feasibility_blocked_count": 1,
            "grasp_feasibility_blocked_count": 1,
            "grasp_feasibility_signature_count": 1,
            "grasp_feasibility_signature_counts": [
                {
                    "schema": "planner_grasp_feasibility_signature_group_v1",
                    "pattern_key": "grasp=3;removals=1",
                    "summary": "3 grasp failures; 1 candidate-removal calls",
                    "count": 1,
                    "request_ids": ["proof_001"],
                    "object_names": ["pickup/body"],
                    "robot_placement_failure_count": 1,
                    "place_robot_near_call_count": 1,
                    "image_artifact_count": 2,
                }
            ],
            "worker_stage_event_count": 2,
            "last_worker_stage_counts": {"rby1m_config_import": 1},
            "view_artifact_count": 2,
            "results": [
                {
                    "request_id": "proof_001",
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "run_result": str(tmp_path / "proofs" / "001" / "run_result.json"),
                    "report": str(tmp_path / "proofs" / "001" / "report.html"),
                    "run_result_exists": True,
                    "report_exists": True,
                    "status": "blocked_capability",
                    "planner_backed": False,
                    "cleanup_binding_promoted": False,
                    "execution_attempted": False,
                    "task_feasibility_status": "blocked",
                    "task_feasibility_blocker_kind": "grasp_feasibility",
                    "task_feasibility_blocker_summary": (
                        "3 grasp failures; 1 candidate-removal calls"
                    ),
                    "grasp_feasibility_signature": {
                        "schema": "planner_grasp_feasibility_signature_v1",
                        "kind": "grasp_feasibility",
                        "pattern_key": "grasp=3;removals=1",
                        "summary": "3 grasp failures; 1 candidate-removal calls",
                        "grasp_failure_count": 3,
                        "candidate_removal_count": 1,
                        "robot_placement_attempt_count": 1,
                        "robot_placement_failure_count": 1,
                        "place_robot_near_call_count": 1,
                        "object_name_count": 1,
                        "object_names": ["pickup/body"],
                        "image_artifact_count": 2,
                    },
                    "visual_status": "views_recorded",
                    "blockers": [
                        {"code": "HouseInvalidForTask", "message": "robot placement"},
                        {"code": "timeout", "message": "Probe exceeded 1.0s"},
                    ],
                    "cleanup_binding_blockers": [],
                    "last_worker_stage": "rby1m_config_import",
                    "worker_stage_event_count": 2,
                    "worker_stage_events": [
                        {"elapsed_s": 0.1, "event": "worker_start", "stage": "worker_start"},
                        {
                            "elapsed_s": 3.2,
                            "event": "rby1m_config_import_start",
                            "stage": "rby1m_config_import",
                        },
                    ],
                    "stdout": str(tmp_path / "proofs" / "001" / "planner_probe_stdout.txt"),
                    "stderr": str(tmp_path / "proofs" / "001" / "planner_probe_stderr.txt"),
                    "requested_cleanup_primitive_binding": {
                        "scene_xml": "/tmp/scene.xml",
                        "planner_object_id": "pickup/body",
                        "planner_target_receptacle_id": "sink/body",
                    },
                    "task_sampler_robot_placement_profile": {
                        "profile": "relaxed",
                        "requested": True,
                        "applied": True,
                        "place_robot_near_overrides": {"max_tries": 50},
                    },
                    "cleanup_task_sampler_adapter": {
                        "applied": True,
                        "task_sampler_class": "PickAndPlaceTaskSampler",
                        "planner_target_receptacle_id": "sink/body",
                    },
                    "task_sampler_failure_diagnostics": {
                        "applied": True,
                        "task_sampler_class": "PickAndPlaceTaskSampler",
                        "robot_placement_attempt_count": 1,
                        "robot_placement_failure_count": 1,
                        "asset_failure_count": 1,
                        "grasp_failure_count": 3,
                        "grasp_failures": [
                            {
                                "object_name": "pickup/body",
                                "count_before": 2,
                                "count_after": 3,
                                "max_failures": 2,
                                "candidate_count_before": 1,
                                "candidate_count_after": 0,
                                "removed_candidate": True,
                            }
                        ],
                        "last_placement_scene_diagnostic": {
                            "target_name": "pickup/body",
                            "valid_free_point_count": 3,
                            "valid_neighborhood_fraction": 0.000017,
                            "nearest_free_point_distance_m": 0.42,
                        },
                        "last_robot_placement_failure": {
                            "pickup_obj_name": "pickup/body",
                            "message": "Failed to place robot near object: pickup/body",
                        },
                    },
                    "views": [
                        {
                            "label": "initial",
                            "path": str(tmp_path / "proofs" / "001" / "initial.png"),
                        },
                        {
                            "label": "final",
                            "path": str(tmp_path / "proofs" / "001" / "final.png"),
                        },
                    ],
                }
            ],
        },
        "cleanup_command": ["python", "cleanup.py", "--planner-proof-run-result", "proof.json"],
    }

    report_path = render_planner_proof_bundle_runner_report(
        output_dir=tmp_path,
        manifest=manifest,
    )

    html = report_path.read_text(encoding="utf-8")
    assert "Planner Proof Bundle Runner" in html
    assert "Source Cleanup Artifact" in html
    assert "Proof Request Selection" in html
    assert "Prior Proof Evidence" in html
    assert "Proof Probe Commands" in html
    assert "Proof Probe Results" in html
    assert "Cleanup Rerun Command" in html
    assert "dry_run" in html
    assert "proof_001" in html
    assert "proof_001_fallback_01" in html
    assert "observed_001" in html
    assert "sink/alt" in html
    assert "HouseInvalidForTask" in html
    assert "Fallback status" in html
    assert "generated" in html
    assert "Fallback required" in html
    assert "prior_task_feasibility_blocked" in html
    assert "Generated Fallback Requests" in html
    assert "Discovered Runtime Aliases" in html
    assert "Discovered aliases" in html
    assert "sink/body_alt" in html
    assert "valid_name_sibling_from_prior_keyerror" in html
    assert "Filtered Fallback Aliases" in html
    assert "Filtered aliases" in html
    assert "Sink|1|2" in html
    assert "not_exact_scene_runtime_alias" in html
    assert "Filtered Fallback Pairs" in html
    assert "Filtered pairs" in html
    assert "Target Feasibility Blockers" in html
    assert "Target blockers" in html
    assert "Grasp Feasibility Blockers" in html
    assert "Grasp Feasibility Blocker Matrix" in html
    assert "Grasp blockers" in html
    assert "Prior match" in html
    assert "request_id" in html
    assert "source_request" in html
    assert "fallback_pair" in html
    assert "worker_exception" in html
    assert "pickup/body" in html
    assert "sink/body_alt" in html
    assert "prior_task_feasibility_blocked_pair" in html
    assert "fallback_generated" in html
    assert "RBY1M/CuRobo Warmup" in html
    assert "config_import" in html
    assert "torch_extensions" in html
    assert "Task feasibility" in html
    assert "blocked" in html
    assert "Grasp-feasible blocked" in html
    assert "Grasp Feasibility Signature Matrix" in html
    assert "Diagnostic views" in html
    assert "Task feasibility blocker" in html
    assert "grasp_feasibility" in html
    assert "3 grasp failures; 1 candidate-removal calls" in html
    assert "standalone_observed_001_to_sink_01" in html
    assert "prior-proof/run_result.json" in html
    assert "prior-proof/report.html" in html
    assert "prior-proof/initial.png" in html
    assert "prior-proof/final.png" in html
    assert 'src="prior-proof/initial.png"' in html
    assert 'src="prior-proof/final.png"' in html
    assert 'src="proofs/001/initial.png"' in html
    assert 'src="proofs/001/final.png"' in html
    assert f'src="{tmp_path}/prior-proof/initial.png"' not in html
    assert f'src="{tmp_path}/proofs/001/initial.png"' not in html
    assert "Robot placement profile" in html
    assert "relaxed" in html
    assert "place_robot_near max tries" in html
    assert "Exact sampler adapter applied" in html
    assert "Exact sampler adapter class" in html
    assert "PickAndPlaceTaskSampler" in html
    assert "Exact sampler adapter target" in html
    assert "Task sampler placement failures" in html
    assert "Task sampler asset failures" in html
    assert "Post-placement grasp failures" in html
    assert "Post-Placement Rejection Views" in html
    assert "Post-placement rejection flow: pickup/body" in html
    assert "Placement free-space fraction" in html
    assert "0.000017" in html
    assert "Failed to place robot near object: pickup/body" in html
    assert "sink/body" in html
    assert "Timeouts" in html
    assert "Config-import timeouts" in html
    assert "Last worker stage" in html
    assert "rby1m_config_import" in html
    assert "Worker stages" in html
    assert "planner_probe_stdout.txt" in html
    assert "planner_probe_stderr.txt" in html
    assert "initial.png" in html
    assert "final.png" in html
    assert "report.html" in html
    assert "--planner-proof-run-result" in html


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
    run_result["manipulation_evidence"]["cleanup_task_config"] = {
        "schema": "planner_probe_exact_cleanup_task_config_v1",
        "applied": True,
        "scene_xml": "/tmp/scene.xml",
        "planner_object_id": "pickup/body",
        "planner_target_receptacle_id": "sink/body",
    }
    run_result["manipulation_evidence"]["task_sampler_robot_placement_profile"] = {
        "schema": "planner_probe_task_sampler_robot_placement_profile_v1",
        "profile": "relaxed",
        "requested": True,
        "applied": True,
        "before": {
            "base_pose_sampling_radius_range": [0.0, 0.7],
            "robot_safety_radius": 0.35,
            "check_robot_placement_visibility": True,
            "max_robot_placement_attempts": 10,
        },
        "after": {
            "base_pose_sampling_radius_range": [0.0, 1.2],
            "robot_safety_radius": 0.15,
            "check_robot_placement_visibility": False,
            "max_robot_placement_attempts": 50,
        },
        "applied_overrides": {"robot_safety_radius": 0.15},
        "place_robot_near_overrides": {"max_tries": 50},
    }
    run_result["manipulation_evidence"]["cleanup_task_sampler_adapter"] = {
        "schema": "planner_probe_exact_cleanup_task_sampler_adapter_v1",
        "applied": True,
        "task_sampler_class": "PickAndPlaceTaskSampler",
        "planner_target_receptacle_id": "sink/body",
    }
    run_result["manipulation_evidence"]["task_sampler_failure_diagnostics"] = {
        "schema": "planner_probe_task_sampler_failure_diagnostics_v1",
        "applied": True,
        "task_sampler_class": "PickAndPlaceTaskSampler",
        "robot_placement_config": {
            "base_pose_sampling_radius_range": [0.0, 0.7],
            "robot_safety_radius": 0.15,
            "check_robot_placement_visibility": True,
            "max_robot_placement_attempts": 10,
        },
        "hooks": ["_sample_and_place_robot", "report_asset_failure"],
        "robot_placement_attempt_count": 1,
        "robot_placement_failure_count": 1,
        "asset_failure_count": 1,
        "candidate_removal_count": 1,
        "candidate_effective_removal_count": 0,
        "candidate_name_miss_count": 1,
        "grasp_threshold_exceeded_count": 1,
        "robot_placement_attempts": [
            {
                "attempt_index": 1,
                "pickup_obj_name": "pickup/body",
                "asset_uid": "asset-book",
                "result": "failed",
                "exception_type": "RobotPlacementError",
                "message": "Failed to place robot near object: pickup/body",
            }
        ],
        "asset_failures": [
            {
                "asset_uid": "asset-book",
                "reason": "robot placement failed",
            }
        ],
        "grasp_failure_count": 1,
        "grasp_failures": [
            {
                "object_name": "pickup/body",
                "count_before": 2,
                "count_after": 3,
                "max_failures": 2,
                "threshold_exceeded": True,
                "threshold_crossed": True,
                "candidate_count_before": 1,
                "candidate_count_after": 1,
                "candidate_name_present_before": False,
                "candidate_name_present_after": False,
                "candidate_removal_call_count_delta": 1,
                "removed_candidate": False,
            }
        ],
        "place_robot_near_calls": [
            {
                "call_index": 1,
                "requested": {"max_tries": 10},
                "effective": {
                    "max_tries": 50,
                    "robot_safety_radius": 0.15,
                    "check_camera_visibility": False,
                },
                "result": False,
            }
        ],
        "placement_scene_diagnostic_count": 1,
        "placement_scene_diagnostics": [
            {
                "schema": "planner_probe_placement_scene_diagnostic_v1",
                "call_index": 1,
                "target_name": "pickup/body",
                "target_position": [1.0, 2.0, 0.5],
                "sampling_radius_range": [0.0, 1.2],
                "sampling_area_m2": 4.523893,
                "robot_safety_radius": 0.15,
                "px_per_m": 200,
                "total_free_point_count": 100,
                "valid_free_point_count": 3,
                "valid_neighborhood_fraction": 0.000017,
                "low_free_space": True,
                "nearest_free_point_distance_m": 0.42,
                "nearest_free_point": [1.42, 2.0, 0.0],
                "radius_band_counts": [
                    {"radius_min_m": 0.0, "radius_max_m": 0.25, "free_point_count": 0},
                    {"radius_min_m": 0.25, "radius_max_m": 0.5, "free_point_count": 1},
                ],
            }
        ],
        "last_placement_scene_diagnostic": {
            "schema": "planner_probe_placement_scene_diagnostic_v1",
            "call_index": 1,
            "target_name": "pickup/body",
            "target_position": [1.0, 2.0, 0.5],
            "sampling_radius_range": [0.0, 1.2],
            "sampling_area_m2": 4.523893,
            "robot_safety_radius": 0.15,
            "px_per_m": 200,
            "total_free_point_count": 100,
            "valid_free_point_count": 3,
            "valid_neighborhood_fraction": 0.000017,
            "low_free_space": True,
            "nearest_free_point_distance_m": 0.42,
            "nearest_free_point": [1.42, 2.0, 0.0],
            "radius_band_counts": [
                {"radius_min_m": 0.0, "radius_max_m": 0.25, "free_point_count": 0},
                {"radius_min_m": 0.25, "radius_max_m": 0.5, "free_point_count": 1},
            ],
        },
        "candidate_removals": [
            {
                "object_name": "pickup/body",
                "candidate_count_before": 1,
                "candidate_count_after": 1,
                "candidate_name_present_before": False,
                "candidate_name_present_after": False,
                "effective_removal": False,
            }
        ],
        "last_robot_placement_failure": {
            "pickup_obj_name": "pickup/body",
            "message": "Failed to place robot near object: pickup/body",
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
    assert "Planner Probe Diagnostic Views" in html
    assert "Task sampler diagnostic: pickup/body" in html
    assert "Planner Probe Cleanup Binding" in html
    assert "Task Sampler Robot Placement Profile" in html
    assert "relaxed" in html
    assert "place_robot_near max tries" in html
    assert "Exact task config applied" in html
    assert "Exact sampler adapter class" in html
    assert "PickAndPlaceTaskSampler" in html
    assert "Task Sampler Failure Diagnostics" in html
    assert "Placement failures" in html
    assert "Effective max tries" in html
    assert "Post-Placement Candidate Rejections" in html
    assert "Post-Placement Rejection Views" in html
    assert "Post-placement rejection flow: pickup/body" in html
    assert "Removed by grasp threshold" in html
    assert "Candidate Removal Effectiveness" in html
    assert "Effective removals" in html
    assert "Candidate name misses" in html
    assert "Removal-call delta" in html
    assert "Placement Scene Diagnostics" in html
    assert "Free-space fraction" in html
    assert "0.000017" in html
    assert "Nearest free distance" in html
    assert "Failed to place robot near object: pickup/body" in html
    assert "asset-book" in html
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


def test_planner_manipulation_probe_report_renders_diagnostic_image_artifacts(
    tmp_path: Path,
) -> None:
    views = tmp_path / "planner_views"
    views.mkdir()
    image = views / "post_placement_attempt_001_head_camera.png"
    image.write_bytes(b"not a real image but enough for an html src")
    run_result = {
        "contract": "planner_backed_manipulation_probe_v1",
        "backend": "molmospaces_subprocess",
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": blocked_planner_probe_evidence(
            backend="molmospaces_subprocess",
            embodiment="rby1m",
            task="pick_and_place",
            probe_mode="execute",
            blockers=[{"code": "HouseInvalidForTask", "message": "candidate removed"}],
            execution_attempted=True,
        ),
        "artifacts": {"stdout": "stdout.txt", "stderr": "stderr.txt"},
    }
    run_result["manipulation_evidence"]["image_artifacts"] = {
        "post_placement_attempt_001_head_camera": (
            "planner_views/post_placement_attempt_001_head_camera.png"
        )
    }
    run_result["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(run_result)

    report_path = render_planner_manipulation_report(run_dir=tmp_path, run_result=run_result)

    html = report_path.read_text(encoding="utf-8")
    assert "Planner Probe Views" in html
    assert "Post Placement Attempt 001 Head Camera" in html
    assert 'src="planner_views/post_placement_attempt_001_head_camera.png"' in html
