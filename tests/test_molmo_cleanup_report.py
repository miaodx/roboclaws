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
        "modules": {
            "curobo": {"available": False, "version": None},
            "molmo_spaces": {"available": True, "version": "0.1.0"},
        },
    }
    run_result["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(run_result)

    report_path = render_planner_manipulation_report(run_dir=tmp_path, run_result=run_result)
    html = report_path.read_text(encoding="utf-8")

    assert "Planner-Backed Manipulation Probe" in html
    assert "Manipulation Provenance" in html
    assert "Runtime Diagnostics" in html
    assert "Capability Blockers" in html
    assert "PickAndPlacePlannerPolicy" in html
    assert "faulthandler=True" in html
    assert "renderer_adapter=True" in html
    assert "MUJOCO_GL=egl" in html
    assert "curobo" in html
    assert "RBY1M CuRobo Gate" in html
    assert "wrong_embodiment" in html
