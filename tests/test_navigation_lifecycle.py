from __future__ import annotations

import json

from roboclaws.core.navigation_lifecycle import NavigationRunLifecycle


def test_navigation_lifecycle_prepares_paths_and_mcp_url(tmp_path) -> None:
    lifecycle = NavigationRunLifecycle(
        scene="FloorPlan201",
        output_dir=tmp_path / "run",
        host="127.0.0.1",
        port=18788,
        agent_id=0,
    )

    lifecycle.prepare_output_dir()

    assert lifecycle.output_dir.exists()
    assert lifecycle.snapshots_dir == tmp_path / "run" / "snapshots" / "agent-0"
    assert lifecycle.mcp_url == "http://127.0.0.1:18788/mcp"


def test_navigation_lifecycle_writes_direct_run_result(tmp_path) -> None:
    lifecycle = NavigationRunLifecycle(
        scene="FloorPlan201",
        output_dir=tmp_path / "run",
        host="127.0.0.1",
        port=18788,
        agent_id=0,
    )
    lifecycle.prepare_output_dir()

    payload = lifecycle.write_direct_run_result(
        terminated_by="agent_done",
        snapshot_metrics={"observed_once": True},
        error=None,
    )

    saved = json.loads((tmp_path / "run" / "run_result.json").read_text(encoding="utf-8"))
    assert saved == payload
    assert payload["scene"] == "FloorPlan201"
    assert payload["mcp_url"] == "http://127.0.0.1:18788/mcp"
    assert payload["snapshots_dir"] == str(tmp_path / "run" / "snapshots" / "agent-0")
    assert payload["sim_server_metrics"] == {"observed_once": True}
