"""Tests for roboclaws/openclaw/bridge.py."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import pytest
from PIL import Image

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


def _b64_frame(size: int = 4, color: int = 128) -> str:
    arr = np.full((size, size, 3), color, dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# OpenClawBridge — construction + config
# ---------------------------------------------------------------------------


def test_bridge_uses_defaults():
    bridge = OpenClawBridge()
    assert bridge._gateway_url == "http://localhost:18789"
    assert bridge._session_prefix == "roboclaws-agent"
    assert bridge._tool == "ai2thor-navigator"
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


def test_bridge_session_key():
    bridge = OpenClawBridge(session_prefix="ci-agent")
    assert bridge.session_key(0) == "ci-agent-0"
    assert bridge.session_key(2) == "ci-agent-2"
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
    # Calls /healthz and /readyz
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
# OpenClawBridge — step / tool invocation
# ---------------------------------------------------------------------------


def test_step_happy_path(tmp_path: Path):
    bridge = OpenClawBridge(token="abc")
    body = {
        "ok": True,
        "result": {"reasoning": "go", "action": "MoveAhead"},
    }
    frame, overhead = tmp_path / "f.jpg", tmp_path / "o.jpg"
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)) as post:
        result = bridge.step(
            agent_id=1,
            frame_path=frame,
            overhead_path=overhead,
            state={"step": 3},
            step_idx=3,
        )
    assert result == {"reasoning": "go", "action": "MoveAhead"}
    post.assert_called_once()
    path, kwargs = post.call_args
    assert path[0] == "/tools/invoke"
    payload = kwargs["json"]
    assert payload["tool"] == "ai2thor-navigator"
    assert payload["sessionKey"] == "roboclaws-agent-1"
    assert payload["args"]["frame_path"] == str(frame)
    assert payload["args"]["overhead_path"] == str(overhead)
    assert payload["args"]["state"] == {"step": 3}
    assert payload["args"]["step"] == 3
    assert payload["dryRun"] is False
    bridge.close()


def test_step_invalid_action_falls_back_to_moveahead(tmp_path: Path):
    bridge = OpenClawBridge()
    body = {"ok": True, "result": {"reasoning": "??", "action": "BogusAction"}}
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)):
        result = bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    assert result["action"] == "MoveAhead"
    bridge.close()


def test_step_404_raises_unavailable(tmp_path: Path):
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", return_value=_mock_response(404)):
        with pytest.raises(OpenClawUnavailable, match="not allowlisted"):
            bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    bridge.close()


def test_step_401_raises_unavailable(tmp_path: Path):
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", return_value=_mock_response(401)):
        with pytest.raises(OpenClawUnavailable, match="401"):
            bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    bridge.close()


def test_step_500_raises_unavailable(tmp_path: Path):
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", return_value=_mock_response(500)):
        with pytest.raises(OpenClawUnavailable, match="HTTP 500"):
            bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    bridge.close()


def test_step_connection_error_raises_unavailable(tmp_path: Path):
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(OpenClawUnavailable, match="unreachable"):
            bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    bridge.close()


def test_step_timeout_raises_unavailable(tmp_path: Path):
    bridge = OpenClawBridge()
    with patch.object(bridge._client, "post", side_effect=httpx.ReadTimeout("slow")):
        with pytest.raises(OpenClawUnavailable):
            bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    bridge.close()


def test_step_ok_false_raises_unavailable(tmp_path: Path):
    bridge = OpenClawBridge()
    body = {"ok": False, "error": "skill exec failed"}
    with patch.object(bridge._client, "post", return_value=_mock_response(200, body)):
        with pytest.raises(OpenClawUnavailable, match="Gateway reported error"):
            bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    bridge.close()


def test_step_non_json_raises_unavailable(tmp_path: Path):
    bridge = OpenClawBridge()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.side_effect = ValueError("not json")
    resp.text = "<html>"
    with patch.object(bridge._client, "post", return_value=resp):
        with pytest.raises(OpenClawUnavailable, match="non-JSON"):
            bridge.step(0, tmp_path / "f", tmp_path / "o", {}, 0)
    bridge.close()


# ---------------------------------------------------------------------------
# OpenClawProvider adapter
# ---------------------------------------------------------------------------


def test_provider_writes_images_and_delegates(tmp_path: Path):
    bridge = MagicMock(spec=OpenClawBridge)
    bridge.step.return_value = {"reasoning": "ok", "action": "RotateLeft"}

    provider = OpenClawProvider(bridge=bridge, work_dir=tmp_path)
    images = [_b64_frame(), _b64_frame(color=32)]
    state = {"my_agent_id": 2, "step": 7, "game": "territory"}

    result = provider.get_action(images=images, state=state)

    assert result == {"reasoning": "ok", "action": "RotateLeft"}
    bridge.step.assert_called_once()
    kwargs = bridge.step.call_args.kwargs
    assert kwargs["agent_id"] == 2
    assert kwargs["step_idx"] == 7
    frame_path = Path(kwargs["frame_path"])
    overhead_path = Path(kwargs["overhead_path"])
    assert frame_path.exists() and overhead_path.exists()
    # Written under work_dir/step-NNNN/
    assert frame_path.parent.parent == tmp_path
    assert "step-0007" in str(frame_path)
    # Verify the saved files are valid JPEGs
    assert Image.open(frame_path).size == (4, 4)


def test_provider_handles_missing_images(tmp_path: Path):
    bridge = MagicMock(spec=OpenClawBridge)
    bridge.step.return_value = {"reasoning": "", "action": "MoveAhead"}

    provider = OpenClawProvider(bridge=bridge, work_dir=tmp_path)
    provider.get_action(images=[], state={"current_agent": 0, "step": 0})

    kwargs = bridge.step.call_args.kwargs
    # Placeholder images still produced
    assert Path(kwargs["frame_path"]).exists()
    assert Path(kwargs["overhead_path"]).exists()


def test_provider_uses_current_agent_when_my_agent_id_missing(tmp_path: Path):
    bridge = MagicMock(spec=OpenClawBridge)
    bridge.step.return_value = {"reasoning": "", "action": "MoveAhead"}

    provider = OpenClawProvider(bridge=bridge, work_dir=tmp_path)
    provider.get_action(images=[], state={"current_agent": 3, "step": 0})

    assert bridge.step.call_args.kwargs["agent_id"] == 3


def test_provider_cost_is_zero():
    bridge = MagicMock(spec=OpenClawBridge)
    provider = OpenClawProvider(bridge=bridge)
    assert provider.cumulative_cost == 0.0
    provider.reset_cost()
    assert provider.cumulative_cost == 0.0


def test_provider_close_closes_owned_bridge():
    bridge = MagicMock(spec=OpenClawBridge)
    provider = OpenClawProvider(bridge=bridge)
    # Injected bridge is not owned
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


def test_provider_propagates_unavailable(tmp_path: Path):
    bridge = MagicMock(spec=OpenClawBridge)
    bridge.step.side_effect = OpenClawUnavailable("no gateway")
    provider = OpenClawProvider(bridge=bridge, work_dir=tmp_path)
    with pytest.raises(OpenClawUnavailable):
        provider.get_action(images=[_b64_frame()], state={"step": 0})


# ---------------------------------------------------------------------------
# VLMProvider protocol compatibility
# ---------------------------------------------------------------------------


def test_provider_conforms_to_vlm_protocol():
    from roboclaws.core.vlm import VLMProvider

    bridge = MagicMock(spec=OpenClawBridge)
    provider = OpenClawProvider(bridge=bridge)
    # runtime_checkable Protocol
    assert isinstance(provider, VLMProvider)
