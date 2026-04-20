"""Tests for roboclaws/openclaw/bridge.py — Phase 2.1 /v1/chat/completions transport."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import pytest

from roboclaws.openclaw.bridge import (
    OpenClawBridge,
    OpenClawProvider,
    OpenClawUnavailable,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int = 200, json_body: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    r.text = "" if json_body is None else str(json_body)
    return r


def _chat_response(content: str) -> dict:
    """Minimal OpenAI chat.completion response with a single choice."""
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


def _rgb_frame(size: int = 8, color: int = 128) -> np.ndarray:
    return np.full((size, size, 3), color, dtype=np.uint8)


# ---------------------------------------------------------------------------
# OpenClawBridge — construction + config
# ---------------------------------------------------------------------------


def test_bridge_uses_defaults():
    bridge = OpenClawBridge()
    assert bridge._gateway_url == "http://localhost:18789"
    assert bridge._agent_prefix == "agent-"
    bridge.close()


def test_bridge_gateway_url_from_env(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_URL", "http://gw.example:9000")
    bridge = OpenClawBridge()
    assert bridge._gateway_url == "http://gw.example:9000"
    bridge.close()


def test_bridge_token_from_env(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "s3cret")
    bridge = OpenClawBridge()
    assert bridge._token == "s3cret"
    assert bridge._client.headers["Authorization"] == "Bearer s3cret"
    bridge.close()


def test_bridge_explicit_args_override_env(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_URL", "http://env")
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "env-token")
    bridge = OpenClawBridge(gateway_url="http://explicit", token="explicit-token")
    assert bridge._gateway_url == "http://explicit"
    assert bridge._token == "explicit-token"
    bridge.close()


def test_bridge_strips_trailing_slash():
    bridge = OpenClawBridge(gateway_url="http://host/")
    assert bridge._gateway_url == "http://host"
    bridge.close()


def test_bridge_model_id():
    bridge = OpenClawBridge(agent_prefix="agent-")
    assert bridge.model_id(0) == "openclaw/agent-0"
    assert bridge.model_id(3) == "openclaw/agent-3"
    bridge.close()


def test_bridge_context_manager_closes_client():
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "close") as close:
        with bridge:
            pass
    close.assert_called_once()


# ---------------------------------------------------------------------------
# OpenClawBridge — healthcheck
# ---------------------------------------------------------------------------


def test_healthcheck_ok():
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "get", return_value=_mock_response(200)) as get:
        assert bridge.healthcheck() is True
    assert [c.args[0] for c in get.call_args_list] == ["/healthz", "/readyz"]
    bridge.close()


def test_healthcheck_fails_when_readyz_bad():
    bridge = OpenClawBridge()
    responses = [_mock_response(200), _mock_response(503)]
    with patch.object(bridge._client, "get", side_effect=responses):
        assert bridge.healthcheck() is False
    bridge.close()


def test_healthcheck_returns_false_on_connection_error():
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "get", side_effect=httpx.ConnectError("refused")):
        assert bridge.healthcheck() is False
    bridge.close()


# ---------------------------------------------------------------------------
# OpenClawBridge — step / chat.completions invocation
# ---------------------------------------------------------------------------


def test_bridge_step_posts_to_chat_completions():
    """POSTs to /v1/chat/completions with model=openclaw/agent-<id> and both images."""
    bridge = OpenClawBridge(token="abc")
    body = _chat_response('{"reasoning": "go", "action": "MoveAhead"}')
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)) as post:
        result = bridge.step(
            agent_id=1,
            frame=_rgb_frame(),
            overhead=_rgb_frame(color=32),
            state={"step": 3, "my_agent_id": 1},
            step_idx=3,
        )
    assert result == {"reasoning": "go", "action": "MoveAhead"}
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "/v1/chat/completions"
    payload = kwargs["json"]
    assert payload["model"] == "openclaw/agent-1"
    content = payload["messages"][0]["content"]
    # one text block + two image_url blocks
    kinds = [b["type"] for b in content]
    assert kinds == ["text", "image_url", "image_url"]
    # image_urls are inline data URLs (no filesystem path leakage)
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert content[2]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    bridge.close()


def test_bridge_step_parses_action_from_response():
    """Action JSON wrapped in a code fence still parses correctly."""
    bridge = OpenClawBridge()
    fenced = '```json\n{"reasoning": "spin", "action": "RotateLeft"}\n```'
    body = _chat_response(fenced)
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)):
        result = bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    assert result == {"reasoning": "spin", "action": "RotateLeft"}
    bridge.close()


def test_bridge_step_fallback_on_malformed_json():
    """Non-JSON LLM content falls back to MoveAhead without raising."""
    bridge = OpenClawBridge()
    body = _chat_response("Sorry, I don't know the map.")
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)):
        result = bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    assert result["action"] == "MoveAhead"
    # reasoning falls back to the raw content (truncated) for debugging
    assert "Sorry" in result["reasoning"]
    bridge.close()


def test_bridge_step_raises_on_400_invalid_model():
    """400 Invalid model → OpenClawUnavailable with a pointer at the bootstrap."""
    bridge = OpenClawBridge()
    resp = MagicMock()
    resp.status_code = 400
    resp.text = 'Invalid model: "openclaw/agent-5"'
    with patch.object(bridge._client, "post", return_value=resp):
        with pytest.raises(OpenClawUnavailable, match="openclaw-bootstrap.sh"):
            bridge.step(5, _rgb_frame(), _rgb_frame(), {}, 0)
    bridge.close()


def test_bridge_step_raises_on_404():
    """404 → OpenClawUnavailable pointing at re-running bootstrap."""
    bridge = OpenClawBridge()
    resp = MagicMock()
    resp.status_code = 404
    resp.text = "Not Found"
    with patch.object(bridge._client, "post", return_value=resp):
        with pytest.raises(OpenClawUnavailable, match="chat/completions not enabled"):
            bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    bridge.close()


def test_bridge_step_raises_on_401():
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", return_value=_mock_response(401)):
        with pytest.raises(OpenClawUnavailable, match="401"):
            bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    bridge.close()


def test_bridge_step_raises_on_5xx():
    bridge = OpenClawBridge()
    resp = MagicMock()
    resp.status_code = 500
    resp.text = '{"error": {"message": "upstream overloaded"}}'
    resp.json.return_value = {"error": {"message": "upstream overloaded"}}
    with patch.object(bridge._client, "post", return_value=resp):
        with pytest.raises(OpenClawUnavailable, match="upstream overloaded"):
            bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    bridge.close()


def test_bridge_step_raises_on_connection_error():
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(OpenClawUnavailable, match="unreachable"):
            bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    bridge.close()


def test_bridge_step_raises_on_read_timeout():
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", side_effect=httpx.ReadTimeout("slow")):
        with pytest.raises(OpenClawUnavailable):
            bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    bridge.close()


def test_bridge_uses_agent_prefix_in_model_id():
    """Custom agent_prefix flows into the outbound model id."""
    bridge = OpenClawBridge(agent_prefix="bot-")
    body = _chat_response('{"reasoning": "", "action": "MoveAhead"}')
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)) as post:
        bridge.step(3, _rgb_frame(), _rgb_frame(), {}, 0)
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == "openclaw/bot-3"
    bridge.close()


def test_bridge_validates_action_in_navigation_actions():
    """Invalid action name is coerced to MoveAhead; valid one passes through."""
    bridge = OpenClawBridge()
    # Invalid
    body_bad = _chat_response('{"reasoning": "wrong", "action": "WalkIntoWall"}')
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body_bad)):
        bad = bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    assert bad["action"] == "MoveAhead"
    # Valid (Teleport is in NAVIGATION_ACTIONS)
    body_ok = _chat_response('{"reasoning": "zap", "action": "Teleport"}')
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body_ok)):
        ok = bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    assert ok["action"] == "Teleport"
    bridge.close()


def test_bridge_ping_posts_pong_prompt():
    """ping() posts a minimal one-turn chat and returns the assistant reply."""
    bridge = OpenClawBridge()
    body = _chat_response("PONG")
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)) as post:
        reply = bridge.ping(agent_id=0)
    assert reply == "PONG"
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == "openclaw/agent-0"
    # A lightweight text-only prompt for the probe (no images)
    assert payload["messages"][0]["content"] == "Reply with only PONG."
    bridge.close()


def test_bridge_ping_raises_when_model_unknown():
    bridge = OpenClawBridge()
    resp = MagicMock()
    resp.status_code = 400
    resp.text = "Invalid model"
    with patch.object(bridge._client, "post", return_value=resp):
        with pytest.raises(OpenClawUnavailable, match="openclaw-bootstrap.sh"):
            bridge.ping(agent_id=99)
    bridge.close()


def test_bridge_handles_content_block_list():
    """Some providers return content as list[{type,text}] — still parses."""
    bridge = OpenClawBridge()
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": '{"reasoning": "',
                        },
                        {"type": "text", "text": 'ok", "action": "MoveBack"}'},
                    ],
                }
            }
        ]
    }
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)):
        result = bridge.step(0, _rgb_frame(), _rgb_frame(), {}, 0)
    assert result == {"reasoning": "ok", "action": "MoveBack"}
    bridge.close()


# ---------------------------------------------------------------------------
# OpenClawProvider adapter
# ---------------------------------------------------------------------------


def test_provider_delegates_to_bridge_step_with_numpy_frames():
    """Provider hands numpy frames straight to bridge.step() — no filesystem."""
    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    bridge.step.return_value = {"reasoning": "ok", "action": "RotateLeft"}

    provider = OpenClawProvider(bridge=bridge)
    images = [_rgb_frame(color=100), _rgb_frame(color=32)]
    state = {"my_agent_id": 2, "step": 7, "game": "openclaw-demo"}

    result = provider.get_action(images=images, state=state)

    assert result == {"reasoning": "ok", "action": "RotateLeft"}
    bridge.step.assert_called_once()
    kwargs = bridge.step.call_args.kwargs
    assert kwargs["agent_id"] == 2
    assert kwargs["step_idx"] == 7
    assert isinstance(kwargs["frame"], np.ndarray)
    assert isinstance(kwargs["overhead"], np.ndarray)
    assert kwargs["frame"].shape == images[0].shape
    assert kwargs["overhead"].shape == images[1].shape


def test_provider_handles_missing_images_with_placeholder():
    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    bridge.step.return_value = {"reasoning": "", "action": "MoveAhead"}

    provider = OpenClawProvider(bridge=bridge)
    provider.get_action(images=[], state={"current_agent": 0, "step": 0})

    kwargs = bridge.step.call_args.kwargs
    # Placeholder 1x1 black frames keep the named agent's payload well-formed.
    assert kwargs["frame"].shape == (1, 1, 3)
    assert kwargs["overhead"].shape == (1, 1, 3)


def test_provider_uses_current_agent_when_my_agent_id_missing():
    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    bridge.step.return_value = {"reasoning": "", "action": "MoveAhead"}

    provider = OpenClawProvider(bridge=bridge)
    provider.get_action(images=[], state={"current_agent": 3, "step": 0})

    assert bridge.step.call_args.kwargs["agent_id"] == 3


def test_provider_cost_is_zero():
    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    provider = OpenClawProvider(bridge=bridge)
    assert provider.cumulative_cost == 0.0
    provider.reset_cost()
    assert provider.cumulative_cost == 0.0


def test_provider_close_does_not_close_injected_bridge():
    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    provider = OpenClawProvider(bridge=bridge)
    provider.close()
    bridge.close.assert_not_called()


def test_provider_creates_its_own_bridge_when_not_given(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_URL", "http://localhost:9")
    provider = OpenClawProvider()
    try:
        assert isinstance(provider._bridge, OpenClawBridge)
        assert provider._owns_bridge is True
    finally:
        provider.close()


def test_provider_propagates_unavailable():
    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    bridge.step.side_effect = OpenClawUnavailable("no gateway")
    provider = OpenClawProvider(bridge=bridge)
    with pytest.raises(OpenClawUnavailable):
        provider.get_action(images=[_rgb_frame()], state={"step": 0})


def test_provider_ping_delegates_to_bridge():
    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    bridge.ping.return_value = "PONG"
    provider = OpenClawProvider(bridge=bridge)
    assert provider.ping(agent_id=1) == "PONG"
    bridge.ping.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# VLMProvider protocol compatibility
# ---------------------------------------------------------------------------


def test_provider_conforms_to_vlm_protocol():
    from roboclaws.core.vlm import VLMProvider

    bridge = MagicMock(spec=OpenClawBridge)
    bridge._agent_prefix = "agent-"
    provider = OpenClawProvider(bridge=bridge)
    assert isinstance(provider, VLMProvider)
