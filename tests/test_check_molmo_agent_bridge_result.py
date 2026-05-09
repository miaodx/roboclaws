from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SMOKE_PATH = REPO_ROOT / "scripts" / "run_molmo_agent_bridge_smoke.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "check_molmo_agent_bridge_result.py"
DEMO_PATH = REPO_ROOT / "examples" / "molmospaces_cleanup_demo.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("run_molmo_agent_bridge_smoke", SMOKE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_demo_module():
    spec = importlib.util.spec_from_file_location("molmospaces_cleanup_demo", DEMO_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_checker_accepts_clean_agent_bridge_and_rule_comparison(tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    demo = _load_demo_module()
    agent_dir = tmp_path / "agent"
    rule_dir = tmp_path / "rule"

    smoke.run_smoke(output_dir=agent_dir, policy="contract_smoke_agent")
    demo.run_demo(output_dir=rule_dir, planner="public_heuristic", task_prompt="帮我整理这个房间")

    subprocess.run(
        [
            sys.executable,
            str(CHECKER_PATH),
            "--expect-policy",
            "contract_smoke_agent",
            "--require-agent-driven",
            "--require-clean",
            "--require-semantic-acceptability",
            "--compare-rule-result",
            str(rule_dir / "run_result.json"),
            str(agent_dir / "run_result.json"),
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def test_checker_accepts_openclaw_minimum_trace(tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    run_result = smoke.run_smoke(output_dir=tmp_path, policy="openclaw_agent")
    assert run_result["policy"] == "openclaw_agent"

    subprocess.run(
        [
            sys.executable,
            str(CHECKER_PATH),
            "--require-agent-driven",
            "--require-openclaw-minimum",
            str(tmp_path / "run_result.json"),
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def test_checker_accepts_visual_agent_bridge_result(tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    smoke.run_smoke(output_dir=tmp_path, policy="contract_smoke_agent")
    _add_visual_bridge_fields(tmp_path / "run_result.json")

    subprocess.run(
        [
            sys.executable,
            str(CHECKER_PATH),
            "--expect-policy",
            "contract_smoke_agent",
            "--expect-backend",
            "molmospaces_subprocess",
            "--expect-robot",
            "rby1m",
            "--require-agent-driven",
            "--require-clean",
            "--require-robot-views",
            "--require-semantic-acceptability",
            str(tmp_path / "run_result.json"),
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def test_checker_rejects_missing_visual_agent_bridge_result(tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    smoke.run_smoke(output_dir=tmp_path, policy="contract_smoke_agent")

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER_PATH),
            "--require-robot-views",
            str(tmp_path / "run_result.json"),
        ],
        cwd=REPO_ROOT,
    )

    assert completed.returncode != 0


def test_checker_rejects_non_agent_result_for_clean_gate(tmp_path: Path) -> None:
    demo = _load_demo_module()
    result = demo.run_demo(output_dir=tmp_path, planner="public_heuristic")
    assert result["cleanup_status"] == "success"
    # Add the current-contract labels but leave agent-driven false to isolate
    # the clean-agent gate behavior without depending on legacy schema shape.
    path = tmp_path / "run_result.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(
        {
            "contract": "current_contract",
            "mcp_server": "molmo_cleanup",
            "adr_0003_satisfied": False,
            "policy": "public_heuristic",
            "agent_driven": False,
            "policy_uses_private_truth": False,
            "planner_uses_private_manifest": False,
            "current_contract_shortcuts": ["global_scene_objects"],
            "agent_bridge": {},
        }
    )
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER_PATH),
            "--require-agent-driven",
            "--require-clean",
            str(path),
        ],
        cwd=REPO_ROOT,
    )

    assert completed.returncode != 0


def _add_visual_bridge_fields(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    robot_views = base / "robot_views"
    robot_views.mkdir()
    report = base / "report.html"
    report_text = report.read_text(encoding="utf-8")
    robot_timeline = (
        '\n<section class="panel robot-timeline"><h2>Robot View Timeline</h2></section>'
    )
    score_marker = '<section class="panel">\n      <h2>Score</h2>'
    if score_marker in report_text:
        report_text = report_text.replace(score_marker, robot_timeline + "\n" + score_marker)
    else:
        report_text += robot_timeline
    report.write_text(report_text, encoding="utf-8")
    actions = [
        ("before", None, None, None),
        ("navigate_to_object mug_01", "mug_01", "sink_01", "target_facing_base_yaw"),
        ("pick mug_01", "mug_01", "sink_01", "target_facing_base_yaw"),
        ("navigate_to_receptacle sink_01", "mug_01", "sink_01", "target_facing_base_yaw"),
        ("place mug_01", "mug_01", "sink_01", "target_facing_base_yaw"),
        ("open_receptacle fridge_01", "apple_01", "fridge_01", "opened_receptacle_access_yaw"),
        ("place_inside apple_01", "apple_01", "fridge_01", "opened_receptacle_access_yaw"),
    ]
    steps = []
    for index, (action, object_id, receptacle_id, theta_source) in enumerate(actions):
        label = f"{index:04d}_{action.split(' ', 1)[0]}"
        views = {}
        for key in ("fpv", "chase", "map", "verify"):
            view_path = robot_views / f"{label}_{key}.png"
            view_path.write_bytes(b"fake png")
            views[key] = str(view_path.relative_to(base))
        focus = {"has_focus": False}
        if object_id is not None:
            focus = {
                "has_focus": True,
                "object_id": object_id,
                "receptacle_id": receptacle_id,
                "receptacle_category": "Fridge" if receptacle_id == "fridge_01" else "",
                "provenance": "public_mujoco_state_report_aid",
                "object_position": [1.45, 2.0, 1.05],
                "object_location_relation": "held"
                if action.startswith(("navigate_to_receptacle ", "open_receptacle "))
                else "at",
                "fpv_visibility": {
                    "status": "ok",
                    "boxes": [{"label": object_id}],
                    "object_pixels": 300,
                    "receptacle_pixels": 120,
                },
                "visibility": {
                    "status": "ok",
                    "boxes": [{"label": object_id}],
                    "object_pixels": 150,
                    "receptacle_pixels": 120,
                },
            }
        steps.append(
            {
                "label": label,
                "action": action,
                "semantic_phase": action.split(" ", 1)[0] if object_id is not None else None,
                "room_outline_count": 1,
                "robot_pose": {
                    "x": 1.0,
                    "y": 2.0,
                    "theta": 0.0,
                    "head_pitch": -0.25,
                    "theta_source": theta_source,
                    "head_pitch_source": "target_framing_head_pitch",
                    "same_room_as_target": True,
                },
                "focus": focus,
                "views": views,
            }
        )
    data.update(
        {
            "backend": "molmospaces_subprocess",
            "view_variant": "molmospaces-rby1m-fpv-map-chase-verify",
            "robot": {
                "robot_included": True,
                "robot_model_stats": {"nbody": 3},
                "robot_camera_names": ["robot_0/head_camera"],
            },
            "robot_name": "rby1m",
            "robot_view_steps": steps,
        }
    )
    data["artifacts"]["robot_views"] = str(robot_views)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
