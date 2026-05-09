from __future__ import annotations

from pathlib import Path

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.report import render_cleanup_report, write_state_snapshot
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
        "score": score.to_dict(),
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
    assert "mug_01" in html
    assert "Semantic acceptability" in html
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
    assert "navigate_to_object -&gt; pick -&gt; navigate_to_receptacle" in html
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
