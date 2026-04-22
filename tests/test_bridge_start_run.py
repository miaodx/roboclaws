from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import httpx
import pytest

from roboclaws.openclaw.bridge import (
    OpenClawBridge,
    OpenClawUnavailable,
    TranscriptMessage,
    _SessionStoreCapture,
)


def _mock_response(status_code: int = 200, json_body: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body or {}
    response.text = "" if json_body is None else str(json_body)
    response.content = (
        b"{}" if json_body is None else str(json_body).encode("utf-8")
    )
    return response


def _chat_response(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def test_start_run_happy_path_returns_done() -> None:
    bridge = OpenClawBridge(transcript_mode="terminal-body")
    done_event = threading.Event()
    with (
        patch.object(bridge._client, "post") as mock_post,
        patch("subprocess.run") as mock_run,
        patch.object(bridge, "_recover_session_store_transcript", return_value=None),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_post.return_value = _mock_response(200, _chat_response("navigation complete"))
        result = bridge.start_run(
            agent_id=0,
            prompt="go",
            wall_budget_s=10.0,
            done_event=done_event,
        )

    assert result.terminated_by == "done"
    assert "navigation complete" in result.final_message
    assert result.transcript_capture_mode == "terminal-body"
    assert result.transcript_source == "terminal-body"
    assert len(result.transcript_messages) == 1
    assert result.transcript_messages[0].is_final is True
    assert result.wallclock_s >= 0.0
    bridge.close()


def test_start_run_wall_clock_timeout_returns_wall_clock() -> None:
    bridge = OpenClawBridge(transcript_mode="terminal-body")
    done_event = threading.Event()
    with (
        patch.object(
            bridge._client,
            "post",
            side_effect=httpx.ReadTimeout("timed out"),
        ),
        patch("subprocess.run") as mock_run,
        patch.object(bridge, "_recover_session_store_transcript", return_value=None),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = bridge.start_run(
            agent_id=0,
            prompt="go",
            wall_budget_s=0.5,
            done_event=done_event,
        )

    assert result.terminated_by == "wall_clock"
    assert "wall-clock timeout" in result.final_message
    assert result.transcript_source == "none"
    bridge.close()


def test_start_run_http_5xx_raises_openclaw_unavailable() -> None:
    bridge = OpenClawBridge(transcript_mode="terminal-body")
    done_event = threading.Event()
    response = _mock_response(500, {"error": {"message": "boom"}})
    with (
        patch.object(bridge._client, "post", return_value=response),
        patch("subprocess.run") as mock_run,
        patch.object(bridge, "_recover_session_store_transcript", return_value=None),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with pytest.raises(OpenClawUnavailable, match="boom"):
            bridge.start_run(
                agent_id=0,
                prompt="go",
                wall_budget_s=10.0,
                done_event=done_event,
            )
    bridge.close()


def test_start_run_does_not_mutate_shared_client_timeout() -> None:
    bridge = OpenClawBridge(timeout=180.0, transcript_mode="terminal-body")
    done_event = threading.Event()
    with (
        patch.object(bridge._client, "post") as mock_post,
        patch("subprocess.run") as mock_run,
        patch.object(bridge, "_recover_session_store_transcript", return_value=None),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_post.return_value = _mock_response(200, _chat_response("done"))
        bridge.start_run(
            agent_id=0,
            prompt="go",
            wall_budget_s=600.0,
            done_event=done_event,
        )

    assert bridge._timeout == 180.0
    client_timeout = bridge._client.timeout
    assert getattr(client_timeout, "read", 180.0) == 180.0
    bridge.close()


def test_start_run_wipes_workspace_state_before_post() -> None:
    bridge = OpenClawBridge(transcript_mode="terminal-body")
    done_event = threading.Event()
    call_order: list[str] = []

    def _mock_subprocess(*args, **kwargs):
        call_order.append("docker_exec")
        return MagicMock(returncode=0, stdout="", stderr="")

    def _mock_post(*args, **kwargs):
        call_order.append("post")
        return _mock_response(200, _chat_response("ok"))

    with (
        patch("subprocess.run", side_effect=_mock_subprocess) as mock_run,
        patch.object(bridge._client, "post", side_effect=_mock_post),
        patch.object(bridge, "_session_store_ids", return_value=set()),
        patch.object(bridge, "_recover_session_store_transcript", return_value=None),
    ):
        bridge.start_run(
            agent_id=2,
            prompt="go",
            wall_budget_s=10.0,
            done_event=done_event,
        )

    assert call_order[0] == "docker_exec"
    assert call_order[-1] == "post"
    docker_cmd = mock_run.call_args.args[0]
    joined = " ".join(str(part) for part in docker_cmd)
    assert "docker" in docker_cmd
    assert "exec" in docker_cmd
    assert "openclaw-gateway" in docker_cmd
    assert "/home/node/.openclaw/workspaces/agent-2/state/" in joined
    bridge.close()


def test_start_run_streaming_happy_path_collects_transcript() -> None:
    bridge = OpenClawBridge(transcript_mode="stream")
    done_event = threading.Event()
    stream_response = MagicMock()
    stream_response.status_code = 200
    stream_response.iter_lines.return_value = [
        'data: {"choices":[{"delta":{"role":"assistant"}}]}',
        'data: {"choices":[{"delta":{"content":"hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        "data: [DONE]",
    ]
    stream_ctx = MagicMock()
    stream_ctx.__enter__.return_value = stream_response
    stream_ctx.__exit__.return_value = None

    with (
        patch.object(bridge._client, "stream", return_value=stream_ctx),
        patch("subprocess.run") as mock_run,
        patch.object(bridge, "_recover_session_store_transcript", return_value=None),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = bridge.start_run(
            agent_id=0,
            prompt="go",
            wall_budget_s=10.0,
            done_event=done_event,
        )

    assert result.terminated_by == "done"
    assert result.transcript_capture_mode == "stream"
    assert result.transcript_source == "stream"
    assert result.final_message == "hello world"
    assert [message.content for message in result.transcript_messages] == ["hello", " world"]
    bridge.close()


def test_start_run_stream_timeout_preserves_partial_transcript() -> None:
    bridge = OpenClawBridge(transcript_mode="stream")
    done_event = threading.Event()
    stream_response = MagicMock()
    stream_response.status_code = 200

    def _iter_lines():
        yield 'data: {"choices":[{"delta":{"content":"partial"}}]}'
        raise httpx.ReadTimeout("timed out")

    stream_response.iter_lines.side_effect = _iter_lines
    stream_ctx = MagicMock()
    stream_ctx.__enter__.return_value = stream_response
    stream_ctx.__exit__.return_value = None

    with (
        patch.object(bridge._client, "stream", return_value=stream_ctx),
        patch("subprocess.run") as mock_run,
        patch.object(bridge, "_recover_session_store_transcript", return_value=None),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = bridge.start_run(
            agent_id=0,
            prompt="go",
            wall_budget_s=10.0,
            done_event=done_event,
        )

    assert result.terminated_by == "wall_clock"
    assert result.transcript_source == "stream"
    assert [message.content for message in result.transcript_messages] == ["partial"]
    assert "wall-clock timeout" in result.final_message
    bridge.close()


def test_start_run_timeout_uses_session_store_transcript_fallback() -> None:
    bridge = OpenClawBridge(transcript_mode="terminal-body")
    done_event = threading.Event()
    session_store_capture = _SessionStoreCapture(
        session_id="new-session",
        session_file="/home/node/.openclaw/agents/agent-0/sessions/new-session.jsonl",
        transcript_messages=[
            TranscriptMessage(
                wallclock_s=18.5,
                source="session-store",
                content="Checking the room before moving.",
                message_index=0,
                chunk_index=0,
            )
        ],
    )

    with (
        patch.object(bridge._client, "post", side_effect=httpx.ReadTimeout("timed out")),
        patch("subprocess.run") as mock_run,
        patch.object(bridge, "_recover_session_store_transcript", return_value=session_store_capture),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = bridge.start_run(
            agent_id=0,
            prompt="go",
            wall_budget_s=10.0,
            done_event=done_event,
        )

    assert result.terminated_by == "wall_clock"
    assert result.transcript_source == "session-store"
    assert [message.content for message in result.transcript_messages] == [
        "Checking the room before moving."
    ]
    metrics = bridge.get_last_run_metrics()
    assert metrics["session_store_session_id"] == "new-session"
    assert metrics["session_store_message_count"] == 1
    bridge.close()
