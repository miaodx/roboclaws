"""Unit tests for :mod:`roboclaws.openclaw.bridge`.

The bridge is HTTP-only and stateless, so we mock ``httpx.Client`` at the
method level rather than running an in-process server.  A real end-to-end
check (docker-compose Gateway) lives in the integration CI job from #39.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from roboclaws.openclaw.bridge import (
    BridgeResult,
    OpenClawBridge,
    OpenClawBridgeProvider,
    OpenClawUnavailable,
    _validate_result,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_body: dict[str, Any] | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"status {status_code}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _ok_action_body(action: str = "MoveAhead", reasoning: str = "go forward") -> dict[str, Any]:
    return {"ok": True, "result": {"reasoning": reasoning, "action": action}}


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_bridge_strips_trailing_slash() -> None:
    bridge = OpenClawBridge(gateway_url="http://localhost:18789/", token="t")
    assert bridge.gateway_url == "http://localhost:18789"
    bridge.close()


def test_bridge_sends_auth_header_when_token_provided() -> None:
    bridge = OpenClawBridge(token="secret-token")
    assert bridge._client.headers["Authorization"] == "Bearer secret-token"
    bridge.close()


def test_bridge_omits_auth_header_when_token_blank() -> None:
    bridge = OpenClawBridge(token="")
    assert "Authorization" not in bridge._client.headers
    bridge.close()


def test_bridge_reads_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "env-token")
    bridge = OpenClawBridge()
    assert bridge._client.headers["Authorization"] == "Bearer env-token"
    bridge.close()


def test_bridge_context_manager_closes_client() -> None:
    with OpenClawBridge(token="t") as bridge:
        inner = bridge._client
    # After exit the client is closed; httpx marks is_closed=True.
    assert inner.is_closed is True


# ---------------------------------------------------------------------------
# healthcheck
# ---------------------------------------------------------------------------


def test_healthcheck_both_200_returns_true() -> None:
    bridge = OpenClawBridge(token="t")
    with patch.object(bridge._client, "get", return_value=_mock_response(200)) as mock_get:
        assert bridge.healthcheck() is True
    assert [c.args[0] for c in mock_get.call_args_list] == ["/healthz", "/readyz"]
    bridge.close()


def test_healthcheck_readyz_fails_returns_false() -> None:
    bridge = OpenClawBridge(token="t")
    responses = [_mock_response(200), _mock_response(503)]
    with patch.object(bridge._client, "get", side_effect=responses):
        assert bridge.healthcheck() is False
    bridge.close()


def test_healthcheck_connection_error_returns_false() -> None:
    bridge = OpenClawBridge(token="t")
    with patch.object(bridge._client, "get", side_effect=httpx.ConnectError("refused")):
        assert bridge.healthcheck() is False
    bridge.close()


# ---------------------------------------------------------------------------
# step — happy path
# ---------------------------------------------------------------------------


def test_step_returns_validated_bridge_result() -> None:
    bridge = OpenClawBridge(token="t")
    resp = _mock_response(200, _ok_action_body(action="RotateLeft", reasoning="scan"))
    with patch.object(bridge._client, "post", return_value=resp) as mock_post:
        result = bridge.step(
            agent_id=1,
            frame_path="/work/frames/step-42/agent-1.jpg",
            overhead_path="/work/frames/step-42/overhead.jpg",
            state={"step": 42, "my_agent_id": 1},
            step_idx=42,
        )
    assert isinstance(result, BridgeResult)
    assert result.action == "RotateLeft"
    assert result.reasoning == "scan"

    # Verify payload shape
    ((_pos, _kw),) = mock_post.call_args_list[0:1]  # noqa: F841
    call = mock_post.call_args
    assert call.args[0] == "/tools/invoke"
    body = call.kwargs["json"]
    assert body["tool"] == "ai2thor-navigator"
    assert body["action"] == "step"
    assert body["sessionKey"] == "roboclaws-agent-1"
    assert body["dryRun"] is False
    assert body["args"]["step"] == 42
    assert body["args"]["frame_path"] == "/work/frames/step-42/agent-1.jpg"
    assert body["args"]["overhead_path"] == "/work/frames/step-42/overhead.jpg"
    assert body["args"]["state"] == {"step": 42, "my_agent_id": 1}
    bridge.close()


def test_step_custom_tool_name_and_session_prefix() -> None:
    bridge = OpenClawBridge(token="t", session_prefix="ci-agent", tool_name="my-skill")
    resp = _mock_response(200, _ok_action_body())
    with patch.object(bridge._client, "post", return_value=resp) as mock_post:
        bridge.step(
            agent_id=2,
            frame_path="/f.jpg",
            overhead_path="/o.jpg",
            state={},
            step_idx=0,
        )
    body = mock_post.call_args.kwargs["json"]
    assert body["tool"] == "my-skill"
    assert body["sessionKey"] == "ci-agent-2"
    bridge.close()


# ---------------------------------------------------------------------------
# step — error paths
# ---------------------------------------------------------------------------


def test_step_404_raises_openclaw_unavailable() -> None:
    bridge = OpenClawBridge(token="t")
    with patch.object(bridge._client, "post", return_value=_mock_response(404)):
        with pytest.raises(OpenClawUnavailable, match="not allowlisted"):
            bridge.step(
                agent_id=0,
                frame_path="/f.jpg",
                overhead_path="/o.jpg",
                state={},
                step_idx=0,
            )
    bridge.close()


def test_step_connection_error_raises_openclaw_unavailable() -> None:
    bridge = OpenClawBridge(gateway_url="http://nohost:1", token="t")
    with patch.object(bridge._client, "post", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(OpenClawUnavailable, match="Cannot reach Gateway"):
            bridge.step(
                agent_id=0,
                frame_path="/f.jpg",
                overhead_path="/o.jpg",
                state={},
                step_idx=0,
            )
    bridge.close()


def test_step_500_raises_http_status_error() -> None:
    bridge = OpenClawBridge(token="t")
    with patch.object(bridge._client, "post", return_value=_mock_response(500)):
        with pytest.raises(httpx.HTTPStatusError):
            bridge.step(
                agent_id=0,
                frame_path="/f.jpg",
                overhead_path="/o.jpg",
                state={},
                step_idx=0,
            )
    bridge.close()


def test_step_gateway_ok_false_raises_runtime_error() -> None:
    bridge = OpenClawBridge(token="t")
    resp = _mock_response(200, {"ok": False, "error": "skill crashed"})
    with patch.object(bridge._client, "post", return_value=resp):
        with pytest.raises(RuntimeError, match="Gateway returned error"):
            bridge.step(
                agent_id=0,
                frame_path="/f.jpg",
                overhead_path="/o.jpg",
                state={},
                step_idx=0,
            )
    bridge.close()


def test_step_invalid_action_raises_validation_error() -> None:
    """A nonsense action from the Gateway fails Pydantic validation."""
    from pydantic import ValidationError

    bridge = OpenClawBridge(token="t")
    bad_body = {"ok": True, "result": {"reasoning": "x", "action": "Teleport-to-Mars"}}
    with patch.object(bridge._client, "post", return_value=_mock_response(200, bad_body)):
        with pytest.raises(ValidationError):
            bridge.step(
                agent_id=0,
                frame_path="/f.jpg",
                overhead_path="/o.jpg",
                state={},
                step_idx=0,
            )
    bridge.close()


# ---------------------------------------------------------------------------
# _validate_result
# ---------------------------------------------------------------------------


def test_validate_result_accepts_all_navigation_actions() -> None:
    from roboclaws.core.engine import NAVIGATION_ACTIONS

    for action in NAVIGATION_ACTIONS:
        out = _validate_result({"reasoning": "r", "action": action})
        assert out.action == action


def test_validate_result_rejects_unknown_action() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _validate_result({"reasoning": "r", "action": "FlyToMoon"})


# ---------------------------------------------------------------------------
# OpenClawBridgeProvider adapter
# ---------------------------------------------------------------------------


def _fake_bridge(action: str = "MoveAhead") -> MagicMock:
    """Return a MagicMock OpenClawBridge whose ``.step`` yields the given action."""
    m = MagicMock(spec=OpenClawBridge)
    m.step.return_value = BridgeResult(reasoning="mock", action=action)
    return m


def test_provider_forwards_to_bridge_step() -> None:
    fake = _fake_bridge("RotateLeft")
    provider = OpenClawBridgeProvider(fake)
    out = provider.get_action(images=[], state={"my_agent_id": 2, "step": 7})
    assert out == {"reasoning": "mock", "action": "RotateLeft"}
    fake.step.assert_called_once()
    kwargs = fake.step.call_args.kwargs
    assert kwargs["agent_id"] == 2
    assert kwargs["step_idx"] == 7
    assert kwargs["frame_path"] == "<unavailable>"
    assert kwargs["overhead_path"] == "<unavailable>"


def test_provider_uses_path_callbacks_when_provided() -> None:
    fake = _fake_bridge()
    provider = OpenClawBridgeProvider(
        fake,
        frame_path_fn=lambda a, s: f"/work/step-{s}/agent-{a}.jpg",
        overhead_path_fn=lambda a, s: f"/work/step-{s}/overhead.jpg",
    )
    provider.get_action(images=[], state={"my_agent_id": 1, "step": 4})
    kwargs = fake.step.call_args.kwargs
    assert kwargs["frame_path"] == "/work/step-4/agent-1.jpg"
    assert kwargs["overhead_path"] == "/work/step-4/overhead.jpg"


def test_provider_defaults_agent_id_and_step() -> None:
    fake = _fake_bridge()
    provider = OpenClawBridgeProvider(fake)
    provider.get_action(images=[], state={})
    kwargs = fake.step.call_args.kwargs
    assert kwargs["agent_id"] == 0
    assert kwargs["step_idx"] == 0


def test_provider_cost_is_zero_and_resettable() -> None:
    provider = OpenClawBridgeProvider(_fake_bridge())
    assert provider.cumulative_cost == 0.0
    provider.reset_cost()  # must not raise
    assert provider.cumulative_cost == 0.0


def test_provider_satisfies_vlm_provider_protocol() -> None:
    from roboclaws.core.vlm import VLMProvider

    provider = OpenClawBridgeProvider(_fake_bridge())
    assert isinstance(provider, VLMProvider)
