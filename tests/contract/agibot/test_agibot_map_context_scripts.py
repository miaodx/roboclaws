from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CAPTURE_PATH = REPO_ROOT / "scripts" / "agibot" / "capture_map_context_views.py"
GENERATOR_PATH = REPO_ROOT / "scripts" / "agibot" / "generate_metric_map_from_context.py"
VERIFY_PATH = REPO_ROOT / "scripts" / "agibot" / "verify_waypoints_with_pnc.py"
SDK_RUNNER_PATH = REPO_ROOT / "vendors" / "agibot_sdk" / "tools" / "run_agibot_cleanup_backend.py"
RAW_FPV_CHECK_PATH = REPO_ROOT / "vendors" / "agibot_sdk" / "tools" / "check_raw_fpv_status.py"
COMPLETED_CONTEXT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "agibot_map_context.completed.json"


def _require_agibot_sdk_runner() -> None:
    if not SDK_RUNNER_PATH.is_file():
        pytest.skip("Agibot SDK vendor runner is unavailable in this checkout")


def _require_raw_fpv_checker() -> None:
    if not RAW_FPV_CHECK_PATH.is_file():
        pytest.skip("Agibot raw-FPV checker is unavailable in this checkout")


def test_generate_metric_map_from_completed_agibot_context(tmp_path: Path) -> None:
    generator = _load_module(GENERATOR_PATH, "generate_metric_map_from_context")
    context_path = tmp_path / "agibot_map_context.completed.json"
    output_dir = tmp_path / "generated"
    context_path.write_text(json.dumps(_completed_context()), encoding="utf-8")

    generator.main([str(context_path), "--output-dir", str(output_dir)])

    metric_map = json.loads((output_dir / "metric_map.json").read_text(encoding="utf-8"))
    fixture_hints = json.loads((output_dir / "fixture_hints.json").read_text(encoding="utf-8"))
    agent_view = json.loads((output_dir / "agent_view.json").read_text(encoding="utf-8"))

    assert metric_map["schema"] == "real_robot_map_bundle_v1"
    assert "map_source" not in metric_map
    assert "map_bundle" not in metric_map
    assert metric_map["occupancy_grid_artifact"] is None
    assert metric_map["map_preview_artifact"] == "semantic_preview.png"
    assert metric_map["inspection_waypoints"][0]["waypoint_source"] == "operator_recorded_pose"
    assert metric_map["inspection_waypoints"][0]["reachability_status"] == "verified"
    assert "verification" not in metric_map["inspection_waypoints"][0]
    assert metric_map["robot_pose"]["pose_source"] == "operator_recorded_pose"
    assert fixture_hints["schema"] == "static_fixture_semantic_map_v1"
    assert fixture_hints["fixture_hint_mode"] == "operator_authored_semantic_map"
    assert fixture_hints["contains_runtime_observations"] is False
    assert "agibot_gdk" not in json.dumps(agent_view)
    assert (output_dir / "semantic_preview.png").is_file()


def test_generate_metric_map_from_minimal_agibot_context(tmp_path: Path) -> None:
    generator = _load_module(GENERATOR_PATH, "generate_metric_map_from_minimal_context")
    context_path = tmp_path / "agibot_map_context.minimal.json"
    output_dir = tmp_path / "generated"
    context_path.write_text(json.dumps(_minimal_context()), encoding="utf-8")

    generator.main([str(context_path), "--output-dir", str(output_dir)])

    metric_map = json.loads((output_dir / "metric_map.json").read_text(encoding="utf-8"))
    fixture_hints = json.loads((output_dir / "fixture_hints.json").read_text(encoding="utf-8"))
    agent_view = json.loads((output_dir / "agent_view.json").read_text(encoding="utf-8"))
    first_waypoint = metric_map["inspection_waypoints"][0]
    payload_text = json.dumps(agent_view).lower()

    assert metric_map["schema"] == "real_robot_map_bundle_v1"
    assert metric_map["mode"] == "minimal"
    assert metric_map["rooms"] == []
    assert metric_map["minimal_map"]["source_rooms_hidden"] is True
    assert metric_map["minimal_map"]["source_fixtures_hidden"] is True
    assert metric_map["minimal_map"]["generated_candidate_count"] == 3
    assert metric_map["safety_bounds"]["polygon"]
    assert len(metric_map["inspection_waypoints"]) == 3
    assert len(metric_map["generated_exploration_candidates"]) == 3
    assert first_waypoint["waypoint_id"] == "generated_exploration_001"
    assert first_waypoint["waypoint_source"] == "generated_exploration_candidate"
    assert first_waypoint["purpose"] == "minimal_map_exploration"
    assert first_waypoint["reachability_status"] == "verified"
    assert first_waypoint["candidate_provenance"]["source"] == "public_free_space_sample"
    assert "verification" not in first_waypoint
    assert fixture_hints["mode"] == "minimal"
    assert fixture_hints["fixture_hint_mode"] == "minimal_map_no_fixtures"
    assert fixture_hints["rooms"] == []
    assert "agibot_gdk" not in payload_text
    assert "map_source" not in payload_text
    assert "verification" not in payload_text
    assert "pnc" not in payload_text
    assert (output_dir / "semantic_preview.png").is_file()


def test_reachability_unverified_does_not_pass_as_verified(tmp_path: Path) -> None:
    generator = _load_module(GENERATOR_PATH, "generate_metric_map_from_context_unverified")
    context = _completed_context()
    context["inspection_waypoints"][0]["reachability_status"] = "unverified"
    context["inspection_waypoints"][0].pop("verification")
    context_path = tmp_path / "agibot_map_context.completed.json"
    output_dir = tmp_path / "generated"
    context_path.write_text(json.dumps(context), encoding="utf-8")

    generator.main([str(context_path), "--output-dir", str(output_dir)])

    metric_map = json.loads((output_dir / "metric_map.json").read_text(encoding="utf-8"))
    assert metric_map["inspection_waypoints"][0]["reachability_status"] == "unverified"


def test_generate_metric_map_rejects_todo_context(tmp_path: Path) -> None:
    generator = _load_module(GENERATOR_PATH, "generate_metric_map_from_context_todo")
    context = _completed_context()
    context["rooms"][0]["room_label"] = "TODO: room label"

    errors = generator.validate_context(context)

    assert "rooms[0].room_label is required" in errors


def test_capture_context_upsert_records_multiple_waypoints(tmp_path: Path) -> None:
    capture = _load_module(CAPTURE_PATH, "capture_map_context_views")
    context_path = tmp_path / "agibot_map_context.todo.json"
    context = {
        "schema": "agibot_gdk_map_context_authoring_v1",
        "map_source": {"type": "agibot_gdk_map_context", "map_id": 3, "map_name": "office"},
        "rooms": [],
        "fixtures": [],
        "inspection_waypoints": [],
        "waypoint_captures": [],
    }
    context_path.write_text(json.dumps(context), encoding="utf-8")

    loaded = json.loads(context_path.read_text(encoding="utf-8"))
    capture._upsert_capture_into_context(
        loaded,
        manifest=_capture_manifest("wp_sofa_front", x=1.0, y=2.0),
        manifest_path=tmp_path / "captures" / "wp_sofa_front" / "capture_manifest.json",
        context_dir=tmp_path,
        room_id="living_room",
        room_label="Living room",
        fixture_id="sofa",
        fixture_label="Sofa",
        fixture_category="sofa",
        waypoint_id="wp_sofa_front",
        waypoint_label="Sofa front",
    )
    capture._upsert_capture_into_context(
        loaded,
        manifest=_capture_manifest("wp_table_front", x=2.0, y=3.0),
        manifest_path=tmp_path / "captures" / "wp_table_front" / "capture_manifest.json",
        context_dir=tmp_path,
        room_id="living_room",
        room_label="Living room",
        fixture_id="table",
        fixture_label="Table",
        fixture_category="table",
        waypoint_id="wp_table_front",
        waypoint_label="Table front",
    )

    assert [item["waypoint_id"] for item in loaded["inspection_waypoints"]] == [
        "wp_sofa_front",
        "wp_table_front",
    ]
    assert {item["fixture_id"] for item in loaded["fixtures"]} == {"sofa", "table"}
    assert len(loaded["rooms"]) == 1
    assert loaded["inspection_waypoints"][0]["capture"]["manifest_path"] == (
        "captures/wp_sofa_front/capture_manifest.json"
    )


def test_verify_helpers_select_map_check_and_record_status() -> None:
    verifier = _load_module(VERIFY_PATH, "verify_waypoints_with_pnc")
    context = _completed_context()
    context["inspection_waypoints"].append(
        {
            "waypoint_id": "wp_table_front",
            "room_id": "living_room",
            "fixture_id": "sofa",
            "label": "Table front",
            "x": 2.0,
            "y": 2.0,
            "yaw": 0.0,
        }
    )

    selected = verifier.select_waypoints(
        context,
        all_waypoints=False,
        waypoint_ids=["wp_table_front"],
    )
    map_check = verifier.compare_current_map(
        context,
        {"id": 3, "name": "office_floor_1", "is_curr_map": True},
    )
    result = {
        "reachability_status": verifier.VERIFIED,
        "navigation_backend": "agibot_gdk",
        "primitive_provenance": "agibot_gdk_normal_navi",
    }
    verifier.record_waypoint_verification(selected[0], result)

    assert len(selected) == 1
    assert map_check["ok"] is True
    assert selected[0]["reachability_status"] == "verified"
    assert selected[0]["verification"]["primitive_provenance"] == "agibot_gdk_normal_navi"


def test_verify_waypoint_timeout_records_cancel_evidence(monkeypatch) -> None:
    verifier = _load_module(VERIFY_PATH, "verify_waypoints_with_pnc_timeout")
    waypoint = _completed_context()["inspection_waypoints"][0]
    pnc = _TimeoutPnc()

    monkeypatch.setattr(verifier.time, "sleep", lambda seconds: None)

    result = verifier.verify_waypoint(
        gdk=_FakeAgibotGDK(),
        pnc=pnc,
        waypoint=waypoint,
        timeout_s=0.0,
        poll_s=0.0,
        map_check={"ok": True},
    )

    assert result["reachability_status"] == "timeout"
    assert result["navigation_backend"] == "agibot_gdk"
    assert result["cancel_attempted"] is True
    assert result["cancel_task_id"] == 42
    assert result["cancel_requested"] is True
    assert result["cancel_error"] == ""
    assert result["final_task_before_cancel"]["state_name"] == "running"
    assert result["final_task_after_cancel"]["state_name"] == "canceled"
    assert result["final_task"]["state_name"] == "canceled"
    assert pnc.cancel_task_calls == [42]


def test_sdk_runner_writes_three_reviewable_dry_run_reports(tmp_path: Path) -> None:
    _require_agibot_sdk_runner()
    context_path = tmp_path / "agibot_map_context.completed.json"
    context_path.write_text(json.dumps(_completed_context()), encoding="utf-8")
    root = tmp_path / "sdk-runner"
    agent_view_dir = root / "01-agent-view"
    observe_dir = root / "02-observe"
    navigate_dir = root / "03-navigate"

    _run_sdk(
        "agent-view",
        "--context-json",
        str(context_path),
        "--output-dir",
        str(agent_view_dir),
    )
    _run_sdk(
        "observe",
        "--agent-view-json",
        str(agent_view_dir / "agent_view.json"),
        "--output-dir",
        str(observe_dir),
    )
    _run_sdk(
        "navigate-waypoint",
        "--agent-view-json",
        str(agent_view_dir / "agent_view.json"),
        "--output-dir",
        str(navigate_dir),
        "--waypoint-id",
        "wp_sofa_front",
    )

    agent_view = json.loads((agent_view_dir / "agent_view.json").read_text(encoding="utf-8"))
    navigate_result = json.loads((navigate_dir / "run_result.json").read_text(encoding="utf-8"))

    for report in (
        agent_view_dir / "report.html",
        observe_dir / "report.html",
        navigate_dir / "report.html",
    ):
        text = report.read_text(encoding="utf-8")
        assert "AgiBot SDK Runner Report" in text
        assert len(text) > 1000

    assert "agibot" not in json.dumps(agent_view).lower()
    assert "map_source" not in json.dumps(agent_view)
    assert "verification" not in json.dumps(agent_view)
    assert navigate_result["tool_response"]["navigation_status"] == "dry_run_not_executed"
    assert navigate_result["tool_response"]["primitive_provenance"] == "blocked_capability"


def test_sdk_runner_exports_minimal_context_generated_candidates(tmp_path: Path) -> None:
    _require_agibot_sdk_runner()
    context_path = tmp_path / "agibot_map_context.minimal.json"
    context_path.write_text(json.dumps(_minimal_context()), encoding="utf-8")
    root = tmp_path / "sdk-runner"
    agent_view_dir = root / "01-agent-view"
    navigate_dir = root / "03-navigate"

    _run_sdk(
        "agent-view",
        "--context-json",
        str(context_path),
        "--output-dir",
        str(agent_view_dir),
    )
    _run_sdk(
        "navigate-waypoint",
        "--agent-view-json",
        str(agent_view_dir / "agent_view.json"),
        "--output-dir",
        str(navigate_dir),
        "--waypoint-id",
        "generated_exploration_001",
    )

    agent_view = json.loads((agent_view_dir / "agent_view.json").read_text(encoding="utf-8"))
    run_result = json.loads((agent_view_dir / "run_result.json").read_text(encoding="utf-8"))
    navigate_result = json.loads((navigate_dir / "run_result.json").read_text(encoding="utf-8"))
    payload_text = json.dumps(agent_view).lower()
    waypoint = agent_view["metric_map"]["inspection_waypoints"][0]

    assert agent_view["metric_map"]["mode"] == "minimal"
    assert agent_view["metric_map"]["rooms"] == []
    assert waypoint["waypoint_source"] == "generated_exploration_candidate"
    assert waypoint["reachability_status"] == "verified"
    assert agent_view["fixture_hints"]["fixture_hint_mode"] == "minimal_map_no_fixtures"
    assert run_result["summary"]["generated_exploration_candidates"] == 3
    assert run_result["privacy_check"]["ok"] is True
    assert "agibot_gdk" not in payload_text
    assert "map_source" not in payload_text
    assert "verification" not in payload_text
    assert navigate_result["tool_response"]["navigation_status"] == "dry_run_not_executed"
    assert navigate_result["tool_response"]["waypoint_id"] == "generated_exploration_001"


def test_sdk_runner_blocks_unverified_waypoint_before_dry_run_navigation(tmp_path: Path) -> None:
    _require_agibot_sdk_runner()
    context = _completed_context()
    context["inspection_waypoints"][0]["reachability_status"] = "unverified"
    context["inspection_waypoints"][0].pop("verification")
    context_path = tmp_path / "agibot_map_context.completed.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")
    root = tmp_path / "sdk-runner"
    agent_view_dir = root / "01-agent-view"
    navigate_dir = root / "03-navigate"

    _run_sdk(
        "agent-view",
        "--context-json",
        str(context_path),
        "--output-dir",
        str(agent_view_dir),
    )
    proc = _run_sdk_allowing_failure(
        "navigate-waypoint",
        "--agent-view-json",
        str(agent_view_dir / "agent_view.json"),
        "--output-dir",
        str(navigate_dir),
        "--waypoint-id",
        "wp_sofa_front",
    )
    navigate_result = json.loads((navigate_dir / "run_result.json").read_text(encoding="utf-8"))

    assert proc.returncode == 2
    assert navigate_result["status"] == "blocked_capability"
    assert navigate_result["tool_response"]["failure_type"] == "waypoint_not_pnc_verified"
    assert navigate_result["tool_response"]["navigation_status"] == "blocked"


def test_sdk_runner_successful_mocked_gdk_navigation_records_normal_navi(
    monkeypatch, tmp_path: Path
) -> None:
    _require_agibot_sdk_runner()
    runner = _load_module(SDK_RUNNER_PATH, "run_agibot_cleanup_backend_mocked_success")
    waypoint = runner._metric_map_from_context(_completed_context(), map_artifacts={})[
        "inspection_waypoints"
    ][0]
    fake_gdk = _FakeAgibotGDK()

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(runner, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(runner, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)

    response = runner._execute_waypoint_navigation(
        waypoint=waypoint,
        context_json=None,
        output_dir=tmp_path,
        robot_host="127.0.0.1",
        init_wait_s=0.0,
        timeout_s=1.0,
        poll_s=0.0,
        arrival_observe=False,
        image_timeout_ms=1.0,
    )

    assert response["ok"] is True
    assert response["navigation_status"] == "succeeded"
    assert response["navigation_backend"] == "agibot_gdk"
    assert response["primitive_provenance"] == "agibot_gdk_normal_navi"
    assert response["pose_source"] == "agibot_gdk_pnc_arrival"
    assert response["navi_request"]["sent"] is True
    assert response["navi_request"]["not_sent"] is False
    assert fake_gdk.pnc.normal_navi_calls == 1
    assert fake_gdk.gdk_release_calls == 1


def test_sdk_runner_camera_observation_uses_vendor_camera_then_sleep_order(
    monkeypatch, tmp_path: Path
) -> None:
    _require_agibot_sdk_runner()
    runner = _load_module(SDK_RUNNER_PATH, "run_agibot_cleanup_backend_mocked_camera_order")
    events: list[str] = []
    fake_gdk = _FakeAgibotGDK(camera_factory=_FakeCameraFactory(events=events))

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(runner, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(runner, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: events.append(f"sleep:{seconds}"))

    response = runner._execute_camera_observation(
        output_dir=tmp_path,
        camera_name="head_color",
        robot_host="127.0.0.1",
        init_wait_s=3.0,
        image_timeout_ms=1000.0,
    )

    assert response["ok"] is True
    assert response["primitive_provenance"] == "agibot_gdk_head_color_camera"
    assert response["camera_artifact"] == "head_color.jpg"
    assert events == ["camera_created", "sleep:3.0", "get_latest_image", "close_camera"]
    assert fake_gdk.gdk_release_calls == 1
    assert (tmp_path / "head_color.jpg").read_bytes().startswith(b"\xff\xd8")


def test_sdk_runner_camera_observation_fails_loudly_on_missing_numpy(
    monkeypatch, tmp_path: Path
) -> None:
    _require_agibot_sdk_runner()
    runner = _load_module(SDK_RUNNER_PATH, "run_agibot_cleanup_backend_mocked_camera_numpy")
    fake_gdk = _FakeAgibotGDK(camera_factory=_FakeCameraFactory(missing_numpy=True))

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(runner, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(runner, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)

    with pytest.raises(ModuleNotFoundError, match="numpy"):
        runner._execute_camera_observation(
            output_dir=tmp_path,
            camera_name="head_color",
            robot_host="127.0.0.1",
            init_wait_s=0.0,
            image_timeout_ms=1000.0,
        )

    assert fake_gdk.gdk_release_calls == 1


def test_raw_fpv_checker_records_head_color_status_and_no_motion(
    monkeypatch, tmp_path: Path
) -> None:
    _require_raw_fpv_checker()
    checker = _load_module(RAW_FPV_CHECK_PATH, "check_raw_fpv_status_mocked_success")
    fake_gdk = _FakeAgibotGDK(camera_factory=_FakeCameraFactory())

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(checker, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(checker, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(checker.time, "sleep", lambda seconds: None)

    rc = checker.main_from_args(
        [
            "--robot-host",
            "127.0.0.1",
            "--output-dir",
            str(tmp_path),
            "--cameras",
            "head_color",
        ]
    )

    status = json.loads((tmp_path / "raw_fpv_status.json").read_text(encoding="utf-8"))
    head = status["checks"][0]
    assert rc == 0
    assert status["raw_fpv_status"] == "head_color_available"
    assert status["read_only"] is True
    assert status["navigation_submission"] is False
    assert status["motion_or_write_calls_used"] == []
    assert head["ok"] is True
    assert head["camera"] == "head_color"
    assert head["shape"] == [640, 400]
    assert head["fps"] == 30.0
    assert (tmp_path / "head_color_latest.jpg").read_bytes().startswith(b"\xff\xd8")
    assert fake_gdk.gdk_release_calls == 1


def test_raw_fpv_checker_fails_loudly_on_missing_numpy(monkeypatch, tmp_path: Path) -> None:
    _require_raw_fpv_checker()
    checker = _load_module(RAW_FPV_CHECK_PATH, "check_raw_fpv_status_mocked_numpy")
    fake_gdk = _FakeAgibotGDK(camera_factory=_FakeCameraFactory(missing_numpy=True))

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(checker, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(checker, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(checker.time, "sleep", lambda seconds: None)

    with pytest.raises(ModuleNotFoundError, match="numpy"):
        checker.main_from_args(
            [
                "--robot-host",
                "127.0.0.1",
                "--output-dir",
                str(tmp_path),
                "--cameras",
                "head_color",
            ]
        )

    assert fake_gdk.gdk_release_calls == 1


def test_sdk_runner_timeout_cancels_gdk_navigation_and_records_evidence(
    monkeypatch, tmp_path: Path
) -> None:
    _require_agibot_sdk_runner()
    runner = _load_module(SDK_RUNNER_PATH, "run_agibot_cleanup_backend_mocked_timeout")
    waypoint = runner._metric_map_from_context(_completed_context(), map_artifacts={})[
        "inspection_waypoints"
    ][0]
    fake_gdk = _FakeAgibotGDK(pnc=_TimeoutPnc())

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(runner, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(runner, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)

    response = runner._execute_waypoint_navigation(
        waypoint=waypoint,
        context_json=None,
        output_dir=tmp_path,
        robot_host="127.0.0.1",
        init_wait_s=0.0,
        timeout_s=0.0,
        poll_s=0.0,
        arrival_observe=False,
        image_timeout_ms=1.0,
    )

    assert response["ok"] is False
    assert response["status"] == "blocked_capability"
    assert response["failure_type"] == "timeout"
    assert response["navigation_status"] == "blocked"
    assert response["final_task"]["state_name"] == "running"
    assert response["final_task_after_cancel"]["state_name"] == "canceled"
    assert response["cancel_attempted"] is True
    assert response["cancel_task_id"] == 42
    assert response["cancel_requested"] is True
    assert response["cancel_error"] == ""
    assert fake_gdk.pnc.normal_navi_calls == 1
    assert fake_gdk.pnc.cancel_task_calls == [42]
    assert fake_gdk.gdk_release_calls == 1


def test_sdk_runner_execute_blocks_current_map_mismatch_before_normal_navi(
    monkeypatch, tmp_path: Path
) -> None:
    _require_agibot_sdk_runner()
    runner = _load_module(SDK_RUNNER_PATH, "run_agibot_cleanup_backend_mocked_map_mismatch")
    waypoint = runner._metric_map_from_context(_completed_context(), map_artifacts={})[
        "inspection_waypoints"
    ][0]
    context_path = tmp_path / "agibot_map_context.completed.json"
    context_path.write_text(json.dumps(_completed_context()), encoding="utf-8")
    fake_gdk = _FakeAgibotGDK(map_item=SimpleNamespace(id=99, name="wrong_map", is_curr_map=True))

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(runner, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(runner, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)

    response = runner._execute_waypoint_navigation(
        waypoint=waypoint,
        context_json=context_path,
        output_dir=tmp_path,
        robot_host="127.0.0.1",
        init_wait_s=0.0,
        timeout_s=1.0,
        poll_s=0.0,
        arrival_observe=False,
        image_timeout_ms=1.0,
    )

    assert response["ok"] is False
    assert response["status"] == "blocked_capability"
    assert response["failure_type"] == "map_mismatch"
    assert response["navigation_status"] == "blocked"
    assert response["map_check"]["ok"] is False
    assert response["map_check"]["expected_map_name"] == "office_floor_1"
    assert response["map_check"]["current_map_name"] == "wrong_map"
    assert fake_gdk.map_calls == 1
    assert fake_gdk.pnc.normal_navi_calls == 0
    assert fake_gdk.gdk_release_calls == 1


def test_sdk_runner_execute_blocks_missing_localization_before_normal_navi(
    monkeypatch, tmp_path: Path
) -> None:
    _require_agibot_sdk_runner()
    runner = _load_module(SDK_RUNNER_PATH, "run_agibot_cleanup_backend_mocked_localization_block")
    waypoint = runner._metric_map_from_context(_completed_context(), map_artifacts={})[
        "inspection_waypoints"
    ][0]
    fake_gdk = _FakeAgibotGDK(slam=_FakeSlam(odom=SimpleNamespace()))

    monkeypatch.setitem(sys.modules, "agibot_gdk", fake_gdk)
    monkeypatch.setattr(runner, "require_robot_discovery", lambda robot_host: None)
    monkeypatch.setattr(runner, "ensure_runtime", lambda robot_host, script_path: None)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)

    response = runner._execute_waypoint_navigation(
        waypoint=waypoint,
        context_json=None,
        output_dir=tmp_path,
        robot_host="127.0.0.1",
        init_wait_s=0.0,
        timeout_s=1.0,
        poll_s=0.0,
        arrival_observe=False,
        image_timeout_ms=1.0,
    )

    assert response["ok"] is False
    assert response["status"] == "blocked_capability"
    assert response["failure_type"] == "gdk_localization_not_ready"
    assert response["navigation_status"] == "blocked"
    assert response["localization_check"]["report_present"] is False
    assert response["localization_check"]["pad_relocalization_required_when_not_ok"] is True
    assert "Relocalize on the G02 Pad" in response["backend_error_summary"]
    assert fake_gdk.pnc.normal_navi_calls == 0
    assert fake_gdk.gdk_release_calls == 1


def _completed_context() -> dict:
    return json.loads(COMPLETED_CONTEXT_FIXTURE.read_text(encoding="utf-8"))


def _minimal_context() -> dict:
    return {
        "schema": "agibot_gdk_map_context_authoring_v1",
        "environment_id": "agibot-minimal-office",
        "map_version": "minimal-navigation-map-v1",
        "frame_id": "map",
        "map_source": {
            "type": "agibot_gdk_map_context",
            "map_id": 7,
            "map_name": "minimal_office",
            "is_curr_map": True,
        },
        "robot_pose": {
            "pose_source": "agibot_gdk_slam_get_curr_pose",
            "x": 0.0,
            "y": 0.0,
            "yaw": 0.0,
        },
        "safety_bounds": {
            "frame_id": "map",
            "polygon": [
                {"x": -1.0, "y": -1.0},
                {"x": 3.0, "y": -1.0},
                {"x": 3.0, "y": 3.0},
                {"x": -1.0, "y": 3.0},
            ],
            "max_linear_speed_mps": 0.25,
        },
        "free_space_samples": [
            {"x": 0.5, "y": 0.0, "yaw": 0.0, "reachability_status": "verified"},
            {"x": 1.5, "y": 0.8, "yaw": 1.57, "reachability_status": "verified"},
            {"x": 2.2, "y": 2.0, "yaw": 3.14, "reachability_status": "verified"},
        ],
        "rooms": [],
        "fixtures": [],
        "inspection_waypoints": [],
        "driveable_ways": [],
    }


def _capture_manifest(waypoint_id: str, *, x: float, y: float) -> dict:
    return {
        "schema": "agibot_gdk_map_context_capture_v1",
        "captured_at": "2026-05-19T00:00:00Z",
        "waypoint_id": waypoint_id,
        "map_source": {
            "type": "agibot_gdk_map_context",
            "map_id": 3,
            "map_name": "office_floor_1",
            "is_curr_map": True,
        },
        "robot_pose": {
            "frame_id": "map",
            "x": x,
            "y": y,
            "yaw": 0.1,
            "pose_source": "agibot_gdk_slam_get_curr_pose",
        },
        "camera_results": [
            {
                "camera_name": "head_color",
                "ok": True,
                "image_path": "head_color.jpg",
            }
        ],
    }


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class _FakeTask:
    def __init__(self, state: int, *, task_id: int = 1, message: str = "") -> None:
        self.id = task_id
        self.state = state
        self.type = "normal_navi"
        self.message = message


class _FakePnc:
    def __init__(self) -> None:
        self._tasks = [_FakeTask(0, message="idle"), _FakeTask(9, message="success")]
        self.normal_navi_calls = 0
        self.last_request: object | None = None

    def get_task_state(self) -> _FakeTask:
        if len(self._tasks) > 1:
            return self._tasks.pop(0)
        return self._tasks[0]

    def normal_navi(self, request: object) -> None:
        self.normal_navi_calls += 1
        self.last_request = request


class _TimeoutPnc:
    def __init__(self) -> None:
        self._canceled = False
        self.normal_navi_calls = 0
        self.cancel_task_calls: list[int] = []
        self.last_request: object | None = None

    def get_task_state(self) -> _FakeTask:
        if self.normal_navi_calls == 0:
            return _FakeTask(0, task_id=42, message="idle")
        if self._canceled:
            return _FakeTask(7, task_id=42, message="canceled")
        return _FakeTask(2, task_id=42, message="running")

    def normal_navi(self, request: object) -> None:
        self.normal_navi_calls += 1
        self.last_request = request

    def cancel_task(self, task_id: int) -> None:
        self.cancel_task_calls.append(task_id)
        self._canceled = True


class _FakeSlam:
    def __init__(self, odom: object | None = None) -> None:
        self.odom = odom or SimpleNamespace(loc_state=1, loc_confidence=100)

    def get_odom_info(self) -> object:
        return self.odom


class _FakeAgibotGDK:
    class GDKRes:
        kSuccess = 0

    class NaviReq:
        def __init__(self) -> None:
            self.target = SimpleNamespace(
                position=SimpleNamespace(x=0.0, y=0.0, z=0.0),
                orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
            )
            self.timestamp_ns = 0

    class CameraType:
        kHeadColor = "kHeadColor"
        kHeadStereoLeft = "kHeadStereoLeft"
        kHeadStereoRight = "kHeadStereoRight"
        kHeadDepth = "kHeadDepth"
        kHandLeftColor = "kHandLeftColor"
        kHandRightColor = "kHandRightColor"

    def __init__(
        self,
        pnc: object | None = None,
        map_item: object | None = None,
        slam: object | None = None,
        camera_factory: object | None = None,
    ) -> None:
        self.pnc = pnc or _FakePnc()
        self.map_item = map_item
        self.slam = slam or _FakeSlam()
        self.camera_factory = camera_factory
        self.map_calls = 0
        self.gdk_release_calls = 0

    def gdk_init(self) -> int:
        return self.GDKRes.kSuccess

    def gdk_release(self) -> None:
        self.gdk_release_calls += 1

    def Pnc(self) -> _FakePnc:
        return self.pnc

    def Map(self) -> object:
        self.map_calls += 1
        return _FakeMap(self.map_item)

    def Slam(self) -> object:
        return self.slam

    def Camera(self) -> object:
        if self.camera_factory is None:
            raise AssertionError("unexpected Camera() call")
        return self.camera_factory()


class _FakeMap:
    def __init__(self, item: object | None) -> None:
        self.item = item

    def get_curr_map(self) -> object | None:
        return self.item


class _FakeCameraFactory:
    def __init__(self, *, missing_numpy: bool = False, events: list[str] | None = None) -> None:
        self.missing_numpy = missing_numpy
        self.events = events if events is not None else []

    def __call__(self) -> object:
        self.events.append("camera_created")
        return _FakeCamera(self.events, missing_numpy=self.missing_numpy)


class _FakeCamera:
    def __init__(self, events: list[str], *, missing_numpy: bool) -> None:
        self.events = events
        self.missing_numpy = missing_numpy

    def get_image_shape(self, camera_type: object) -> tuple[int, int]:
        return (640, 400)

    def get_image_fps(self, camera_type: object) -> float:
        return 30.0

    def get_latest_image(self, camera_type: object, timeout_ms: float) -> object:
        self.events.append("get_latest_image")
        if self.missing_numpy:
            raise ModuleNotFoundError("No module named 'numpy'", name="numpy")
        return SimpleNamespace(
            timestamp_ns=123,
            width=640,
            height=400,
            encoding=SimpleNamespace(name="JPEG"),
            color_format=SimpleNamespace(name="RGB"),
            bit_depth=8,
            data=_FakeImageData(b"\xff\xd8fake-jpeg\xff\xd9"),
        )

    def close_camera(self) -> int:
        self.events.append("close_camera")
        return _FakeAgibotGDK.GDKRes.kSuccess


class _FakeImageData:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.shape = (len(payload),)

    def tobytes(self) -> bytes:
        return self.payload


def _run_sdk(*args: str) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, str(SDK_RUNNER_PATH), *args],
        cwd=SDK_RUNNER_PATH.parent.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc


def _run_sdk_allowing_failure(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SDK_RUNNER_PATH), *args],
        cwd=SDK_RUNNER_PATH.parent.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
