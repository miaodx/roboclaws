from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from scripts.visual_grounding.adapters import (
    ADAPTER_MODE_REAL,
    CONTRACT_FAKE_PIPELINE_ID,
    FAKE_HTTP_PIPELINE_ID,
    REAL_ROUTER_PIPELINE_ID,
    effective_pipeline_id,
    pipeline_request_is_allowed,
    should_use_contract_fake,
    visual_grounding_adapter_catalog,
)
from scripts.visual_grounding.serve_fake_visual_grounding import make_handler
from scripts.visual_grounding.serve_visual_grounding_service import (
    make_handler as make_configurable_handler,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPO_ROOT / "harness" / "visual_grounding" / "smoke_corpus.json"
RUNNER = REPO_ROOT / "scripts" / "visual_grounding" / "run_visual_grounding_benchmark.py"
CHECKER = REPO_ROOT / "scripts" / "visual_grounding" / "check_visual_grounding_benchmark_result.py"


def test_visual_grounding_real_router_allows_requested_real_pipeline() -> None:
    selected = effective_pipeline_id(
        configured_pipeline_id=REAL_ROUTER_PIPELINE_ID,
        requested_pipeline_id="grounding-dino",
    )

    assert selected == "grounding-dino"
    assert pipeline_request_is_allowed(
        configured_pipeline_id=REAL_ROUTER_PIPELINE_ID,
        requested_pipeline_id="yoloe",
        effective_pipeline_id="yoloe",
    )
    assert not should_use_contract_fake(
        configured_pipeline_id=REAL_ROUTER_PIPELINE_ID,
        effective_pipeline_id="grounding-dino",
        adapter_mode=ADAPTER_MODE_REAL,
    )
    assert should_use_contract_fake(
        configured_pipeline_id=REAL_ROUTER_PIPELINE_ID,
        effective_pipeline_id=FAKE_HTTP_PIPELINE_ID,
        adapter_mode=ADAPTER_MODE_REAL,
    )
    assert should_use_contract_fake(
        configured_pipeline_id=CONTRACT_FAKE_PIPELINE_ID,
        effective_pipeline_id="grounding-dino",
        adapter_mode=ADAPTER_MODE_REAL,
    )
    catalog = visual_grounding_adapter_catalog()
    assert catalog["real_router_pipeline_id"] == REAL_ROUTER_PIPELINE_ID


def test_visual_grounding_benchmark_runs_against_fake_http_service(tmp_path: Path) -> None:
    server = _start_fake_server(mode="success")
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--corpus",
                str(CORPUS),
                "--output-dir",
                str(tmp_path),
                "--pipeline",
                "fake-http",
                "--base-url",
                base_url,
                "--timeout-s",
                "2",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    finally:
        server.shutdown()
        server.server_close()

    subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(tmp_path),
            "--expect-pipeline",
            "fake-http",
            "--require-success",
            "--require-candidates",
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    result = json.loads((tmp_path / "visual_grounding_benchmark_result.json").read_text())
    pipeline = result["pipelines"][0]
    assert pipeline["pipeline_id"] == "fake-http"
    assert pipeline["candidate_count"] == 3
    assert pipeline["failure_count"] == 0
    assert pipeline["timeout_rate"] == 0.0
    assert pipeline["evidence_level"] == "contract_fake"
    assert pipeline["metrics"]["recall"] == 1.0
    assert pipeline["metrics"]["precision"] < 1.0
    assert pipeline["metrics"]["destination_hint_rate"] == 1.0
    assert pipeline["metrics"]["destination_hint_known_fixture_rate"] == 1.0
    assert pipeline["metrics"]["actionability_proxy_rate"] > 0.0
    assert pipeline["stage_summary"][0]["producer_id"] == "fake-http"
    assert result["corpus"]["private_labels_in_requests"] is False
    promotion = result["promotion_recommendation"]
    assert promotion["selected_end_to_end_pipelines"] == [
        "sim",
        "fake-http",
    ]
    assert promotion["selected_real_stage_provenance_complete"] is False
    assert promotion["requires_real_stage_provenance_before_promotion"] is True

    predictions = (tmp_path / "visual_grounding_predictions.jsonl").read_text(encoding="utf-8")
    assert "private_labels" not in predictions
    assert "bytes_base64" not in predictions
    assert "Bearer " not in predictions
    assert (tmp_path / "overlays" / "raw_fpv_kitchen_dish_001" / "fake-http.jpg").is_file()
    report = (tmp_path / "visual_grounding_benchmark_report.html").read_text(encoding="utf-8")
    assert "Visual Grounding Quality" in report
    assert "Destination Hint Quality" in report
    assert "Real stage provenance present: False" in report
    assert "Requires real stage provenance before promotion: True" in report


def test_visual_grounding_benchmark_records_fake_http_failure(tmp_path: Path) -> None:
    server = _start_fake_server(mode="failure")
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--corpus",
                str(CORPUS),
                "--output-dir",
                str(tmp_path),
                "--pipeline",
                "fake-http",
                "--base-url",
                base_url,
                "--timeout-s",
                "2",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    finally:
        server.shutdown()
        server.server_close()

    subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(tmp_path),
            "--expect-pipeline",
            "fake-http",
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    result = json.loads((tmp_path / "visual_grounding_benchmark_result.json").read_text())
    pipeline = result["pipelines"][0]
    assert pipeline["candidate_count"] == 0
    assert pipeline["failure_count"] == 3
    assert pipeline["timeout_count"] == 0
    assert pipeline["timeout_rate"] == 0.0
    predictions = [
        json.loads(line)
        for line in (tmp_path / "visual_grounding_predictions.jsonl").read_text().splitlines()
    ]
    assert {item["pipeline"]["status"] for item in predictions} == {"failed"}
    assert {item["error"]["reason"] for item in predictions} == {"fake_failure"}


def test_visual_grounding_checker_allows_zero_candidate_success_without_candidate_gate(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    corpus.write_text(
        json.dumps(
            {
                "schema": "visual_grounding_benchmark_corpus_v1",
                "name": "zero-candidate-success",
                "category_family_map": {"dish": "dish"},
                "observations": [
                    {
                        "observation_id": "raw_fpv_room_2_empty_001",
                        "waypoint_id": "room_2_scan_1",
                        "room_id": "room_2",
                        "capture_context": {"discovered_during": "waypoint_observe"},
                        "category_hints": ["dish"],
                        "fixture_hints": [],
                        "image": {
                            "source": "synthetic",
                            "width": 32,
                            "height": 24,
                            "background": [220, 220, 220],
                            "objects": [],
                        },
                        "private_labels": [{"category": "dish", "category_family": "dish"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = _start_fake_server(mode="success")
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--corpus",
                str(corpus),
                "--output-dir",
                str(tmp_path / "benchmark"),
                "--pipeline",
                "grounding-dino",
                "--base-url",
                base_url,
                "--timeout-s",
                "2",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    finally:
        server.shutdown()
        server.server_close()

    subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(tmp_path / "benchmark"),
            "--expect-pipeline",
            "grounding-dino",
            "--require-success",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    candidate_gate = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(tmp_path / "benchmark"),
            "--expect-pipeline",
            "grounding-dino",
            "--require-success",
            "--require-candidates",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    result_path = tmp_path / "benchmark" / "visual_grounding_benchmark_result.json"
    result = json.loads(result_path.read_text())
    assert result["pipelines"][0]["failure_count"] == 0
    assert result["pipelines"][0]["candidate_count"] == 0
    assert candidate_gate.returncode == 1
    assert "pipeline has no candidates" in candidate_gate.stderr


def test_visual_grounding_benchmark_compares_named_contract_pipelines(tmp_path: Path) -> None:
    server = _start_fake_server(mode="success")
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--corpus",
                str(CORPUS),
                "--output-dir",
                str(tmp_path),
                "--pipeline",
                "grounding-dino,yoloe,yoloe+mimo-v2-omni,mimo-v2-omni-direct",
                "--base-url",
                base_url,
                "--timeout-s",
                "2",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    finally:
        server.shutdown()
        server.server_close()

    subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(tmp_path),
            "--require-success",
            "--require-candidates",
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    result = json.loads((tmp_path / "visual_grounding_benchmark_result.json").read_text())
    by_pipeline = {item["pipeline_id"]: item for item in result["pipelines"]}
    assert set(by_pipeline) == {
        "grounding-dino",
        "yoloe",
        "yoloe+mimo-v2-omni",
        "mimo-v2-omni-direct",
    }
    assert by_pipeline["grounding-dino"]["stage_summary"][0]["producer_id"] == "grounding-dino"
    assert by_pipeline["grounding-dino"]["metrics"]["precision"] == 1.0
    assert by_pipeline["yoloe"]["stage_summary"][0]["producer_id"] == "yoloe"
    assert by_pipeline["yoloe"]["metrics"]["precision"] < 1.0
    assert by_pipeline["yoloe"]["metrics"]["duplicate_count"] >= 1
    assert by_pipeline["grounding-dino"]["metrics"]["actionability_proxy_rate"] > 0.0
    assert by_pipeline["yoloe"]["metrics"]["destination_hint_rate"] == 1.0
    assert [stage["stage"] for stage in by_pipeline["yoloe+mimo-v2-omni"]["stage_summary"]] == [
        "proposer",
        "refiner",
    ]
    assert by_pipeline["yoloe+mimo-v2-omni"]["metrics"]["rejected_proposal_count"] >= 1
    assert by_pipeline["mimo-v2-omni-direct"]["stage_summary"][0]["stage"] == "direct_producer"
    assert result["ranking"][0]["pipeline_id"] in {
        "grounding-dino",
        "mimo-v2-omni-direct",
        "yoloe+mimo-v2-omni",
    }
    assert "actionability_proxy_rate" in result["ranking"][0]
    promotion = result["promotion_recommendation"]
    assert promotion["selected_end_to_end_pipelines"][0] == "sim"
    assert promotion["best_proposer_only_pipeline_id"] == "grounding-dino"
    assert promotion["best_proposer_plus_refiner_pipeline_id"] == "yoloe+mimo-v2-omni"
    assert promotion["best_direct_vlm_pipeline_id"] == "mimo-v2-omni-direct"
    assert promotion["selected_real_stage_provenance_complete"] is False
    assert promotion["requires_real_stage_provenance_before_promotion"] is True
    assert (
        len(
            [
                pipeline_id
                for pipeline_id in promotion["selected_end_to_end_pipelines"]
                if pipeline_id.endswith("-direct")
            ]
        )
        <= 1
    )

    predictions = [
        json.loads(line)
        for line in (tmp_path / "visual_grounding_predictions.jsonl").read_text().splitlines()
    ]
    refined = [
        item
        for item in predictions
        if item["pipeline_id"] == "yoloe+mimo-v2-omni"
        and item["diagnostic_evidence"]["rejected_proposal_count"]
    ]
    assert refined
    assert "private_labels" not in json.dumps(predictions)
    assert "bytes_base64" not in json.dumps(predictions)


def test_visual_grounding_benchmark_runs_against_configurable_contract_fake_service(
    tmp_path: Path,
) -> None:
    server = _start_configurable_service(pipeline_id="contract-fake", adapter_mode="auto")
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--corpus",
                str(CORPUS),
                "--output-dir",
                str(tmp_path),
                "--pipeline",
                "grounding-dino,yoloe",
                "--base-url",
                base_url,
                "--timeout-s",
                "2",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    finally:
        server.shutdown()
        server.server_close()

    subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(tmp_path),
            "--require-success",
            "--require-candidates",
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    result = json.loads((tmp_path / "visual_grounding_benchmark_result.json").read_text())
    assert {item["pipeline_id"] for item in result["pipelines"]} == {
        "grounding-dino",
        "yoloe",
    }
    assert all(item["failure_count"] == 0 for item in result["pipelines"])


def test_visual_grounding_benchmark_runs_hosted_vlm_direct_through_configurable_service(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seen: dict[str, Any] = {}
    chat_server = _start_chat_server(
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
                                            "value": [0.4, 0.42, 0.22, 0.18],
                                        },
                                        "confidence": 0.83,
                                        "evidence_note": "fake hosted VLM direct output",
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
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        },
    )
    monkeypatch.setenv(
        "VISUAL_GROUNDING_MIMO_BASE_URL",
        f"http://127.0.0.1:{chat_server.server_port}/v1",
    )
    monkeypatch.setenv("VISUAL_GROUNDING_MIMO_API_KEY", "secret-mimo-key")
    monkeypatch.setenv("VISUAL_GROUNDING_VLM_INPUT_USD_PER_1K_TOKENS", "0.001")
    monkeypatch.setenv("VISUAL_GROUNDING_VLM_OUTPUT_USD_PER_1K_TOKENS", "0.002")
    service = _start_configurable_service(
        pipeline_id="mimo-v2-omni-direct",
        adapter_mode="real",
    )
    try:
        base_url = f"http://127.0.0.1:{service.server_port}"
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--corpus",
                str(CORPUS),
                "--output-dir",
                str(tmp_path),
                "--pipeline",
                "mimo-v2-omni-direct",
                "--base-url",
                base_url,
                "--timeout-s",
                "2",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    finally:
        service.shutdown()
        service.server_close()
        chat_server.shutdown()
        chat_server.server_close()

    subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(tmp_path),
            "--expect-pipeline",
            "mimo-v2-omni-direct",
            "--require-success",
            "--require-candidates",
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    result = json.loads((tmp_path / "visual_grounding_benchmark_result.json").read_text())
    pipeline = result["pipelines"][0]
    assert pipeline["pipeline_id"] == "mimo-v2-omni-direct"
    assert pipeline["failure_count"] == 0
    assert pipeline["auth_mode"] == "bearer_configured"
    assert pipeline["evidence_level"] == "real_or_hosted_service"
    assert pipeline["api_cost"]["available"] is True
    assert pipeline["api_cost"]["total_usd"] > 0
    assert pipeline["api_cost"]["token_usage"]["total_tokens"] == 360
    assert pipeline["memory_profile"]["available"] is False
    assert seen["path"] == "/v1/chat/completions"
    assert seen["authorization"] == "Bearer secret-mimo-key"
    assert "secret-mimo-key" not in json.dumps(result)
    predictions = [
        json.loads(line)
        for line in (tmp_path / "visual_grounding_predictions.jsonl").read_text().splitlines()
    ]
    assert {item["pipeline"]["auth_mode"] for item in predictions} == {"bearer_configured"}
    assert result["promotion_recommendation"]["real_stage_provenance_present"] is True
    assert result["promotion_recommendation"]["selected_real_stage_provenance_complete"] is True
    assert (
        result["promotion_recommendation"]["requires_real_stage_provenance_before_promotion"]
        is False
    )


def test_visual_grounding_benchmark_runs_provider_prefixed_hosted_vlm_direct(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seen: dict[str, Any] = {}
    chat_server = _start_chat_server(
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
                                            "value": [0.4, 0.42, 0.22, 0.18],
                                        },
                                        "confidence": 0.83,
                                        "evidence_note": "fake hosted VLM direct output",
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
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        },
    )
    monkeypatch.setenv(
        "VISUAL_GROUNDING_VLM_BASE_URL",
        f"http://127.0.0.1:{chat_server.server_port}/v1",
    )
    monkeypatch.setenv("VISUAL_GROUNDING_VLM_API_KEY", "secret-vlm-key")
    service = _start_configurable_service(
        pipeline_id="real-router",
        adapter_mode="real",
    )
    pipelines = [
        "xiaomi/mimo-v2-omni-direct",
        "vertex_ai/gemini-3-flash-preview-direct",
        "tongyi/qwen3-vl-flash-direct",
        "siliconflow/Qwen/Qwen3-VL-8B-Instruct-direct",
    ]
    try:
        base_url = f"http://127.0.0.1:{service.server_port}"
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--corpus",
                str(CORPUS),
                "--output-dir",
                str(tmp_path),
                "--pipeline",
                ",".join(pipelines),
                "--base-url",
                base_url,
                "--timeout-s",
                "2",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    finally:
        service.shutdown()
        service.server_close()
        chat_server.shutdown()
        chat_server.server_close()

    result = json.loads((tmp_path / "visual_grounding_benchmark_result.json").read_text())
    by_pipeline = {item["pipeline_id"]: item for item in result["pipelines"]}
    assert set(by_pipeline) == set(pipelines)
    assert all(item["failure_count"] == 0 for item in by_pipeline.values())
    assert all(item["auth_mode"] == "bearer_configured" for item in by_pipeline.values())
    assert all(item["evidence_level"] == "real_or_hosted_service" for item in by_pipeline.values())
    seen_models = {
        request["payload"]["model"]
        for request in seen["requests"]
        if request["payload"].get("model")
    }
    assert seen_models == {
        "xiaomi/mimo-v2-omni",
        "vertex_ai/gemini-3-flash-preview",
        "tongyi/qwen3-vl-flash",
        "siliconflow/Qwen/Qwen3-VL-8B-Instruct",
    }
    assert {request["authorization"] for request in seen["requests"]} == {"Bearer secret-vlm-key"}
    assert "secret-vlm-key" not in json.dumps(result)


def _start_fake_server(*, mode: str) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(mode=mode, latency_ms=1),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _start_configurable_service(
    *,
    pipeline_id: str,
    adapter_mode: str,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_configurable_handler(
            pipeline_id=pipeline_id,
            adapter_mode=adapter_mode,
            latency_ms=1,
        ),
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
            seen.setdefault("requests", []).append(
                {
                    "path": seen["path"],
                    "authorization": seen["authorization"],
                    "payload": seen["payload"],
                }
            )
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
