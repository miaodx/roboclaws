from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from roboclaws.mcp.text_bridge import (
    VisionBridge,
    VisionBridgeResult,
    resolve_observe_delivery,
)


def _frame(color: int = 0) -> np.ndarray:
    return np.full((240, 320, 3), color, dtype=np.uint8)


class _FakeClient:
    def __init__(
        self, *, content: object = "Immediate view: clear path", exc: Exception | None = None
    ):
        self.content = content
        self.exc = exc
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_resolve_observe_delivery_auto_uses_text_bridge_for_text_only_mimo() -> None:
    assert (
        resolve_observe_delivery("mimo_openai/mimo-v2.5-pro", observe_mode="auto") == "text-bridge"
    )
    assert (
        resolve_observe_delivery("mimo_anthropic/mimo-v2.5", observe_mode="auto") == "text-bridge"
    )


def test_resolve_observe_delivery_auto_keeps_images_for_image_capable_models() -> None:
    assert resolve_observe_delivery("mimo_openai/mimo-v2-omni", observe_mode="auto") == "images"
    assert resolve_observe_delivery("anthropic_kimi/k2p5", observe_mode="auto") == "images"


def test_vision_bridge_sends_navigation_images_in_one_request() -> None:
    client = _FakeClient(content="Immediate view: table ahead.\nNavigation cues: rotate right.")
    bridge = VisionBridge(
        bridge_model="mimo_openai/mimo-v2-omni",
        image_model="mimo_openai/mimo-v2-omni",
        client=client,
    )

    result = bridge.describe(
        images=[_frame(10), _frame(200), _frame(80)],
        image_labels=["fpv", "map_v2", "chase"],
        state={"position": {"x": 1.0, "y": 0.0, "z": -2.0}, "rotation": {"y": 90.0}},
        view_variant="map-v2+chase",
    )

    assert isinstance(result, VisionBridgeResult)
    assert result.delivery == "text-bridge"
    assert result.bridge_model == "mimo_openai/mimo-v2-omni"
    assert result.error is None
    assert "Immediate view" in result.description

    request = client.calls[0]
    assert request["model"] == "mimo-v2-omni"
    content = request["messages"][1]["content"]
    image_parts = [part for part in content if part["type"] == "image_url"]
    assert len(image_parts) == 3
    assert content[0]["type"] == "text"


def test_vision_bridge_failure_returns_safe_fallback_text() -> None:
    client = _FakeClient(exc=RuntimeError("upstream unavailable"))
    bridge = VisionBridge(
        bridge_model="mimo_openai/mimo-v2-omni",
        image_model="mimo_openai/mimo-v2-omni",
        client=client,
    )

    result = bridge.describe(
        images=[_frame(10), _frame(200)],
        image_labels=["fpv", "map_v2"],
        state={"position": {"x": 1.0, "y": 0.0, "z": -2.0}},
        view_variant="map-v2+chase",
    )

    assert result.delivery == "text-bridge"
    assert result.bridge_model == "mimo_openai/mimo-v2-omni"
    assert result.error == "upstream unavailable"
    assert "Vision bridge unavailable" in result.description
