# ruff: noqa: I001

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "examples" / "mcp"))

from coding_agent_nav_server import (  # noqa: E402
    _client_setup_commands,
    _mcp_url,
    _parse_args,
    _snapshots_dir,
    run_coding_agent_nav_server,
)


def _make_fake_mcp_server() -> MagicMock:
    fake = MagicMock(
        spec_set=[
            "done_event",
            "host",
            "port",
            "run_in_thread",
            "close",
            "snapshot_metrics",
            "write_runtime_event",
        ]
    )
    fake.done_event = threading.Event()
    fake.host = "127.0.0.1"
    fake.port = 18788
    fake.run_in_thread.side_effect = fake.done_event.set
    fake.close = MagicMock()
    fake.write_runtime_event = MagicMock()
    fake.snapshot_metrics.return_value = {
        "observed_once": True,
        "moves_since_observe": 0,
        "done_event_set": True,
        "tool_event_counts": {"observe:request": 1, "done:request": 1},
    }
    return fake


def test_parse_args_defaults() -> None:
    args = _parse_args([])
    assert args.scene == "FloorPlan201"
    assert args.host == "127.0.0.1"
    assert args.port == 18788
    assert args.output_dir is None


def test_client_setup_commands_match_current_http_mcp_cli_syntax() -> None:
    url = "http://127.0.0.1:18788/mcp"
    assert _mcp_url("127.0.0.1", 18788) == url
    assert _client_setup_commands(url) == {
        "Codex": "codex mcp add roboclaws --url http://127.0.0.1:18788/mcp",
        "Claude Code": ("claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp"),
    }


def test_snapshot_layout_matches_photo_task_checker(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    assert _snapshots_dir(run_dir) == run_dir / "snapshots" / "agent-0"


def test_run_direct_server_starts_mcp_and_writes_result(
    tmp_path: Path,
    capsys,
) -> None:
    output_dir = tmp_path / "coding-agent-nav"
    fake_server = _make_fake_mcp_server()

    with (
        patch("coding_agent_nav_server.MultiAgentEngine") as engine_cls,
        patch(
            "coding_agent_nav_server.make_roboclaws_mcp",
            return_value=fake_server,
        ) as mcp_factory,
    ):
        result = run_coding_agent_nav_server(
            scene="FloorPlan201",
            output_dir=output_dir,
            poll_interval_s=0,
            print_setup=True,
        )

    captured = capsys.readouterr().out
    assert "codex mcp add roboclaws --url http://127.0.0.1:18788/mcp" in captured
    assert "claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp" in captured
    engine_cls.assert_called_once_with(scene="FloorPlan201", agent_count=1)
    _, mcp_kwargs = mcp_factory.call_args
    assert mcp_kwargs["agent_id"] == 0
    assert mcp_kwargs["run_dir"] == output_dir
    assert mcp_kwargs["host"] == "127.0.0.1"
    assert mcp_kwargs["port"] == 18788
    assert mcp_kwargs["snapshots_dir"] == output_dir / "snapshots" / "agent-0"
    fake_server.run_in_thread.assert_called_once()
    fake_server.close.assert_called_once()
    engine_cls.return_value.close.assert_called_once()

    run_result = json.loads((output_dir / "run_result.json").read_text(encoding="utf-8"))
    assert result == run_result
    assert run_result["terminated_by"] == "agent_done"
    assert run_result["mcp_url"] == "http://127.0.0.1:18788/mcp"
    assert run_result["snapshots_dir"] == str(output_dir / "snapshots" / "agent-0")
    assert run_result["sim_server_metrics"]["tool_event_counts"]["observe:request"] == 1

    runtime_events = [call.args[0] for call in fake_server.write_runtime_event.call_args_list]
    assert "direct_server_started" in runtime_events
    assert "direct_server_finished" in runtime_events
