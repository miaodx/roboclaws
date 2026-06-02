from __future__ import annotations

import base64
import io
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PIL import Image

from roboclaws.household.visual_grounding import (
    VISUAL_GROUNDING_RESPONSE_SCHEMA,
    HttpVisualGroundingClient,
    VisualGroundingClientConfig,
    visual_grounding_request,
)
from scripts.visual_grounding import adapters
from scripts.visual_grounding.adapters import visual_grounding_adapter_catalog
from scripts.visual_grounding.serve_visual_grounding_service import make_handler

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_SCRIPT = REPO_ROOT / "scripts" / "visual_grounding" / "serve_visual_grounding_service.py"


def test_configurable_service_reports_real_adapter_unavailable_by_default() -> None:
    server = _start_service(pipeline_id="grounding-dino", adapter_mode="auto")
    try:
        response = _client("grounding-dino", server).request_candidates(_request("grounding-dino"))
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "failed"
    assert response["candidates"] == []
    assert response["error"]["reason"] == "adapter_unavailable"
    assert response["pipeline"]["pipeline_id"] == "grounding-dino"
    assert response["pipeline"]["stages"][0]["stage"] == "proposer"
    assert response["pipeline"]["stages"][0]["producer_id"] == "grounding-dino"
    assert response["pipeline"]["stages"][0]["status"] == "adapter_unavailable"
    assert response["diagnostics"]["diagnostic_mode"] == "adapter_registry_stub"
    assert response["diagnostics"]["private_truth_included"] is False
    required = response["diagnostics"]["required_adapters"][0]
    assert required["producer_id"] == "grounding-dino"
    assert required["optional_extra"] == "visual-grounding-dino"
    assert "sidecar adapter" in required["setup_hint"]


def test_configurable_service_contract_fake_mode_serves_named_pipeline() -> None:
    server = _start_service(pipeline_id="grounding-dino", adapter_mode="contract-fake")
    try:
        response = _client("grounding-dino", server).request_candidates(_request("grounding-dino"))
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "ok"
    assert response["pipeline"]["pipeline_id"] == "grounding-dino"
    assert response["pipeline"]["stages"][0]["producer_id"] == "grounding-dino"
    assert response["candidates"][0]["category"] == "dish"
    assert response["diagnostics"]["diagnostic_mode"] == "deterministic_contract_fake"


def test_configurable_service_contract_fake_dispatcher_allows_request_pipeline() -> None:
    server = _start_service(pipeline_id="contract-fake", adapter_mode="auto")
    try:
        response = _client("yoloe+mimo-v2.5", server).request_candidates(
            _request("yoloe+mimo-v2.5")
        )
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "ok"
    assert response["pipeline"]["pipeline_id"] == "yoloe+mimo-v2.5"
    assert [stage["stage"] for stage in response["pipeline"]["stages"]] == [
        "proposer",
        "refiner",
    ]
    assert response["diagnostics"]["rejected_proposals"] == []


def test_real_mode_dispatches_grounding_dino_adapter(monkeypatch) -> None:
    def fake_grounding_dino_response(
        *,
        payload: dict[str, Any],
        pipeline_id: str,
        latency_ms: int,
    ) -> dict[str, Any]:
        assert payload["pipeline_request"]["pipeline_id"] == "grounding-dino"
        assert latency_ms == 1
        return {
            "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
            "status": "ok",
            "pipeline": {
                "pipeline_id": pipeline_id,
                "stages": [
                    {
                        "stage": "proposer",
                        "producer_id": "grounding-dino",
                        "model_id": "fake-real-model",
                        "status": "ok",
                        "latency_ms": 1,
                    }
                ],
            },
            "candidates": [
                {
                    "category": "dish",
                    "image_region": {"type": "bbox", "value": [0.1, 0.2, 0.3, 0.4]},
                    "confidence": 0.9,
                    "evidence_note": "fake real adapter candidate",
                    "destination_hint": {"candidate_fixture_id": "sink_01"},
                }
            ],
            "diagnostics": {
                "schema": "visual_grounding_diagnostics_v1",
                "diagnostic_mode": "real_grounding_dino",
                "raw_proposals": [],
                "rejected_proposals": [],
                "private_truth_included": False,
            },
        }

    monkeypatch.setattr(
        adapters,
        "_grounding_dino_real_response",
        fake_grounding_dino_response,
    )

    response = adapters.visual_grounding_service_response(
        payload=_request("grounding-dino"),
        configured_pipeline_id="grounding-dino",
        adapter_mode="real",
        latency_ms=1,
    )

    assert response["status"] == "ok"
    assert response["pipeline"]["stages"][0]["model_id"] == "fake-real-model"
    assert response["candidates"][0]["category"] == "dish"
    assert response["diagnostics"]["private_truth_included"] is False


def test_real_mode_reports_refiner_pipeline_missing_config_without_fake_success() -> None:
    response = adapters.visual_grounding_service_response(
        payload=_request("grounding-dino+mimo-v2.5"),
        configured_pipeline_id="grounding-dino+mimo-v2.5",
        adapter_mode="real",
        latency_ms=1,
    )

    assert response["status"] == "failed"
    assert response["error"]["reason"] == "missing_config"
    assert response["candidates"] == []
    assert response["pipeline"]["stages"][0]["stage"] == "refiner"
    assert response["pipeline"]["stages"][0]["producer_id"] == "mimo-v2.5"
    assert response["diagnostics"]["required_adapters"][0]["producer_id"] == "mimo-v2.5"


def test_real_mode_reports_grounding_dino_missing_dependency(monkeypatch) -> None:
    def missing_grounding_dino(
        _model_id: str,
        _requested_device: str,
        _requested_dtype: str,
    ) -> tuple[Any, Any, Any, dict[str, Any]]:
        raise ImportError("missing sidecar deps")

    monkeypatch.setattr(adapters, "_load_grounding_dino", missing_grounding_dino)

    response = adapters.visual_grounding_service_response(
        payload=_request("grounding-dino", image=_jpeg_image_payload()),
        configured_pipeline_id="grounding-dino",
        adapter_mode="real",
        latency_ms=1,
    )

    assert response["status"] == "failed"
    assert response["error"]["reason"] == "missing_dependency"
    assert response["candidates"] == []
    assert response["pipeline"]["stages"][0]["status"] == "missing_dependency"
    assert response["diagnostics"]["required_adapters"][0]["producer_id"] == "grounding-dino"
    assert response["diagnostics"]["private_truth_included"] is False


def test_real_mode_reports_grounding_dino_device_unavailable(monkeypatch) -> None:
    def cuda_unavailable(
        model_id: str,
        requested_device: str,
        requested_dtype: str,
    ) -> tuple[Any, Any, Any, dict[str, Any]]:
        assert model_id == "IDEA-Research/grounding-dino-tiny"
        assert requested_device == "cuda"
        assert requested_dtype == "float16"
        raise adapters.VisualGroundingDeviceError("cuda unavailable")

    monkeypatch.setattr(adapters, "_load_grounding_dino", cuda_unavailable)
    request = _request("grounding-dino", image=_jpeg_image_payload())
    request["pipeline_request"]["proposer"]["runtime_parameters"] = {
        "device": "cuda",
        "torch_dtype": "float16",
        "box_threshold": 0.25,
        "text_threshold": 0.2,
    }

    response = adapters.visual_grounding_service_response(
        payload=request,
        configured_pipeline_id="grounding-dino",
        adapter_mode="real",
        latency_ms=1,
    )

    assert response["status"] == "failed"
    assert response["error"]["reason"] == "device_unavailable"
    stage = response["pipeline"]["stages"][0]
    assert stage["runtime"]["requested_device"] == "cuda"
    assert stage["runtime"]["requested_dtype"] == "float16"
    assert stage["runtime_parameters"]["box_threshold"] == 0.25
    assert response["diagnostics"]["runtime"]["requested_device"] == "cuda"


def test_real_mode_dispatches_yolo_world_through_standard_yolo_loader(monkeypatch) -> None:
    seen: dict[str, str] = {}

    class FakeBoxes:
        xyxy = [[1, 2, 7, 6]]
        conf = [0.72]
        cls = [0]

    class FakeResult:
        boxes = FakeBoxes()
        names = {0: "dish"}

    class FakeModel:
        def predict(self, *, source: str, conf: float, verbose: bool) -> list[FakeResult]:
            assert source.endswith(".jpg")
            assert conf > 0
            assert verbose is False
            return [FakeResult()]

    def fake_yolo_loader(model_id: str, *, producer_id: str) -> FakeModel:
        seen["model_id"] = model_id
        seen["producer_id"] = producer_id
        return FakeModel()

    monkeypatch.setattr(adapters, "_load_yolo_model", fake_yolo_loader)

    response = adapters.visual_grounding_service_response(
        payload=_request("yolo-world", image=_jpeg_image_payload()),
        configured_pipeline_id="yolo-world",
        adapter_mode="real",
        latency_ms=1,
    )

    assert response["status"] == "ok"
    assert seen["producer_id"] == "yolo-world"
    assert response["pipeline"]["stages"][0]["producer_id"] == "yolo-world"
    assert response["candidates"][0]["category"] == "dish"
    assert response["diagnostics"]["diagnostic_mode"] == "real_yolo-world"


def test_real_mode_dispatches_omdet_turbo_adapter(monkeypatch) -> None:
    seen: dict[str, Any] = {}

    class FakeInputs(dict):
        input_ids = [[1]]

        def to(self, device: str) -> "FakeInputs":
            seen["device"] = device
            return self

    class FakeProcessor:
        def __call__(
            self,
            *,
            images: Image.Image,
            text: list[str],
            task: str,
            return_tensors: str,
        ) -> FakeInputs:
            assert images.size == (10, 10)
            assert text == ["a dish", "a book", "a toy"]
            assert task.startswith("Detect")
            assert return_tensors == "pt"
            seen["text"] = text
            return FakeInputs(pixel_values="fake")

        def post_process_grounded_object_detection(
            self,
            outputs: Any,
            *,
            text_labels: list[str],
            threshold: float,
            nms_threshold: float,
            target_sizes: list[tuple[int, int]],
            max_num_det: int | None,
        ) -> list[dict[str, Any]]:
            assert outputs == {"fake": "outputs"}
            assert text_labels == ["a dish", "a book", "a toy"]
            assert threshold == 0.2
            assert nms_threshold == 0.4
            assert target_sizes == [(10, 10)]
            assert max_num_det == 6
            return [
                {
                    "boxes": [[1, 2, 7, 6]],
                    "scores": [0.73],
                    "text_labels": ["a dish"],
                }
            ]

    class FakeModel:
        def __call__(self, **inputs: Any) -> dict[str, str]:
            assert inputs == {"pixel_values": "fake"}
            return {"fake": "outputs"}

    class FakeTorch:
        class _NoGrad:
            def __enter__(self) -> None:
                return None

            def __exit__(self, *_args: Any) -> None:
                return None

        def no_grad(self) -> "FakeTorch._NoGrad":
            return self._NoGrad()

    def fake_load_omdet(
        model_id: str,
        requested_device: str,
        requested_dtype: str,
    ) -> tuple[FakeProcessor, FakeModel, FakeTorch, dict[str, Any]]:
        seen["model_id"] = model_id
        seen["requested_device"] = requested_device
        seen["requested_dtype"] = requested_dtype
        return (
            FakeProcessor(),
            FakeModel(),
            FakeTorch(),
            {"device": "cpu", "dtype": "auto", "model_id": model_id},
        )

    monkeypatch.setattr(adapters, "_load_omdet_turbo", fake_load_omdet)
    request = _request("omdet-turbo", image=_jpeg_image_payload())
    request["pipeline_request"]["proposer"]["runtime_parameters"] = {
        "confidence_threshold": 0.2,
        "nms_threshold": 0.4,
        "max_detections": 6,
        "device": "cpu",
        "torch_dtype": "auto",
    }

    response = adapters.visual_grounding_service_response(
        payload=request,
        configured_pipeline_id="omdet-turbo",
        adapter_mode="real",
        latency_ms=1,
    )

    assert response["status"] == "ok"
    assert seen["model_id"] == "omlab/omdet-turbo-swin-tiny-hf"
    assert seen["requested_device"] == "cpu"
    assert response["pipeline"]["stages"][0]["producer_id"] == "omdet-turbo"
    assert response["pipeline"]["stages"][0]["runtime_parameters"]["confidence_threshold"] == 0.2
    assert response["candidates"][0]["category"] == "dish"
    assert response["diagnostics"]["diagnostic_mode"] == "real_omdet-turbo"


def test_real_mode_direct_mimo_uses_hosted_vlm_boundary(monkeypatch) -> None:
    seen: dict[str, Any] = {}
    server = _start_chat_server(
        seen,
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "candidates": [
                                    {
                                        "category": "dish",
                                        "image_region": {
                                            "type": "bbox",
                                            "value": [0.1, 0.2, 0.3, 0.4],
                                        },
                                        "confidence": 0.88,
                                        "evidence_note": "white dish in frame",
                                        "destination_hint": {
                                            "candidate_fixture_id": "sink_01",
                                            "confidence": 0.5,
                                        },
                                    }
                                ],
                                "rejected_proposals": [],
                            }
                        )
                    }
                }
            ]
        },
    )
    monkeypatch.setenv(
        "VISUAL_GROUNDING_MIMO_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1"
    )
    monkeypatch.setenv("VISUAL_GROUNDING_MIMO_API_KEY", "secret-mimo-key")
    try:
        response = adapters.visual_grounding_service_response(
            payload=_request("mimo-v2.5-direct", image=_jpeg_image_payload()),
            configured_pipeline_id="mimo-v2.5-direct",
            adapter_mode="real",
            latency_ms=1,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "ok"
    assert response["pipeline"]["stages"][0]["stage"] == "direct_producer"
    assert response["pipeline"]["stages"][0]["producer_id"] == "mimo-v2.5"
    assert response["candidates"][0]["category"] == "dish"
    assert response["diagnostics"]["diagnostic_mode"] == "real_mimo-v2.5_direct"
    assert response["diagnostics"]["private_truth_included"] is False
    assert seen["path"] == "/v1/chat/completions"
    assert seen["authorization"] == "Bearer secret-mimo-key"
    assert seen["payload"]["model"] == "mimo-v2.5"
    content = seen["payload"]["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "secret-mimo-key" not in json.dumps(response)


def test_real_mode_refines_proposals_with_hosted_mimo(monkeypatch) -> None:
    def fake_proposer_response(
        *,
        payload: dict[str, Any],
        pipeline_id: str,
        producer_id: str,
        latency_ms: int,
    ) -> dict[str, Any] | None:
        assert producer_id == "grounding-dino"
        return {
            "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
            "status": "ok",
            "pipeline": {
                "pipeline_id": pipeline_id,
                "stages": [
                    {
                        "stage": "proposer",
                        "producer_id": producer_id,
                        "model_id": "fake-dino",
                        "version": "test",
                        "status": "ok",
                        "latency_ms": latency_ms,
                    }
                ],
            },
            "candidates": [
                {
                    "category": "dish",
                    "image_region": {"type": "bbox", "value": [0.1, 0.2, 0.3, 0.4]},
                    "confidence": 0.55,
                    "evidence_note": "proposal before refiner",
                    "destination_hint": {"candidate_fixture_id": "sink_01"},
                }
            ],
            "diagnostics": {
                "schema": "visual_grounding_diagnostics_v1",
                "diagnostic_mode": "fake_proposer",
                "raw_proposals": [],
                "rejected_proposals": [],
                "private_truth_included": False,
            },
        }

    seen: dict[str, Any] = {}
    server = _start_chat_server(
        seen,
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "candidates": [
                                            {
                                                "proposal_id": "proposal_001",
                                                "category": "dish",
                                                "confidence": 0.91,
                                                "evidence_note": "refiner accepted proposal",
                                            }
                                        ],
                                        "rejected_proposals": [
                                            {
                                                "proposal_id": "proposal_999",
                                                "reason": "not visible",
                                            }
                                        ],
                                    }
                                ),
                            }
                        ],
                    }
                }
            ]
        },
    )
    monkeypatch.setattr(adapters, "_real_proposer_response", fake_proposer_response)
    monkeypatch.setenv(
        "VISUAL_GROUNDING_MIMO_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1"
    )
    monkeypatch.setenv("VISUAL_GROUNDING_MIMO_API_KEY", "secret-mimo-key")
    try:
        response = adapters.visual_grounding_service_response(
            payload=_request("grounding-dino+mimo-v2.5", image=_jpeg_image_payload()),
            configured_pipeline_id="grounding-dino+mimo-v2.5",
            adapter_mode="real",
            latency_ms=1,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "ok"
    assert [stage["stage"] for stage in response["pipeline"]["stages"]] == [
        "proposer",
        "refiner",
    ]
    assert response["pipeline"]["stages"][1]["producer_id"] == "mimo-v2.5"
    assert response["candidates"][0]["confidence"] == 0.91
    assert response["candidates"][0]["image_region"] == {
        "type": "bbox",
        "value": [0.1, 0.2, 0.3, 0.4],
    }
    assert response["diagnostics"]["raw_proposals"]
    assert response["diagnostics"]["rejected_proposals"][0]["reason"] == "not visible"
    assert "private_labels" not in json.dumps(seen["payload"])


def test_real_mode_qwen_direct_reports_missing_config_without_fake_success() -> None:
    response = adapters.visual_grounding_service_response(
        payload=_request("qwen3-vl-direct", image=_jpeg_image_payload()),
        configured_pipeline_id="qwen3-vl-direct",
        adapter_mode="real",
        latency_ms=1,
    )

    assert response["status"] == "failed"
    assert response["error"]["reason"] == "missing_config"
    assert response["candidates"] == []
    assert response["pipeline"]["stages"][0]["stage"] == "direct_producer"
    assert response["pipeline"]["stages"][0]["producer_id"] == "qwen3-vl"
    assert response["diagnostics"]["required_adapters"][0]["producer_id"] == "qwen3-vl"


def test_real_adapter_bbox_normalization_and_destination_hint() -> None:
    request = _request("grounding-dino")
    candidate = adapters._candidate_from_xyxy(  # noqa: SLF001
        payload=request,
        image=_tiny_image(),
        category="dish",
        xyxy=[1, 2, 7, 6],
        confidence=1.2,
        evidence_note="unit probe",
    )

    assert candidate is not None
    assert candidate["image_region"] == {"type": "bbox", "value": [0.1, 0.2, 0.6, 0.4]}
    assert candidate["confidence"] == 1.0
    assert candidate["destination_hint"]["candidate_fixture_id"] == "sink_01"


def test_configurable_service_rejects_pipeline_mismatch() -> None:
    server = _start_service(pipeline_id="grounding-dino", adapter_mode="contract-fake")
    try:
        response = _client("yoloe", server).request_candidates(_request("yoloe"))
    finally:
        server.shutdown()
        server.server_close()

    assert response["status"] == "failed"
    assert response["error"]["reason"] == "pipeline_mismatch"
    assert response["candidates"] == []


def test_adapter_catalog_lists_real_adapter_slots_without_private_truth() -> None:
    catalog = visual_grounding_adapter_catalog()

    assert catalog["schema"] == "visual_grounding_adapter_catalog_v1"
    assert "real" in catalog["adapter_modes"]
    assert catalog["private_truth_included"] is False
    by_id = {item["producer_id"]: item for item in catalog["adapters"]}
    assert "yolo-custom" not in by_id
    assert by_id["fake-http"]["status"] == "available"
    assert by_id["fake-http"]["runtime"]["status"] == "available"
    assert by_id["grounding-dino"]["optional_extra"] == "visual-grounding-dino"
    assert by_id["grounding-dino"]["runtime"]["status"] in {
        "missing_dependency",
        "dependency_ready_model_unverified",
    }
    assert {item["name"] for item in by_id["grounding-dino"]["runtime"]["checks"]} == {
        "torch",
        "transformers",
    }
    assert by_id["yoloe"]["optional_extra"] == "visual-grounding-yoloe"
    assert {item["name"] for item in by_id["yoloe"]["runtime"]["checks"]} == {"ultralytics"}
    assert by_id["yolo-world"]["optional_extra"] == "visual-grounding-yolo-world"
    assert {item["name"] for item in by_id["yolo-world"]["runtime"]["checks"]} == {"ultralytics"}
    assert by_id["omdet-turbo"]["optional_extra"] == "visual-grounding-omdet"
    assert {item["name"] for item in by_id["omdet-turbo"]["runtime"]["checks"]} == {
        "torch",
        "transformers",
    }
    assert by_id["mimo-v2.5"]["role"] == "refiner_or_direct_producer"
    assert by_id["mimo-v2.5"]["runtime"]["status"] in {"configured", "missing_config"}
    assert by_id["mimo-v2.5"]["runtime"]["auth_mode"] in {
        "none",
        "bearer_configured",
    }
    assert by_id["qwen3-vl"]["optional_extra"] == "visual-grounding-qwen3vl"
    assert by_id["qwen3-vl"]["runtime"]["status"] in {"configured", "missing_config"}
    assert "authorization" not in json.dumps(catalog).lower()
    assert "secret-mimo-key" not in json.dumps(catalog)


def test_configurable_service_lists_adapter_catalog_cli() -> None:
    result = subprocess.run(
        [sys.executable, str(SERVICE_SCRIPT), "--list-adapters"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    catalog = json.loads(result.stdout)
    assert catalog["schema"] == "visual_grounding_adapter_catalog_v1"
    assert {item["producer_id"] for item in catalog["adapters"]} >= {
        "fake-http",
        "grounding-dino",
        "yoloe",
        "yolo-world",
        "omdet-turbo",
        "mimo-v2.5",
        "qwen3-vl",
    }
    assert "yolo-custom" not in {item["producer_id"] for item in catalog["adapters"]}
    by_id = {item["producer_id"]: item for item in catalog["adapters"]}
    assert "runtime" in by_id["grounding-dino"]
    assert "runtime" in by_id["mimo-v2.5"]
    assert "authorization" not in result.stdout.lower()
    assert "secret-mimo-key" not in result.stdout


def _start_service(*, pipeline_id: str, adapter_mode: str) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(pipeline_id=pipeline_id, adapter_mode=adapter_mode, latency_ms=1),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _start_chat_server(
    seen: dict[str, Any],
    response_payload: dict[str, Any],
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            seen["path"] = self.path
            seen["authorization"] = self.headers.get("Authorization")
            seen["payload"] = json.loads(self.rfile.read(length).decode("utf-8"))
            body = json.dumps(response_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _client(pipeline_id: str, server: ThreadingHTTPServer) -> HttpVisualGroundingClient:
    return HttpVisualGroundingClient(
        VisualGroundingClientConfig(
            pipeline_id=pipeline_id,
            base_url=f"http://127.0.0.1:{server.server_port}",
            timeout_s=2,
        )
    )


def _tiny_image() -> Image.Image:
    return Image.new("RGB", (10, 10), (240, 240, 240))


def _request(pipeline_id: str, *, image: dict[str, Any] | None = None) -> dict[str, Any]:
    return visual_grounding_request(
        run_id="seed-7",
        raw_observation={
            "observation_id": "raw_fpv_kitchen_dish_001",
            "waypoint_id": "wp_kitchen_01",
            "room_id": "kitchen",
            "artifact_status": "recorded",
        },
        category_hints=["dish", "book", "toy"],
        fixture_hints=[
            {
                "fixture_id": "sink_01",
                "room_id": "kitchen",
                "category": "sink",
                "affordances": ["inside"],
            }
        ],
        pipeline_id=pipeline_id,
        image=image
        or {
            "mime_type": "image/jpeg",
            "bytes_base64": "ZmFrZQ==",
            "width": 2,
            "height": 2,
        },
        proposer={"producer_id": pipeline_id.split("+", maxsplit=1)[0]},
    )


def _jpeg_image_payload() -> dict[str, Any]:
    buffer = io.BytesIO()
    _tiny_image().save(buffer, format="JPEG", quality=90)
    return {
        "mime_type": "image/jpeg",
        "bytes_base64": base64.b64encode(buffer.getvalue()).decode("ascii"),
        "width": 10,
        "height": 10,
    }
