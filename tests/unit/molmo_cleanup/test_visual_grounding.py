from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from roboclaws.household.visual_grounding import (
    VISUAL_GROUNDING_RESPONSE_SCHEMA,
    HttpVisualGroundingClient,
    VisualGroundingClientConfig,
    VisualGroundingContractError,
    validate_visual_grounding_response,
    visual_grounding_client_from_env,
    visual_grounding_request,
)


def test_http_visual_grounding_client_posts_json_with_optional_bearer_auth() -> None:
    seen: dict[str, Any] = {}
    server = _start_server(_success_handler(seen))
    try:
        client = HttpVisualGroundingClient(
            VisualGroundingClientConfig(
                pipeline_id="grounding-dino",
                base_url=f"http://127.0.0.1:{server.server_port}",
                timeout_s=2,
                api_key="secret-token",
            )
        )
        response = client.request_candidates(_request())
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "ok"
    assert response["candidates"][0]["category"] == "dish"
    assert seen["authorization"] == "Bearer secret-token"
    assert seen["payload"]["image"]["bytes_base64"] == "ZmFrZQ=="
    assert client.config.redacted_metadata()["auth_mode"] == "bearer_configured"
    assert "secret-token" not in json.dumps(client.config.redacted_metadata())


def test_http_visual_grounding_client_accepts_valid_failure_response() -> None:
    server = _start_server(_failure_handler())
    try:
        client = HttpVisualGroundingClient(
            VisualGroundingClientConfig(
                pipeline_id="grounding-dino",
                base_url=f"http://127.0.0.1:{server.server_port}",
                timeout_s=2,
            )
        )
        response = client.request_candidates(_request())
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "failed"
    assert response["candidates"] == []
    assert response["error"]["reason"] == "adapter_unavailable"


def test_http_visual_grounding_client_accepts_http_error_failure_response() -> None:
    server = _start_server(_failure_handler(status_code=503))
    try:
        client = HttpVisualGroundingClient(
            VisualGroundingClientConfig(
                pipeline_id="grounding-dino",
                base_url=f"http://127.0.0.1:{server.server_port}",
                timeout_s=2,
            )
        )
        response = client.request_candidates(_request())
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "failed"
    assert response["candidates"] == []
    assert response["error"]["reason"] == "adapter_unavailable"


def test_http_visual_grounding_client_rejects_non_object_http_response() -> None:
    server = _start_server(_raw_response_handler(b"[]"))
    try:
        client = HttpVisualGroundingClient(
            VisualGroundingClientConfig(
                pipeline_id="grounding-dino",
                base_url=f"http://127.0.0.1:{server.server_port}",
                timeout_s=2,
            )
        )
        with pytest.raises(
            VisualGroundingContractError,
            match="visual grounding HTTP response source must contain a JSON object",
        ):
            client.request_candidates(_request())
    finally:
        server.shutdown()
        server.server_close()


def test_http_visual_grounding_client_retries_connection_setup_errors() -> None:
    client = HttpVisualGroundingClient(
        VisualGroundingClientConfig(
            pipeline_id="grounding-dino",
            base_url="http://127.0.0.1:9",
            timeout_s=0.05,
        )
    )

    response = client.request_candidates(_request())

    assert response["status"] == "failed"
    assert response["error"]["reason"] == "connection_error"
    assert response["pipeline"]["stages"][0]["status"] == "connection_error"


def test_visual_grounding_client_from_env_preserves_sim_without_timeout_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VISUAL_GROUNDING_TIMEOUT_S", "not-a-number")

    assert visual_grounding_client_from_env("sim") is None


def test_visual_grounding_client_from_env_rejects_invalid_timeout_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VISUAL_GROUNDING_TIMEOUT_S", "not-a-number")

    with pytest.raises(
        ValueError,
        match="VISUAL_GROUNDING_TIMEOUT_S must be a positive finite number of seconds",
    ):
        visual_grounding_client_from_env("grounding-dino")


def test_visual_grounding_client_from_env_rejects_non_positive_direct_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="visual_grounding_timeout_s must be a positive finite number of seconds",
    ):
        visual_grounding_client_from_env("grounding-dino", timeout_s=0)


def test_visual_grounding_response_rejects_unnormalized_bbox() -> None:
    with pytest.raises(VisualGroundingContractError):
        validate_visual_grounding_response(
            {
                "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
                "status": "ok",
                "pipeline": {
                    "pipeline_id": "bad",
                    "stages": [{"stage": "proposer", "latency_ms": 1}],
                },
                "candidates": [
                    {
                        "category": "dish",
                        "image_region": {"type": "bbox", "value": [10, 20, 30, 40]},
                    }
                ],
            }
        )


def test_visual_grounding_request_rejects_invalid_base64_as_contract_error() -> None:
    with pytest.raises(VisualGroundingContractError, match="not valid base64"):
        visual_grounding_request(
            run_id="seed-7",
            raw_observation={
                "observation_id": "raw_fpv_001",
                "waypoint_id": "wp_01",
                "room_id": "kitchen",
                "artifact_status": "recorded",
            },
            category_hints=["dish"],
            static_fixture_projection=[],
            pipeline_id="grounding-dino",
            image={
                "mime_type": "image/jpeg",
                "bytes_base64": "not base64!",
                "width": 2,
                "height": 2,
            },
        )


def test_visual_grounding_request_rejects_empty_image_bytes() -> None:
    with pytest.raises(VisualGroundingContractError, match="image.bytes_base64 is required"):
        visual_grounding_request(
            run_id="seed-7",
            raw_observation={
                "observation_id": "raw_fpv_001",
                "waypoint_id": "wp_01",
                "room_id": "kitchen",
                "artifact_status": "recorded",
            },
            category_hints=["dish"],
            static_fixture_projection=[],
            pipeline_id="grounding-dino",
            image={
                "mime_type": "image/jpeg",
                "bytes_base64": "",
                "width": 2,
                "height": 2,
            },
        )


def test_visual_grounding_request_rejects_zero_image_dimensions() -> None:
    with pytest.raises(VisualGroundingContractError, match="image.width must be positive"):
        visual_grounding_request(
            run_id="seed-7",
            raw_observation={
                "observation_id": "raw_fpv_001",
                "waypoint_id": "wp_01",
                "room_id": "kitchen",
                "artifact_status": "recorded",
            },
            category_hints=["dish"],
            static_fixture_projection=[],
            pipeline_id="grounding-dino",
            image={
                "mime_type": "image/jpeg",
                "bytes_base64": "ZmFrZQ==",
                "width": 0,
                "height": 2,
            },
        )


def _request() -> dict[str, Any]:
    return visual_grounding_request(
        run_id="seed-7",
        raw_observation={
            "observation_id": "raw_fpv_001",
            "waypoint_id": "wp_01",
            "room_id": "kitchen",
            "artifact_status": "recorded",
        },
        category_hints=["dish"],
        static_fixture_projection=[
            {"fixture_id": "sink_01", "room_id": "kitchen", "affordances": []}
        ],
        pipeline_id="grounding-dino",
        image={
            "mime_type": "image/jpeg",
            "bytes_base64": "ZmFrZQ==",
            "width": 2,
            "height": 2,
        },
    )


def _start_server(handler: type[BaseHTTPRequestHandler]) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _success_handler(seen: dict[str, Any]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            seen["authorization"] = self.headers.get("Authorization")
            length = int(self.headers.get("Content-Length") or 0)
            seen["payload"] = json.loads(self.rfile.read(length).decode("utf-8"))
            self._write_json(
                {
                    "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
                    "status": "ok",
                    "pipeline": {
                        "pipeline_id": "grounding-dino",
                        "stages": [
                            {
                                "stage": "proposer",
                                "producer_id": "grounding-dino",
                                "model_id": "fixture:grounding-dino",
                                "status": "ok",
                                "latency_ms": 1,
                            }
                        ],
                    },
                    "candidates": [
                        {
                            "category": "dish",
                            "image_region": {
                                "type": "bbox",
                                "value": [0.1, 0.2, 0.3, 0.4],
                            },
                            "confidence": 0.8,
                        }
                    ],
                }
            )

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _write_json(self, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _raw_response_handler(body: bytes, *, status_code: int = 200) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return Handler


def _failure_handler(*, status_code: int = 200) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self._write_json(
                {
                    "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
                    "status": "failed",
                    "pipeline": {
                        "pipeline_id": "grounding-dino",
                        "stages": [
                            {
                                "stage": "proposer",
                                "producer_id": "grounding-dino",
                                "model_id": "fixture:grounding-dino",
                                "status": "adapter_unavailable",
                                "latency_ms": 1,
                            }
                        ],
                    },
                    "candidates": [],
                    "error": {"reason": "adapter_unavailable", "message": "failure requested"},
                }
            )

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _write_json(self, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler
