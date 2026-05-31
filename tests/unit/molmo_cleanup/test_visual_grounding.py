from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from roboclaws.molmo_cleanup.visual_grounding import (
    VISUAL_GROUNDING_RESPONSE_SCHEMA,
    HttpVisualGroundingClient,
    VisualGroundingClientConfig,
    VisualGroundingContractError,
    validate_visual_grounding_response,
    visual_grounding_request,
)


def test_http_visual_grounding_client_posts_json_with_optional_bearer_auth() -> None:
    seen: dict[str, Any] = {}
    server = _start_server(_success_handler(seen))
    try:
        client = HttpVisualGroundingClient(
            VisualGroundingClientConfig(
                pipeline_id="fake-http",
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
                pipeline_id="fake-http",
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
    assert response["error"]["reason"] == "fake_failure"


def test_http_visual_grounding_client_retries_connection_setup_errors() -> None:
    client = HttpVisualGroundingClient(
        VisualGroundingClientConfig(
            pipeline_id="fake-http",
            base_url="http://127.0.0.1:9",
            timeout_s=0.05,
        )
    )

    response = client.request_candidates(_request())

    assert response["status"] == "failed"
    assert response["error"]["reason"] == "connection_error"
    assert response["pipeline"]["stages"][0]["status"] == "connection_error"


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
            fixture_hints=[],
            pipeline_id="fake-http",
            image={
                "mime_type": "image/jpeg",
                "bytes_base64": "not base64!",
                "width": 2,
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
        fixture_hints=[{"fixture_id": "sink_01", "room_id": "kitchen", "affordances": []}],
        pipeline_id="fake-http",
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
                        "pipeline_id": "fake-http",
                        "stages": [
                            {
                                "stage": "proposer",
                                "producer_id": "fake-http",
                                "model_id": "fake",
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


def _failure_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self._write_json(
                {
                    "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
                    "status": "failed",
                    "pipeline": {
                        "pipeline_id": "fake-http",
                        "stages": [
                            {
                                "stage": "proposer",
                                "producer_id": "fake-http",
                                "model_id": "fake",
                                "status": "fake_failure",
                                "latency_ms": 1,
                            }
                        ],
                    },
                    "candidates": [],
                    "error": {"reason": "fake_failure", "message": "failure requested"},
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
